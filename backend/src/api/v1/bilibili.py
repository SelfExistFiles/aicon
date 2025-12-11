"""
Bilibili发布API端点
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.bilibili import (
    BilibiliAccountInfo,
    LoginResponse,
    PublishRequest,
    PublishResponse,
    PublishTaskStatus,
    TidOption
)
from src.core.database import get_db
from src.models.publish_task import BilibiliAccount, PublishTask
from src.models.user import User
from src.services.bilibili import BilibiliService
from src.tasks.bilibili_task import upload_chapter_to_bilibili

router = APIRouter()


@router.post("/accounts/create")
async def create_account(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        account_name: str
):
    """创建新账号并获取登录命令"""
    from datetime import datetime
    
    # 创建账号记录
    account = BilibiliAccount(
        user_id=current_user.id,
        account_name=account_name,
        is_active=False,
        login_status="pending"
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    # 获取登录命令
    bilibili_service = BilibiliService(db)
    login_info = await bilibili_service.get_login_command(str(account.id))
    
    # 更新cookie路径
    account.cookie_path = login_info["cookie_file"]
    await db.commit()
    
    return {
        "success": True,
        "account_id": str(account.id),
        "account_name": account.account_name,
        "command": login_info["command"],
        "post_command": login_info["post_command"],
        "cookie_file": login_info["cookie_file"],
        "message": login_info["message"]
    }


@router.post("/accounts/{account_id}/check-login")
async def check_account_login(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        account_id: str
):
    """检查账号登录状态"""
    from datetime import datetime
    
    # 获取账号
    query = select(BilibiliAccount).where(
        BilibiliAccount.id == account_id,
        BilibiliAccount.user_id == current_user.id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )
    
    # 检查cookie文件
    bilibili_service = BilibiliService(db)
    print("Checking cookie at path: ")
    print(account.cookie_path)
    cookie_exists = await bilibili_service.check_cookie_exists(account.cookie_path)
    
    if cookie_exists:
        # 登录成功
        account.mark_login_success()
        await db.commit()
        
        return {
            "success": True,
            "logged_in": True,
            "message": "登录成功"
        }
    else:
        return {
            "success": True,
            "logged_in": False,
            "message": "Cookie文件不存在,请确认已完成登录"
        }


@router.put("/accounts/{account_id}/set-default")
async def set_default_account(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        account_id: str
):
    """设置默认账号"""
    # 取消其他账号的默认状态
    query = select(BilibiliAccount).where(
        BilibiliAccount.user_id == current_user.id,
        BilibiliAccount.is_default == True
    )
    result = await db.execute(query)
    old_defaults = result.scalars().all()
    
    for acc in old_defaults:
        acc.is_default = False
    
    # 设置新的默认账号
    query = select(BilibiliAccount).where(
        BilibiliAccount.id == account_id,
        BilibiliAccount.user_id == current_user.id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )
    
    account.is_default = True
    await db.commit()
    
    return {
        "success": True,
        "message": "已设置为默认账号"
    }


@router.get("/publishable-videos")
async def get_publishable_videos(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        limit: int = 20,
        offset: int = 0
):
    """获取可发布的视频列表(已完成的video_tasks)"""
    from src.models.video_task import VideoTask, VideoTaskStatus
    from src.models.project import Project
    from src.models.chapter import Chapter
    
    # 查询已完成的视频任务
    query = select(VideoTask, Project, Chapter).join(
        Project, VideoTask.project_id == Project.id
    ).join(
        Chapter, VideoTask.chapter_id == Chapter.id
    ).where(
        VideoTask.user_id == current_user.id,
        VideoTask.status == VideoTaskStatus.COMPLETED.value,
        VideoTask.video_key.isnot(None)
    ).order_by(VideoTask.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    rows = result.all()
    
    videos = []
    for video_task, project, chapter in rows:
        videos.append({
            "id": str(video_task.id),
            "project_id": str(video_task.project_id),
            "project_title": project.title,
            "chapter_id": str(video_task.chapter_id),
            "chapter_title": chapter.title,
            "video_url": video_task.get_video_url(),
            "video_duration": video_task.video_duration,
            "created_at": video_task.created_at.isoformat() if video_task.created_at else None,
        })
    
    return {
        "videos": videos,
        "total": len(videos)
    }


@router.post("/publish", response_model=PublishResponse)
async def publish_to_bilibili(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        request: PublishRequest
):
    """发布视频到B站"""
    
    # 验证video_task是否存在且已完成
    from src.models.video_task import VideoTask, VideoTaskStatus
    query = select(VideoTask).where(VideoTask.id == request.video_task_id)
    result = await db.execute(query)
    video_task = result.scalar_one_or_none()
    
    if not video_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频任务不存在"
        )
    
    if video_task.status != VideoTaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="视频尚未生成完成"
        )
    
    if not video_task.video_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="视频文件不存在"
        )
    
    # 创建发布任务
    publish_task = PublishTask(
        video_task_id=video_task.id,
        user_id=current_user.id,
        platform="bilibili",
        title=request.title,
        desc=request.desc,
        tid=request.tid,
        tag=request.tag,
        copyright=request.copyright,
        source=request.source,
        dynamic=request.dynamic,
        cover_url=request.cover_url,
        dtime=request.dtime,
        upload_line=request.upload_line,
        upload_limit=request.upload_limit
    )
    
    db.add(publish_task)
    await db.commit()
    await db.refresh(publish_task)
    
    # 投递Celery任务
    from src.tasks.bilibili_task import upload_chapter_to_bilibili
    task = upload_chapter_to_bilibili.delay(
        publish_task_id=str(publish_task.id),
        user_id=str(current_user.id)
    )
    
    # 更新任务ID
    publish_task.celery_task_id = task.id
    await db.commit()
    
    return PublishResponse(
        success=True,
        task_id=task.id,
        publish_task_id=str(publish_task.id),
        message="发布任务已提交"
    )


@router.get("/tasks/{task_id}", response_model=PublishTaskStatus)
async def get_publish_task_status(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        task_id: str
):
    """获取发布任务状态"""
    query = select(PublishTask).where(
        PublishTask.id == task_id,
        PublishTask.user_id == current_user.id
    )
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    return PublishTaskStatus(
        id=str(task.id),
        video_task_id=str(task.video_task_id),
        platform=task.platform,
        title=task.title,
        status=task.status,
        progress=task.progress,
        bvid=task.bvid,
        aid=task.aid,
        error_message=task.error_message,
        created_at=task.created_at,
        published_at=task.published_at
    )


@router.get("/tasks", response_model=List[PublishTaskStatus])
async def get_publish_tasks(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str = None,
        status_filter: str = None,
        limit: int = 20
):
    """获取发布任务列表"""
    query = select(PublishTask).where(
        PublishTask.user_id == current_user.id
    )
    
    if chapter_id:
        query = query.where(PublishTask.chapter_id == chapter_id)
    
    if status_filter:
        query = query.where(PublishTask.status == status_filter)
    
    query = query.order_by(PublishTask.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [
        PublishTaskStatus(
            id=str(task.id),
            video_task_id=str(task.video_task_id),
            platform=task.platform,
            title=task.title,
            status=task.status,
            progress=task.progress,
            bvid=task.bvid,
            aid=task.aid,
            error_message=task.error_message,
            created_at=task.created_at,
            published_at=task.published_at
        )
        for task in tasks
    ]


@router.get("/tid-options", response_model=List[TidOption])
async def get_tid_options():
    """获取B站分区选项"""
    return [
        TidOption(label="知识", value=36),
        TidOption(label="科技", value=188),
        TidOption(label="生活", value=160),
        TidOption(label="游戏", value=4),
        TidOption(label="娱乐", value=5),
        TidOption(label="影视", value=181),
        TidOption(label="音乐", value=3),
        TidOption(label="动画", value=1),
        TidOption(label="时尚", value=155),
        TidOption(label="美食", value=211),
        TidOption(label="汽车", value=223),
        TidOption(label="运动", value=234),
        TidOption(label="动物圈", value=217),
        TidOption(label="舞蹈", value=129),
        TidOption(label="国创", value=167),
        TidOption(label="鬼畜", value=119),
    ]


@router.get("/accounts", response_model=List[BilibiliAccountInfo])
async def get_bilibili_accounts(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db)
):
    """获取用户的B站账号列表"""
    query = select(BilibiliAccount).where(
        BilibiliAccount.user_id == current_user.id
    ).order_by(BilibiliAccount.last_login_at.desc())
    
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    # 检查cookie有效性
    bilibili_service = BilibiliService(db)
    account_list = []
    
    for account in accounts:
        cookie_valid = False
        if account.cookie_path:
            cookie_valid = await bilibili_service.check_cookie_exists(account.cookie_path)
        
        account_list.append(BilibiliAccountInfo(
            id=str(account.id),
            account_name=account.account_name,
            is_active=account.is_active and cookie_valid,
            is_default=account.is_default,
            cookie_valid=cookie_valid,
            last_login_at=account.last_login_at,
            created_at=account.created_at
        ))
    
    return account_list


@router.get("/accounts/status")
async def get_account_status(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db)
):
    """获取账号登录状态"""
    query = select(BilibiliAccount).where(
        BilibiliAccount.user_id == current_user.id,
        BilibiliAccount.is_active == True
    ).order_by(BilibiliAccount.last_login_at.desc())
    
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        return {
            "logged_in": False,
            "message": "未登录B站账号"
        }
    
    # 检查cookie文件是否存在
    from pathlib import Path
    cookie_path = Path(account.cookie_path) if account.cookie_path else None
    cookie_exists = cookie_path.exists() if cookie_path else False
    
    return {
        "logged_in": cookie_exists,
        "account_name": account.account_name,
        "last_login_at": account.last_login_at.isoformat() if account.last_login_at else None,
        "message": "已登录" if cookie_exists else "Cookie已过期,请重新登录"
    }


@router.delete("/accounts/{account_id}")
async def delete_bilibili_account(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        account_id: str
):
    """删除B站账号"""
    query = select(BilibiliAccount).where(
        BilibiliAccount.id == account_id,
        BilibiliAccount.user_id == current_user.id
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )
    
    # 删除cookie文件
    from pathlib import Path
    if account.cookie_path:
        cookie_path = Path(account.cookie_path)
        if cookie_path.exists():
            cookie_path.unlink()
    
    # 删除账号记录
    await db.delete(account)
    await db.commit()
    
    return {
        "success": True,
        "message": "账号已删除"
    }


__all__ = ["router"]
