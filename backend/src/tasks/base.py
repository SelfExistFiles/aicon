"""
任务基础工具模块 - 提供异步任务运行和数据库会话管理
"""
import asyncio
import functools
import threading
from typing import Any, Callable, Coroutine, TypeVar

from src.core.database import get_async_db
from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# 全局事件循环容器（针对每个 worker 进程，固定一个后台 loop 线程）
_worker_loop = None
_worker_loop_thread = None
_worker_loop_lock = threading.Lock()
_worker_loop_ready = threading.Event()


def _worker_loop_runner() -> None:
    """在独立线程中启动并常驻一个事件循环。"""
    global _worker_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _worker_loop = loop
    _worker_loop_ready.set()
    try:
        loop.run_forever()
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        loop.close()
        _worker_loop = None

def get_worker_loop():
    """获取或创建一个在该 worker 进程中持续存在的后台事件循环。"""
    global _worker_loop_thread
    with _worker_loop_lock:
        if (
            _worker_loop is None
            or _worker_loop.is_closed()
            or _worker_loop_thread is None
            or not _worker_loop_thread.is_alive()
        ):
            _worker_loop_ready.clear()
            _worker_loop_thread = threading.Thread(
                target=_worker_loop_runner,
                name="celery-worker-async-loop",
                daemon=True,
            )
            _worker_loop_thread.start()
    _worker_loop_ready.wait()
    return _worker_loop

def run_async_task(coro: Coroutine[Any, Any, T]) -> T:
    """
    在同步环境中运行异步协程的辅助函数。
    所有任务都提交到同一个后台事件循环，避免 loop 重入以及数据库连接池跨 loop 复用。
    """
    loop = get_worker_loop()
    if threading.current_thread() is _worker_loop_thread:
        raise RuntimeError("run_async_task 不能在 worker loop 线程内部再次同步等待")
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

def async_task_decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    将异步函数包装为同步 Celery 任务的装饰器。
    自动注入数据库会话并处理异步运行。
    
    使用此装饰器的函数定义应为：
    @async_task_decorator
    async def my_task(db_session, *args, **kwargs):
        ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        async def _run():
            # 获取异步数据库会话
            async with get_async_db() as db:
                # 将 db_session 注入第一个参数
                return await func(db, *args, **kwargs)
        
        return run_async_task(_run())
    
    return wrapper
