import asyncio

import pytest

from src.tasks import base


def _stop_worker_loop():
    loop = getattr(base, "_worker_loop", None)
    thread = getattr(base, "_worker_loop_thread", None)
    ready = getattr(base, "_worker_loop_ready", None)

    if loop and not loop.is_closed():
        loop.call_soon_threadsafe(loop.stop)
    if thread and thread.is_alive():
        thread.join(timeout=2)

    base._worker_loop = None
    base._worker_loop_thread = None
    if ready is not None:
        ready.clear()


@pytest.fixture(autouse=True)
def reset_worker_loop_state():
    _stop_worker_loop()
    yield
    _stop_worker_loop()


@pytest.mark.unit
def test_run_async_task_reuses_same_background_loop():
    async def sample():
        await asyncio.sleep(0)
        return id(asyncio.get_running_loop())

    first_loop_id = base.run_async_task(sample())
    second_loop_id = base.run_async_task(sample())

    assert first_loop_id == second_loop_id
    assert base._worker_loop_thread is not None
    assert base._worker_loop_thread.is_alive()


@pytest.mark.unit
def test_run_async_task_can_serve_multiple_callers_without_loop_reentry():
    async def sample(value):
        await asyncio.sleep(0)
        return value, id(asyncio.get_running_loop())

    first_value, first_loop_id = base.run_async_task(sample("first"))
    second_value, second_loop_id = base.run_async_task(sample("second"))

    assert first_value == "first"
    assert second_value == "second"
    assert first_loop_id == second_loop_id
