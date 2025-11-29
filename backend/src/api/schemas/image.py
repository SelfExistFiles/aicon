"""
图片生成相关的Pydantic模式
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """生成图片请求模型"""
    sentences_ids: list[UUID] = Field(..., description="句子ID列表")
    api_key_id: UUID = Field(..., description="API密钥ID")
    
    class Config:
        """配置"""
        json_schema_extra = {
            "example": {
                "sentences_ids": ["123e4567-e89b-12d3-a456-426614174000", "223e4567-e89b-12d3-a456-426614174111"],
                "api_key_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class ImageGenerateResponse(BaseModel):
    """生成图片响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
