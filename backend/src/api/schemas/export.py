"""
导出相关 API Schema
"""

from pydantic import BaseModel, Field


class JianYingExportResponse(BaseModel):
    """剪映导出响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    download_url: str = Field("", description="下载URL")
    filename: str = Field("", description="文件名")


__all__ = ["JianYingExportResponse"]
