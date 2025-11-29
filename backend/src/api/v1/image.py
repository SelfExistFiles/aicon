"""
图片生成 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.image import ImageGenerateRequest, ImageGenerateResponse
from src.core.database import get_db
from src.core.exceptions import NotFoundError, BusinessLogicError
from src.core.logging import get_logger
from src.models.chapter import Chapter
from src.models.user import User
from src.tasks.task import generate_images

logger = get_logger(__name__)

router = APIRouter()


@router.post("/generate-images", response_model=ImageGenerateResponse)
async def generate_images_api(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        request: ImageGenerateRequest
):
    """
    批量生成图片
    
    根据句子ID列表，调用AI图像生成服务生成图片。
    适合批量生成和重新生成图片场景。
    """
    from sqlalchemy import select
    from src.models.sentence import Sentence
    from src.models.paragraph import Paragraph

    # 1. 验证句子权限和状态
    if not request.sentences_ids:
        raise BusinessLogicError(message="句子ID列表不能为空")

    # 2. 获取句子并验证权限
    stmt = select(Sentence).join(Paragraph).join(Chapter).where(
        Sentence.id.in_(request.sentences_ids)
    )
    result = await db.execute(stmt)
    sentences = result.scalars().all()

    if len(sentences) != len(request.sentences_ids):
        raise NotFoundError(
            "部分句子不存在",
            resource_type="sentence"
        )

    # 4. 验证所有句子都有提示词
    for sentence in sentences:
        if not sentence.image_prompt:
            raise BusinessLogicError(message=f"句子 {sentence.id} 没有生成提示词")

    # 5. 投递任务到celery
    sentence_ids_hex = [sentence_id.hex for sentence_id in request.sentences_ids]
    result = generate_images.delay(request.api_key_id.hex, sentence_ids_hex)

    logger.info(f"成功为句子列表 {request.sentences_ids} 投递图片生成任务，任务ID: {result.id}")
    return ImageGenerateResponse(success=True, message="图片生成任务已提交")


__all__ = ["router"]
