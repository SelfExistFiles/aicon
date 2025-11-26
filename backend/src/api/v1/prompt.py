"""
AI导演引擎 API

提供功能：
- 批量生成图像提示词
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.prompt import PromptGenerateRequest, PromptGenerateResponse
from src.core.database import get_db
from src.core.exceptions import BusinessLogicError, NotFoundError
from src.core.logging import get_logger
from src.models.chapter import Chapter
from src.models.paragraph import Paragraph
from src.models.sentence import Sentence
from src.models.user import User
from src.services.project import ProjectService
from src.services.prompt import PromptService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/generate-prompts", response_model=PromptGenerateResponse)
async def generate_prompts(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        request: PromptGenerateRequest
):
    """
    为章节批量生成提示词
    
    根据章节内容，调用LLM为每个句子生成专业的图像提示词。
    """
    # 1. 获取章节并验证权限
    stmt = select(Chapter).where(Chapter.id == request.chapter_id)
    result = await db.execute(stmt)
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise NotFoundError(
            "章节不存在",
            resource_type="chapter",
            resource_id=str(request.chapter_id)
        )

    # 验证项目权限
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    # 2. 获取章节下的所有句子（通过段落）
    stmt = (
        select(Sentence)
        .join(Paragraph)
        .join(Chapter)
        .where(Chapter.id == request.chapter_id)
        .order_by(Paragraph.order_index, Sentence.order_index)
    )
    result = await db.execute(stmt)
    sentences = result.scalars().all()

    if not sentences:
        raise BusinessLogicError("章节没有句子数据")

    # 3. 提取文本
    sentence_texts = [s.content for s in sentences]

    # 4. 调用AI服务生成提示词
    prompt_service = PromptService(db)
    prompts = await prompt_service.generate_prompts_batch(
        sentences=sentence_texts,
        api_key=request.api_key,
        provider=request.provider,
        model=request.model,
        style=request.style
    )

    # 5. 更新数据库
    updated_count = 0
    for sentence, prompt_data in zip(sentences, prompts):
        sentence.image_prompt = prompt_data["prompt"]
        sentence.image_style = request.style
        # 如果没有手动编辑过，则更新edited_prompt
        if not sentence.is_manual_edited:
            sentence.edited_prompt = prompt_data["prompt"]
        updated_count += 1

    await db.commit()

    logger.info(f"成功为章节 {request.chapter_id} 生成 {updated_count} 个提示词")

    return PromptGenerateResponse(
        success=True,
        message=f"成功为 {updated_count} 个句子生成提示词",
        updated_count=updated_count
    )


__all__ = ["router"]
