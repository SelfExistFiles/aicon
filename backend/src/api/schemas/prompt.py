"""
AI导演引擎相关的Pydantic模式
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import UUIDMixin


class PromptGenerateRequest(BaseModel):
    """生成提示词请求模型"""
    chapter_id: UUID = Field(..., description="章节ID")
    api_key_id: UUID = Field(..., description="密钥key_id")
    style: str = Field("cinematic", description="风格预设")

    model_config = {
        "json_schema_extra": {
            "example": {
                "chapter_id": "123e4567-e89b-12d3-a456-426614174000",
                "api_key_id": "123e4567-e89b-12d3-a456-426614174000",
                "style": "cinematic"
            }
        }
    }


class PromptGenerateResponse(BaseModel):
    """生成提示词响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "成功为 100 个句子生成提示词",
            }
        }
    }


__all__ = [
    "PromptGenerateRequest",
    "PromptGenerateResponse",
]
