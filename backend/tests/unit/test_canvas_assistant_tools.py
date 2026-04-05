from unittest.mock import AsyncMock

import pytest

from src.assistant.tools.canvas_tools import CanvasAssistantCanvasExecutionTools
from src.assistant.tools.generation_tools import CanvasAssistantGenerationTools


@pytest.mark.asyncio
async def test_canvas_execution_tools_commit_mutations() -> None:
    service = AsyncMock()
    service.create_item.return_value = {"id": "item-1", "item_type": "text", "title": "剧本草稿"}

    tools = CanvasAssistantCanvasExecutionTools(service)
    result = await tools.create_item("doc-1", "user-1", {"item_type": "text", "title": "剧本草稿"})

    service.create_item.assert_awaited_once_with("doc-1", "user-1", {"item_type": "text", "title": "剧本草稿"})
    service.commit.assert_awaited_once()
    assert result["effect"].mutated is True
    assert result["effect"].created_item_ids == ["item-1"]


@pytest.mark.asyncio
async def test_canvas_execution_tools_batch_create_items_with_relations() -> None:
    service = AsyncMock()
    service.create_item.side_effect = [
        {"id": "shot-1", "item_type": "text", "title": "分镜1"},
        {"id": "shot-2", "item_type": "text", "title": "分镜2"},
    ]
    service.create_connection.side_effect = [
        {"id": "conn-1", "source_item_id": "script-1", "target_item_id": "shot-1"},
        {"id": "conn-2", "source_item_id": "script-1", "target_item_id": "shot-2"},
    ]

    tools = CanvasAssistantCanvasExecutionTools(service)
    result = await tools.create_items(
        "doc-1",
        "user-1",
        [
            {"node_type": "text", "title": "分镜1", "purpose": "镜头描述", "content": "场景一"},
            {"node_type": "text", "title": "分镜2", "purpose": "镜头描述", "content": "场景二"},
        ],
        {"mode": "column", "start_x": 100, "start_y": 120, "gap_y": 20},
        "script-1",
    )

    assert service.create_item.await_count == 2
    assert service.create_connection.await_count == 2
    service.commit.assert_awaited_once()
    assert result["effect"].created_item_ids == ["shot-1", "shot-2"]
    assert result["effect"].created_connection_ids == ["conn-1", "conn-2"]
    assert result["references"] == [
        {"item_id": "shot-1", "source_item_id": "script-1"},
        {"item_id": "shot-2", "source_item_id": "script-1"},
    ]


@pytest.mark.asyncio
async def test_generation_tools_commit_after_attach_task() -> None:
    generation_service = AsyncMock()
    generation = type("Generation", (), {"id": "gen-1"})()
    generation_service.prepare_text_generation.return_value = (object(), generation)
    generation_service.attach_task.return_value = (object(), generation)

    tools = CanvasAssistantGenerationTools(
        generation_service=generation_service,
        dispatch_text=lambda generation_id: f"task-{generation_id}",
    )
    result = await tools.submit_generation("user-1", "item-1", "text", {"prompt": "写一个科幻分镜脚本"})

    generation_service.prepare_text_generation.assert_awaited_once_with("item-1", "user-1", {"prompt": "写一个科幻分镜脚本"})
    generation_service.attach_task.assert_awaited_once_with("gen-1", "task-gen-1")
    generation_service.commit.assert_awaited_once()
    assert result["effect"].mutated is True
    assert result["submitted"][0]["task_id"] == "task-gen-1"
