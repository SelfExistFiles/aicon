from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.sentence import SentenceStatus


class SentenceBase(BaseModel):
    content: str = Field(..., description="句子内容")


class SentenceCreate(SentenceBase):
    paragraph_id: str = Field(..., description="所属段落ID")
    order_index: Optional[int] = Field(None, description="顺序索引，不传则自动追加到最后")


class SentenceUpdate(BaseModel):
    content: str = Field(..., description="句子内容")


class SentenceResponse(SentenceBase):
    id: str
    paragraph_id: str
    order_index: int
    word_count: int
    character_count: int
    status: SentenceStatus
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
