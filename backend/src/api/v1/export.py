"""
导出相关 API 路由
"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.export import JianYingExportResponse
from src.core.database import get_db
from src.models.user import User
from src.services.jianying_export import JianYingExportService, JianYingExportError

router = APIRouter()


@router.post("/jianying/{chapter_id}", response_model=JianYingExportResponse)
async def export_chapter_to_jianying(
    *,
    chapter_id: str,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    导出章节为剪映草稿格式
    
    Args:
        chapter_id: 章节ID
        
    Returns:
        导出结果，包含下载URL
    """
    try:
        export_service = JianYingExportService(db)
        zip_path = await export_service.export_chapter(
            chapter_id=chapter_id,
            user_id=str(current_user.id)
        )
        
        # 生成下载URL（使用文件ID）
        filename = Path(zip_path).name
        
        return JianYingExportResponse(
            success=True,
            message="导出成功",
            download_url=f"/api/v1/export/jianying/download/{filename}",
            filename=filename
        )
        
    except JianYingExportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出失败: {str(e)}"
        )


@router.get("/jianying/download/{filename}")
async def download_jianying_export(
    filename: str,
    current_user: User = Depends(get_current_user_required)
):
    """
    下载导出的剪映文件
    
    Args:
        filename: 文件名
        
    Returns:
        文件下载响应
    """
    import tempfile
    from src.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    # 构建文件路径（从临时目录）
    file_path = Path(tempfile.gettempdir()) / filename
    
    logger.info(f"尝试下载文件: {file_path}")
    logger.info(f"文件是否存在: {file_path.exists()}")
    
    if file_path.exists():
        file_size = file_path.stat().st_size
        logger.info(f"文件大小: {file_size} bytes")
    
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或已过期"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


__all__ = ["router"]
