from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.sentence import SentenceCreate, SentenceResponse, SentenceUpdate, SentenceListResponse
from src.services.sentence import SentenceService

router = APIRouter()


@router.get("/", response_model=SentenceListResponse)
async def list_sentences(
    paragraph_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取段落的句子列表
    
    Args:
        paragraph_id: 段落ID
        
    Returns:
        句子列表，按order_index排序
    """
    service = SentenceService(db)
    sentences = await service.get_sentences_by_paragraph(paragraph_id)
    
    # Convert ORM objects to dicts for Pydantic v2 compatibility
    data = [s.to_dict() for s in sentences]
    
    return SentenceListResponse(
        data=data,
        total=len(sentences)
    )


@router.post("/", response_model=SentenceResponse, status_code=status.HTTP_201_CREATED)
async def create_sentence(
    sentence_in: SentenceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新句子
    """
    service = SentenceService(db)
    return await service.create_sentence(
        paragraph_id=sentence_in.paragraph_id,
        content=sentence_in.content,
        order_index=sentence_in.order_index
    )


@router.get("/{sentence_id}", response_model=SentenceResponse)
async def get_sentence(
    sentence_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取句子详情
    """
    service = SentenceService(db)
    return await service.get_sentence_by_id(sentence_id)


@router.put("/{sentence_id}", response_model=SentenceResponse)
async def update_sentence(
    sentence_id: str,
    sentence_in: SentenceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新句子内容
    """
    service = SentenceService(db)
    return await service.update_sentence(
        sentence_id=sentence_id,
        content=sentence_in.content
    )


@router.delete("/{sentence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sentence(
    sentence_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除句子
    """
    service = SentenceService(db)
    await service.delete_sentence(sentence_id)
