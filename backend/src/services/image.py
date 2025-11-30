import asyncio
import uuid
from typing import List

import aiohttp
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError
from src.core.logging import get_logger
from src.models import Sentence, APIKey, SentenceStatus, Paragraph, Chapter
from src.services.api_key import APIKeyService
from src.services.base import SessionManagedService
from src.services.provider.base import BaseLLMProvider
from src.services.provider.factory import ProviderFactory
from src.utils.storage import get_storage_client

logger = get_logger(__name__)


# ============================================================
# 处理单句 – 优化版（返回异常信息）
# ============================================================

async def process_sentence(
    sentence: Sentence,
    llm_provider: BaseLLMProvider,
    semaphore: asyncio.Semaphore,
):
    """
    单句 LLM 图片生成任务（含限流、错误透传）。
    """
    async with semaphore:
        try:
            logger.info(f"[LLM] 处理句子 {sentence.id}")

            result = await llm_provider.generate_image(
                prompt=sentence.image_prompt,
                model="Kwai-Kolors/Kolors",
                size="960×1280",
                n=1,
            )

            url = result.data[0].url
            return sentence, url, None

        except Exception as e:
            logger.error(f"[LLM] 句子 {sentence.id} 错误: {e}", exc_info=True)
            return sentence, None, e


# ============================================================
# ImageService 主体
# ============================================================

class ImageService(SessionManagedService):

    async def generate_images(self, api_key_id: str, sentence_ids: List[str]) -> None:

        # --- 1. 查询 Sentence ----
        stmt = (
            select(Sentence)
            .where(Sentence.id.in_(sentence_ids))
            .options(
                selectinload(Sentence.paragraph)
                .selectinload(Paragraph.chapter)
                .selectinload(Chapter.project)
            )
        )
        result = await self.execute(stmt)
        sentences = result.scalars().all()

        if not sentences:
            raise NotFoundError("未找到待处理句子")

        chapter = sentences[0].paragraph.chapter
        user_id = chapter.project.owner_id

        # --- 2. 获取 API Key ---
        api_key_service = APIKeyService(self.db_session)
        api_key = await api_key_service.get_api_key_by_id(api_key_id, user_id)

        # --- 3. LLM Provider ---
        llm_provider = ProviderFactory.create(
            provider=api_key.provider,
            api_key=api_key.get_api_key(),
            max_concurrency=5,
        )

        # --- 4. 创建统一并发控制 ---
        semaphore = asyncio.Semaphore(5)

        # --- 5. 创建任务列表 ---
        tasks = [
            process_sentence(sentence, llm_provider, semaphore)
            for sentence in sentences
        ]

        logger.info(f"[LLM] 开始并发处理，共 {len(tasks)} 项")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # --- 6. 统一的下载 Session ---
        storage_client = await get_storage_client()
        async with aiohttp.ClientSession() as http_session:

            for sentence, image_url, err in results:
                if err or not image_url:
                    continue  # 跳过失败的句子

                # --- 下载图片 ---
                try:
                    async with http_session.get(image_url) as resp:
                        if resp.status != 200:
                            logger.error(f"[Download] 失败 {resp.status} url={image_url}")
                            continue
                        content = await resp.read()
                except Exception as e:
                    logger.error(f"[Download] 图片下载错误: {e}")
                    continue

                # --- 上传 MinIO ---
                file_id = str(uuid.uuid4())
                storage_result = await storage_client.upload_file(
                    user_id=user_id,
                    file=content,
                    metadata={
                        "user_id": user_id,
                        "file_id": file_id,
                        "file_type": "image/jpeg",
                        "original_filename": f"{file_id}.jpg"
                    }
                )

                object_key = storage_result["object_key"]

                # --- 更新数据库 ---
                sentence.image_url = object_key
                sentence.status = SentenceStatus.GENERATED_IMAGE

        # --- 7. 提交数据库 ---
        await self.db_session.flush()
        await self.db_session.commit()

        # --- 8. 更新 API Key 统计 ---
        await api_key_service.update_usage(api_key.id, user_id)

        logger.info("[FINISH] 所有任务完成")


image_service = ImageService()
__all__ = ["ImageService", "image_service"]
