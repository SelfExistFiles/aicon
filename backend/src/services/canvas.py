import asyncio
import base64
import html
import io
import json
import re
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from fastapi import UploadFile
from sqlalchemy import delete, desc, func, select

from src.core.exceptions import BusinessLogicError, NotFoundError
from src.core.logging import get_logger
from src.models.api_key import APIKey
from src.models.canvas import (
    CanvasConnection,
    CanvasDocument,
    CanvasGenerationType,
    CanvasItem,
    CanvasItemGeneration,
    CanvasItemType,
    CanvasRunStatus,
    ensure_canvas_uuid,
)
from src.services.api_key import APIKeyService
from src.services.base import BaseService
from src.services.provider.factory import ProviderFactory
from src.services.provider.vector_engine_provider import VectorEngineProvider
from src.utils.storage import get_storage_client

logger = get_logger(__name__)

PROMPT_BREAK_TAG_PATTERN = re.compile(r"(?i)<br\s*/?>")
PROMPT_LIST_ITEM_PATTERN = re.compile(r"(?i)<li\b[^>]*>")
PROMPT_LIST_ITEM_CLOSE_PATTERN = re.compile(r"(?i)</li>")
PROMPT_BLOCK_TAG_PATTERN = re.compile(r"(?i)</?(p|div|h[1-6]|ul|ol|blockquote|section|article|hr)\b[^>]*>")
PROMPT_HTML_TAG_PATTERN = re.compile(r"(?is)<[^>]+>")
PROMPT_SPACE_PATTERN = re.compile(r"[ \t]+")
PROMPT_BLANK_LINE_PATTERN = re.compile(r"\n{3,}")
REFERENCE_TEXT_LIMIT = 1500
REFERENCE_IMAGE_LIMIT = 2


class CanvasService(BaseService):
    async def list_documents(self, user_id: str, page: int = 1, size: int = 20) -> Tuple[List[CanvasDocument], int]:
        count_stmt = select(func.count(CanvasDocument.id)).where(CanvasDocument.user_id == ensure_canvas_uuid(user_id))
        total = (await self.execute(count_stmt)).scalar() or 0
        stmt = (
            select(CanvasDocument)
            .where(CanvasDocument.user_id == ensure_canvas_uuid(user_id))
            .order_by(desc(CanvasDocument.updated_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.execute(stmt)
        return list(result.scalars().all()), total

    async def create_document(self, user_id: str, title: str, description: Optional[str] = None) -> CanvasDocument:
        document = CanvasDocument(user_id=ensure_canvas_uuid(user_id), title=title, description=description)
        self.add(document)
        await self.flush()
        await self.refresh(document)
        return document

    async def get_document(self, document_id: str, user_id: str) -> CanvasDocument:
        stmt = select(CanvasDocument).where(
            CanvasDocument.id == ensure_canvas_uuid(document_id),
            CanvasDocument.user_id == ensure_canvas_uuid(user_id),
        )
        result = await self.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            raise NotFoundError("画布不存在", resource_id=document_id, resource_type="canvas_document")
        return document

    async def update_document(self, document_id: str, user_id: str, title: Optional[str], description: Optional[str]) -> CanvasDocument:
        document = await self.get_document(document_id, user_id)
        if title is not None:
            document.title = title
        if description is not None:
            document.description = description
        await self.flush()
        await self.refresh(document)
        return document

    async def delete_document(self, document_id: str, user_id: str) -> None:
        document = await self.get_document(document_id, user_id)
        await self.db_session.delete(document)
        await self.flush()

    async def create_item(self, document_id: str, user_id: str, payload: Dict[str, Any]) -> CanvasItem:
        document = await self.get_document(document_id, user_id)
        item = CanvasItem(
            document_id=document.id,
            item_type=payload["item_type"],
            title=payload.get("title", ""),
            position_x=payload.get("position_x", 0),
            position_y=payload.get("position_y", 0),
            width=payload.get("width", 320),
            height=payload.get("height", 220),
            z_index=payload.get("z_index", 0),
            content_json=payload.get("content", {}),
            generation_config_json=payload.get("generation_config", {}),
            last_run_status=payload.get("last_run_status") or CanvasRunStatus.IDLE.value,
            last_run_error=payload.get("last_run_error"),
            last_output_json=payload.get("last_output", {}),
        )
        self.add(item)
        await self.flush()
        await self.refresh(item)
        return item

    async def update_item(self, document_id: str, item_id: str, user_id: str, payload: Dict[str, Any]) -> CanvasItem:
        await self.get_document(document_id, user_id)
        item = await self.get_item(item_id, user_id)
        if str(item.document_id) != str(ensure_canvas_uuid(document_id)):
            raise NotFoundError("画布节点不存在", resource_id=item_id, resource_type="canvas_item")

        scalar_fields = ("title", "position_x", "position_y", "width", "height", "z_index", "last_run_status", "last_run_error")
        for field in scalar_fields:
            if field in payload and payload[field] is not None:
                setattr(item, field, payload[field])

        if "content" in payload and payload["content"] is not None:
            item.content_json = {**(item.content_json or {}), **payload["content"]}
        if "generation_config" in payload and payload["generation_config"] is not None:
            item.generation_config_json = {**(item.generation_config_json or {}), **payload["generation_config"]}
        if "last_output" in payload and payload["last_output"] is not None:
            item.last_output_json = {**(item.last_output_json or {}), **payload["last_output"]}

        await self.flush()
        await self.refresh(item)
        return item

    async def delete_item(self, document_id: str, item_id: str, user_id: str) -> None:
        await self.get_document(document_id, user_id)
        item = await self.get_item(item_id, user_id)
        if str(item.document_id) != str(ensure_canvas_uuid(document_id)):
            raise NotFoundError("画布节点不存在", resource_id=item_id, resource_type="canvas_item")
        await self.db_session.delete(item)
        await self.flush()

    async def create_connection(self, document_id: str, user_id: str, payload: Dict[str, Any]) -> CanvasConnection:
        document = await self.get_document(document_id, user_id)
        source_item = await self.get_item(str(payload["source_item_id"]), user_id)
        target_item = await self.get_item(str(payload["target_item_id"]), user_id)
        if source_item.document_id != document.id or target_item.document_id != document.id:
            raise BusinessLogicError("连线节点不属于当前画布")

        connection = CanvasConnection(
            document_id=document.id,
            source_item_id=source_item.id,
            target_item_id=target_item.id,
            source_handle=payload["source_handle"],
            target_handle=payload["target_handle"],
        )
        self.add(connection)
        await self.flush()
        await self.refresh(connection)
        return connection

    async def delete_connection(self, document_id: str, connection_id: str, user_id: str) -> None:
        document = await self.get_document(document_id, user_id)
        stmt = select(CanvasConnection).where(
            CanvasConnection.id == ensure_canvas_uuid(connection_id),
            CanvasConnection.document_id == document.id,
        )
        connection = (await self.execute(stmt)).scalar_one_or_none()
        if not connection:
            raise NotFoundError("画布连线不存在", resource_id=connection_id, resource_type="canvas_connection")
        await self.db_session.delete(connection)
        await self.flush()

    async def save_graph(self, document_id: str, user_id: str, items: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> CanvasDocument:
        document = await self.get_document(document_id, user_id)

        existing_items_stmt = select(CanvasItem).where(CanvasItem.document_id == document.id)
        existing_items = list((await self.execute(existing_items_stmt)).scalars().all())
        existing_by_id = {str(item.id): item for item in existing_items}
        incoming_ids = {str(ensure_canvas_uuid(item["id"])) for item in items}

        for existing_item in existing_items:
            if str(existing_item.id) not in incoming_ids:
                await self.db_session.delete(existing_item)

        for item_payload in items:
            item_id = str(ensure_canvas_uuid(item_payload["id"]))
            item = existing_by_id.get(item_id)
            if item is None:
                item = CanvasItem(
                    id=ensure_canvas_uuid(item_payload["id"]),
                    document_id=document.id,
                )
                self.add(item)

            item.item_type = item_payload["item_type"]
            item.title = item_payload.get("title", "")
            item.position_x = item_payload.get("position_x", 0)
            item.position_y = item_payload.get("position_y", 0)
            item.width = item_payload.get("width", 320)
            item.height = item_payload.get("height", 220)
            item.z_index = item_payload.get("z_index", 0)
            item.content_json = item_payload.get("content", {})
            item.generation_config_json = item_payload.get("generation_config", {})
            item.last_run_status = item_payload.get("last_run_status") or item.last_run_status or CanvasRunStatus.IDLE.value
            item.last_run_error = item_payload.get("last_run_error")
            item.last_output_json = item_payload.get("last_output", item.last_output_json or {})

        await self.execute(delete(CanvasConnection).where(CanvasConnection.document_id == document.id))
        await self.flush()

        for connection in connections:
            self.add(
                CanvasConnection(
                    id=ensure_canvas_uuid(connection["id"]),
                    document_id=document.id,
                    source_item_id=ensure_canvas_uuid(connection["source_item_id"]),
                    target_item_id=ensure_canvas_uuid(connection["target_item_id"]),
                    source_handle=connection["source_handle"],
                    target_handle=connection["target_handle"],
                )
            )

        await self.flush()
        await self.refresh(document)
        return document

    async def get_graph(self, document_id: str, user_id: str) -> Dict[str, Any]:
        document = await self.get_document(document_id, user_id)
        item_stmt = select(CanvasItem).where(CanvasItem.document_id == document.id).order_by(CanvasItem.z_index, CanvasItem.created_at)
        connection_stmt = select(CanvasConnection).where(CanvasConnection.document_id == document.id).order_by(CanvasConnection.created_at)
        items = list((await self.execute(item_stmt)).scalars().all())
        connections = list((await self.execute(connection_stmt)).scalars().all())
        return {"document": document, "items": items, "connections": connections}

    async def get_stage_snapshot(self, document_id: str, user_id: str) -> Dict[str, Any]:
        graph = await self.get_graph(document_id, user_id)
        projected_items = [self._project_stage_item(item) for item in graph["items"]]
        return {
            "document": graph["document"],
            "items": projected_items,
            "connections": graph["connections"],
        }

    async def get_item_previews(self, document_id: str, user_id: str, item_ids: List[str]) -> List[CanvasItem]:
        document = await self.get_document(document_id, user_id)
        if not item_ids:
            return []

        stmt = select(CanvasItem).where(
            CanvasItem.document_id == document.id,
            CanvasItem.id.in_([ensure_canvas_uuid(item_id) for item_id in item_ids]),
        )
        items = list((await self.execute(stmt)).scalars().all())
        return [self._serialize_item(item, content=self._project_preview_content(item)) for item in items]

    async def get_item(self, item_id: str, user_id: str) -> CanvasItem:
        stmt = (
            select(CanvasItem)
            .join(CanvasDocument, CanvasDocument.id == CanvasItem.document_id)
            .where(CanvasItem.id == ensure_canvas_uuid(item_id), CanvasDocument.user_id == ensure_canvas_uuid(user_id))
        )
        result = await self.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("画布节点不存在", resource_id=item_id, resource_type="canvas_item")
        return item

    async def get_item_by_id(self, item_id: str) -> CanvasItem:
        stmt = select(CanvasItem).where(CanvasItem.id == ensure_canvas_uuid(item_id))
        item = (await self.execute(stmt)).scalar_one_or_none()
        if not item:
            raise NotFoundError("画布节点不存在", resource_id=item_id, resource_type="canvas_item")
        return item

    async def get_generation(self, generation_id: str) -> CanvasItemGeneration:
        stmt = select(CanvasItemGeneration).where(CanvasItemGeneration.id == ensure_canvas_uuid(generation_id))
        generation = (await self.execute(stmt)).scalar_one_or_none()
        if not generation:
            raise NotFoundError("节点生成记录不存在", resource_id=generation_id, resource_type="canvas_generation")
        return generation

    async def get_item_generation(self, item_id: str, generation_id: str, user_id: str) -> Tuple[CanvasItem, CanvasItemGeneration]:
        item = await self.get_item(item_id, user_id)
        stmt = select(CanvasItemGeneration).where(
            CanvasItemGeneration.id == ensure_canvas_uuid(generation_id),
            CanvasItemGeneration.item_id == item.id,
        )
        generation = (await self.execute(stmt)).scalar_one_or_none()
        if not generation:
            raise NotFoundError("节点生成记录不存在", resource_id=generation_id, resource_type="canvas_generation")
        return item, generation

    async def list_generations(self, item_id: str, user_id: str, page: int = 1, size: int = 20) -> Tuple[List[CanvasItemGeneration], int]:
        item = await self.get_item(item_id, user_id)
        count_stmt = select(func.count(CanvasItemGeneration.id)).where(CanvasItemGeneration.item_id == item.id)
        total = (await self.execute(count_stmt)).scalar() or 0
        stmt = (
            select(CanvasItemGeneration)
            .where(CanvasItemGeneration.item_id == item.id)
            .order_by(desc(CanvasItemGeneration.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        generations = list((await self.execute(stmt)).scalars().all())
        return generations, total

    async def apply_generation(self, item_id: str, generation_id: str, user_id: str) -> Tuple[CanvasItem, CanvasItemGeneration]:
        item = await self.get_item(item_id, user_id)
        stmt = select(CanvasItemGeneration).where(
            CanvasItemGeneration.id == ensure_canvas_uuid(generation_id),
            CanvasItemGeneration.item_id == item.id,
        )
        generation = (await self.execute(stmt)).scalar_one_or_none()
        if not generation:
            raise NotFoundError("节点生成记录不存在", resource_id=generation_id, resource_type="canvas_generation")
        item.last_output_json = generation.result_payload_json or {}
        item.content_json = self._apply_generation_output(item.item_type, item.content_json or {}, generation.result_payload_json or {})
        item.last_run_status = generation.status
        item.last_run_error = generation.error_message
        await self.flush()
        await self.refresh(item)
        return item, generation

    async def create_pending_generation(
        self,
        item: CanvasItem,
        user_id: str,
        generation_type: str,
        request_payload: Dict[str, Any],
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> CanvasItemGeneration:
        generation = CanvasItemGeneration(
            item_id=item.id,
            document_id=item.document_id,
            user_id=ensure_canvas_uuid(user_id),
            generation_type=generation_type,
            request_payload_json=request_payload,
            status=CanvasRunStatus.PENDING.value,
            result_payload_json=result_payload or {},
            error_message=None,
        )
        self.add(generation)
        item.last_run_status = CanvasRunStatus.PENDING.value
        item.last_run_error = None
        item.last_output_json = result_payload or {}
        await self.flush()
        await self.refresh(generation)
        await self.refresh(item)
        return generation

    async def update_generation(
        self,
        generation: CanvasItemGeneration,
        item: CanvasItem,
        status: str,
        result_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> CanvasItemGeneration:
        merged_payload = dict(generation.result_payload_json or {})
        if result_payload:
            merged_payload.update(result_payload)

        generation.status = status
        generation.result_payload_json = merged_payload
        generation.error_message = error_message

        item.last_run_status = status
        item.last_run_error = error_message
        item.last_output_json = merged_payload
        if status == CanvasRunStatus.COMPLETED.value:
            item.content_json = self._apply_generation_output(item.item_type, item.content_json or {}, merged_payload)

        await self.flush()
        await self.refresh(generation)
        await self.refresh(item)
        return generation

    def _apply_generation_output(self, item_type: str, content: Dict[str, Any], result_payload: Dict[str, Any]) -> Dict[str, Any]:
        next_content = dict(content or {})
        if item_type == CanvasItemType.TEXT.value and result_payload.get("text"):
            next_content["text"] = result_payload["text"]
        if item_type == CanvasItemType.IMAGE.value and result_payload.get("result_image_url"):
            next_content["result_image_url"] = result_payload["result_image_url"]
        if item_type == CanvasItemType.VIDEO.value and result_payload.get("result_video_url"):
            next_content["result_video_url"] = result_payload["result_video_url"]
        if result_payload.get("provider_task_id"):
            next_content["provider_task_id"] = result_payload["provider_task_id"]
        if result_payload.get("task_id"):
            next_content["task_id"] = result_payload["task_id"]
        return next_content

    def _project_stage_item(self, item: CanvasItem) -> CanvasItem:
        return self._serialize_item(item, content=self._project_stage_content(item))

    def _project_stage_content(self, item: CanvasItem) -> Dict[str, Any]:
        content = dict(item.content_json or {})
        if item.item_type == CanvasItemType.TEXT.value:
            text = str(content.get("text") or content.get("value") or "").strip()
            preview = text[:240] + ("..." if len(text) > 240 else "")
            return {"text_preview": preview}
        if item.item_type == CanvasItemType.IMAGE.value:
            return self._project_preview_content(item)
        if item.item_type == CanvasItemType.VIDEO.value:
            return self._project_preview_content(item)
        return content

    def _project_preview_content(self, item: CanvasItem) -> Dict[str, Any]:
        content = dict(item.content_json or {})
        if item.item_type == CanvasItemType.IMAGE.value:
            return {
                "result_image_url": content.get("result_image_url", ""),
                "reference_image_url": content.get("reference_image_url", ""),
            }
        if item.item_type == CanvasItemType.VIDEO.value:
            return {
                "result_video_url": content.get("result_video_url", ""),
                "provider_task_id": content.get("provider_task_id", ""),
            }
        return content

    def _serialize_item(self, item: CanvasItem, *, content: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "id": item.id,
            "item_type": item.item_type,
            "title": item.title or "",
            "position_x": float(item.position_x or 0),
            "position_y": float(item.position_y or 0),
            "width": float(item.width or 0),
            "height": float(item.height or 0),
            "z_index": int(item.z_index or 0),
            "content": content if content is not None else dict(item.content_json or {}),
            "generation_config": dict(item.generation_config_json or {}),
            "last_run_status": item.last_run_status,
            "last_run_error": item.last_run_error,
            "last_output": dict(item.last_output_json or {}),
        }


class CanvasGenerationService(BaseService):
    async def prepare_text_generation(self, item_id: str, user_id: str, request: Dict[str, Any]) -> Tuple[CanvasItem, CanvasItemGeneration]:
        return await self._prepare_generation(item_id, user_id, CanvasGenerationType.TEXT.value, request)

    async def prepare_image_generation(self, item_id: str, user_id: str, request: Dict[str, Any]) -> Tuple[CanvasItem, CanvasItemGeneration]:
        return await self._prepare_generation(item_id, user_id, CanvasGenerationType.IMAGE.value, request)

    async def prepare_video_generation(self, item_id: str, user_id: str, request: Dict[str, Any]) -> Tuple[CanvasItem, CanvasItemGeneration]:
        return await self._prepare_generation(item_id, user_id, CanvasGenerationType.VIDEO.value, request)

    async def attach_task(self, generation_id: str, task_id: str) -> Tuple[CanvasItem, CanvasItemGeneration]:
        canvas_service = CanvasService(self.db_session)
        generation = await canvas_service.get_generation(generation_id)
        item = await canvas_service.get_item_by_id(str(generation.item_id))
        await canvas_service.update_generation(
            generation,
            item,
            CanvasRunStatus.PENDING.value,
            result_payload={"task_id": task_id},
        )
        return item, generation

    async def process_text_generation(self, generation_id: str) -> Dict[str, Any]:
        generation, item = await self._load_generation_and_item(generation_id, CanvasGenerationType.TEXT.value)
        canvas_service = CanvasService(self.db_session)
        try:
            await canvas_service.update_generation(generation, item, CanvasRunStatus.PROCESSING.value)
            request = generation.request_payload_json or {}
            api_key = await self._resolve_api_key(str(generation.user_id), request, item)
            provider = self._build_provider(api_key)
            response = await provider.completions(
                model=request.get("model") or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一个专业的中文创作助手。请直接输出适合写入画布节点的正文内容。"},
                    {"role": "user", "content": request["prompt"]},
                ],
            )
            text = response.choices[0].message.content.strip()
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.COMPLETED.value,
                result_payload={"text": text},
            )
            await self.commit()
            return {"generation_id": generation_id, "status": CanvasRunStatus.COMPLETED.value, "text": text}
        except Exception as exc:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                error_message=str(exc),
            )
            await self.commit()
            logger.exception("Canvas text generation failed: %s", generation_id)
            raise

    async def stream_text_generation(self, item_id: str, user_id: str, request: Dict[str, Any]) -> AsyncIterator[str]:
        item, generation = await self.prepare_text_generation(item_id, user_id, request)
        canvas_service = CanvasService(self.db_session)
        accumulated_text = ""

        try:
            await canvas_service.update_generation(generation, item, CanvasRunStatus.PROCESSING.value)
            await self.commit()
            yield self._encode_sse_event(
                "start",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.PROCESSING.value,
                },
            )

            request_payload = generation.request_payload_json or {}
            api_key = await self._resolve_api_key(str(generation.user_id), request_payload, item)
            provider = self._build_provider(api_key)
            stream = await provider.completions(
                model=request_payload.get("model") or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一个专业的中文创作助手。请直接输出适合写入画布节点的正文内容。"},
                    {"role": "user", "content": request_payload["prompt"]},
                ],
                stream=True,
            )

            async for delta in self._iterate_text_stream(stream):
                if not delta:
                    continue
                accumulated_text += delta
                yield self._encode_sse_event(
                    "delta",
                    {
                        "item_id": str(item.id),
                        "generation_id": str(generation.id),
                        "status": CanvasRunStatus.PROCESSING.value,
                        "delta": delta,
                        "text": accumulated_text,
                    },
                )

            final_text = accumulated_text.strip()
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.COMPLETED.value,
                result_payload={"text": final_text},
            )
            await self.commit()
            await self.refresh(item)
            await self.refresh(generation)
            yield self._encode_sse_event(
                "complete",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.COMPLETED.value,
                    "text": final_text,
                    "item": canvas_service._serialize_item(item),
                    "generation": self._serialize_generation(generation),
                },
            )
        except Exception as exc:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                error_message=str(exc),
            )
            await self.commit()
            logger.exception("Canvas text stream generation failed: %s", item_id)
            yield self._encode_sse_event(
                "fail",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.FAILED.value,
                    "error_message": str(exc),
                },
            )

    async def stream_image_generation(self, item_id: str, user_id: str, request: Dict[str, Any]) -> AsyncIterator[str]:
        item, generation = await self.prepare_image_generation(item_id, user_id, request)
        canvas_service = CanvasService(self.db_session)

        try:
            await canvas_service.update_generation(generation, item, CanvasRunStatus.PROCESSING.value)
            await self.commit()
            yield self._encode_sse_event(
                "start",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.PROCESSING.value,
                },
            )

            request_payload = generation.request_payload_json or {}
            api_key = await self._resolve_api_key(str(generation.user_id), request_payload, item)
            provider = self._build_provider(api_key)
            image_kwargs: Dict[str, Any] = {}
            if api_key.provider.lower() == "custom":
                reference_images = (request_payload.get("options") or {}).get("reference_image_urls") or []
                if reference_images:
                    image_kwargs["reference_images"] = reference_images

            response = await provider.generate_image(
                prompt=request_payload["prompt"],
                model=request_payload.get("model"),
                **image_kwargs,
            )
            image_url = await self._resolve_image_result(response, str(generation.user_id))
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.COMPLETED.value,
                result_payload={"result_image_url": image_url},
            )
            await self.commit()
            await self.refresh(item)
            await self.refresh(generation)
            yield self._encode_sse_event(
                "complete",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.COMPLETED.value,
                    "result_image_url": image_url,
                    "item": canvas_service._serialize_item(item),
                    "generation": self._serialize_generation(generation),
                },
            )
        except Exception as exc:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                error_message=str(exc),
            )
            await self.commit()
            logger.exception("Canvas image stream generation failed: %s", item_id)
            yield self._encode_sse_event(
                "fail",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.FAILED.value,
                    "error_message": str(exc),
                },
            )

    async def process_image_generation(self, generation_id: str) -> Dict[str, Any]:
        generation, item = await self._load_generation_and_item(generation_id, CanvasGenerationType.IMAGE.value)
        canvas_service = CanvasService(self.db_session)
        try:
            await canvas_service.update_generation(generation, item, CanvasRunStatus.PROCESSING.value)
            request = generation.request_payload_json or {}
            api_key = await self._resolve_api_key(str(generation.user_id), request, item)
            provider = self._build_provider(api_key)
            image_kwargs: Dict[str, Any] = {}
            if api_key.provider.lower() == "custom":
                reference_images = (request.get("options") or {}).get("reference_image_urls") or []
                if reference_images:
                    image_kwargs["reference_images"] = reference_images
            response = await provider.generate_image(
                prompt=request["prompt"],
                model=request.get("model"),
                **image_kwargs,
            )
            image_url = await self._resolve_image_result(response, str(generation.user_id))
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.COMPLETED.value,
                result_payload={"result_image_url": image_url},
            )
            await self.commit()
            return {"generation_id": generation_id, "status": CanvasRunStatus.COMPLETED.value, "result_image_url": image_url}
        except Exception as exc:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                error_message=str(exc),
            )
            await self.commit()
            logger.exception("Canvas image generation failed: %s", generation_id)
            raise

    async def stream_video_generation(self, item_id: str, user_id: str, request: Dict[str, Any]) -> AsyncIterator[str]:
        item, generation = await self.prepare_video_generation(item_id, user_id, request)
        canvas_service = CanvasService(self.db_session)

        try:
            await canvas_service.update_generation(generation, item, CanvasRunStatus.PROCESSING.value)
            await self.commit()
            yield self._encode_sse_event(
                "start",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.PROCESSING.value,
                },
            )

            request_payload = generation.request_payload_json or {}
            api_key = await self._resolve_api_key(str(generation.user_id), request_payload, item)
            if api_key.provider.lower() not in {"vectorengine", "custom"}:
                raise BusinessLogicError("当前 API Key 不支持视频生成")

            provider = VectorEngineProvider(
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url or "https://api.vectorengine.ai/v1",
            )
            options = request_payload.get("options") or {}
            reference_images = options.get("reference_image_urls") or item.content_json.get("reference_image_urls") or []
            response = await provider.create_video(
                prompt=request_payload["prompt"],
                images=reference_images,
                model=request_payload.get("model") or "veo_3_1-fast",
                **options,
            )

            provider_task_id = response.get("id") or response.get("task_id")
            direct_video_url = self._extract_video_url(response)
            if direct_video_url:
                stored_video_url = await self._store_remote_video(direct_video_url, str(generation.user_id))
                await canvas_service.update_generation(
                    generation,
                    item,
                    CanvasRunStatus.COMPLETED.value,
                    result_payload={
                        "provider_task_id": provider_task_id,
                        "provider_response": response,
                        "result_video_url": stored_video_url,
                    },
                )
                await self.commit()
                await self.refresh(item)
                await self.refresh(generation)
                yield self._encode_sse_event(
                    "complete",
                    {
                        "item_id": str(item.id),
                        "generation_id": str(generation.id),
                        "status": CanvasRunStatus.COMPLETED.value,
                        "result_video_url": stored_video_url,
                        "provider_task_id": provider_task_id,
                        "item": canvas_service._serialize_item(item),
                        "generation": self._serialize_generation(generation),
                    },
                )
                return

            if not provider_task_id:
                raise BusinessLogicError("视频任务已提交，但未返回 provider task id")

            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.PROCESSING.value,
                result_payload={"provider_task_id": provider_task_id, "provider_response": response},
            )
            await self.commit()
            yield self._encode_sse_event(
                "progress",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.PROCESSING.value,
                    "provider_task_id": provider_task_id,
                    "provider_payload": response,
                },
            )

            async for progress_payload in self._iterate_video_progress(provider, provider_task_id):
                provider_status = str(progress_payload.get("status") or progress_payload.get("state") or "").lower()
                normalized_status = self._normalize_video_provider_status(provider_status)
                provider_video_url = self._extract_video_url(progress_payload)

                if provider_video_url and normalized_status == CanvasRunStatus.COMPLETED.value:
                    stored_video_url = await self._store_remote_video(provider_video_url, str(generation.user_id))
                    await canvas_service.update_generation(
                        generation,
                        item,
                        CanvasRunStatus.COMPLETED.value,
                        result_payload={
                            "provider_task_id": provider_task_id,
                            "provider_response": progress_payload,
                            "result_video_url": stored_video_url,
                        },
                    )
                    await self.commit()
                    await self.refresh(item)
                    await self.refresh(generation)
                    yield self._encode_sse_event(
                        "complete",
                        {
                            "item_id": str(item.id),
                            "generation_id": str(generation.id),
                            "status": CanvasRunStatus.COMPLETED.value,
                            "provider_task_id": provider_task_id,
                            "result_video_url": stored_video_url,
                            "provider_payload": progress_payload,
                            "item": canvas_service._serialize_item(item),
                            "generation": self._serialize_generation(generation),
                        },
                    )
                    return

                if normalized_status == CanvasRunStatus.FAILED.value:
                    error_message = progress_payload.get("message") or progress_payload.get("error") or "视频生成失败"
                    await canvas_service.update_generation(
                        generation,
                        item,
                        CanvasRunStatus.FAILED.value,
                        result_payload={
                            "provider_task_id": provider_task_id,
                            "provider_response": progress_payload,
                        },
                        error_message=error_message,
                    )
                    await self.commit()
                    yield self._encode_sse_event(
                        "fail",
                        {
                            "item_id": str(item.id),
                            "generation_id": str(generation.id),
                            "status": CanvasRunStatus.FAILED.value,
                            "provider_task_id": provider_task_id,
                            "error_message": error_message,
                            "provider_payload": progress_payload,
                        },
                    )
                    return

                await canvas_service.update_generation(
                    generation,
                    item,
                    normalized_status,
                    result_payload={
                        "provider_task_id": provider_task_id,
                        "provider_response": progress_payload,
                    },
                )
                await self.commit()
                yield self._encode_sse_event(
                    "progress",
                    {
                        "item_id": str(item.id),
                        "generation_id": str(generation.id),
                        "status": normalized_status,
                        "provider_task_id": provider_task_id,
                        "provider_payload": progress_payload,
                    },
                )

            raise BusinessLogicError("视频生成超时，请稍后查看任务状态")
        except Exception as exc:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                error_message=str(exc),
            )
            await self.commit()
            logger.exception("Canvas video stream generation failed: %s", item_id)
            yield self._encode_sse_event(
                "fail",
                {
                    "item_id": str(item.id),
                    "generation_id": str(generation.id),
                    "status": CanvasRunStatus.FAILED.value,
                    "error_message": str(exc),
                },
            )

    async def process_video_generation(self, generation_id: str) -> Dict[str, Any]:
        generation, item = await self._load_generation_and_item(generation_id, CanvasGenerationType.VIDEO.value)
        canvas_service = CanvasService(self.db_session)
        try:
            await canvas_service.update_generation(generation, item, CanvasRunStatus.PROCESSING.value)
            request = generation.request_payload_json or {}
            api_key = await self._resolve_api_key(str(generation.user_id), request, item)
            if api_key.provider.lower() not in {"vectorengine", "custom"}:
                raise BusinessLogicError("当前 API Key 不支持视频生成")

            provider = VectorEngineProvider(
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url or "https://api.vectorengine.ai/v1",
            )
            options = request.get("options") or {}
            reference_images = options.get("reference_image_urls") or item.content_json.get("reference_image_urls") or []
            response = await provider.create_video(
                prompt=request["prompt"],
                images=reference_images,
                model=request.get("model") or "veo_3_1-fast",
                **options,
            )

            provider_task_id = response.get("id") or response.get("task_id")
            direct_video_url = self._extract_video_url(response)
            if direct_video_url:
                stored_video_url = await self._store_remote_video(direct_video_url, str(generation.user_id))
                await canvas_service.update_generation(
                    generation,
                    item,
                    CanvasRunStatus.COMPLETED.value,
                    result_payload={
                        "provider_task_id": provider_task_id,
                        "provider_response": response,
                        "result_video_url": stored_video_url,
                    },
                )
                await self.commit()
                return {"generation_id": generation_id, "status": CanvasRunStatus.COMPLETED.value, "result_video_url": stored_video_url}

            if not provider_task_id:
                raise BusinessLogicError("视频任务已提交，但未返回 provider task id")

            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.PROCESSING.value,
                result_payload={"provider_task_id": provider_task_id, "provider_response": response},
            )

            video_url = await self._poll_video_result(provider, provider_task_id)
            stored_video_url = await self._store_remote_video(video_url, str(generation.user_id))
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.COMPLETED.value,
                result_payload={"provider_task_id": provider_task_id, "result_video_url": stored_video_url},
            )
            await self.commit()
            return {"generation_id": generation_id, "status": CanvasRunStatus.COMPLETED.value, "result_video_url": stored_video_url}
        except Exception as exc:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                error_message=str(exc),
            )
            await self.commit()
            logger.exception("Canvas video generation failed: %s", generation_id)
            raise

    async def get_video_task_status(self, document_id: str, item_id: str, generation_id: str, user_id: str) -> Dict[str, Any]:
        canvas_service = CanvasService(self.db_session)
        item, generation = await canvas_service.get_item_generation(item_id, generation_id, user_id)
        if str(item.document_id) != str(ensure_canvas_uuid(document_id)):
            raise NotFoundError("画布节点不存在", resource_id=item_id, resource_type="canvas_item")
        self._ensure_item_type_matches(item, CanvasGenerationType.VIDEO.value)

        request = generation.request_payload_json or {}
        provider_task_id = str(
            (generation.result_payload_json or {}).get("provider_task_id")
            or (generation.result_payload_json or {}).get("task_id")
            or ""
        ).strip()

        result_video_url = str((generation.result_payload_json or {}).get("result_video_url") or "").strip()
        if generation.status == CanvasRunStatus.COMPLETED.value and result_video_url:
            return {
                "task_id": str(generation.id),
                "provider_task_id": provider_task_id or None,
                "status": generation.status,
                "result_video_url": result_video_url,
                "error_message": generation.error_message,
                "provider_payload": generation.result_payload_json or {},
                "item": item,
            }

        if not provider_task_id:
            return {
                "task_id": str(generation.id),
                "provider_task_id": None,
                "status": generation.status,
                "result_video_url": result_video_url or None,
                "error_message": generation.error_message,
                "provider_payload": generation.result_payload_json or {},
                "item": item,
            }

        api_key = await self._resolve_api_key(user_id, request, item)
        provider = VectorEngineProvider(
            api_key=api_key.get_api_key(),
            base_url=api_key.base_url or "https://api.vectorengine.ai/v1",
        )
        status_payload = await provider.get_task_status(provider_task_id)
        provider_status = str(status_payload.get("status") or status_payload.get("state") or generation.status or "").lower()
        provider_video_url = self._extract_video_url(status_payload)
        if not provider_video_url and provider_status in {"completed", "succeeded", "success", "done"}:
            content_payload = await provider.get_video_content(provider_task_id)
            provider_video_url = self._extract_video_url(content_payload)
            if provider_video_url:
                status_payload = {**status_payload, "content": content_payload}

        normalized_status = self._normalize_video_provider_status(provider_status)
        if provider_video_url and normalized_status == CanvasRunStatus.COMPLETED.value:
            stored_video_url = await self._store_remote_video(provider_video_url, user_id)
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.COMPLETED.value,
                result_payload={
                    "provider_task_id": provider_task_id,
                    "provider_response": status_payload,
                    "result_video_url": stored_video_url,
                },
            )
            await self.commit()
            result_video_url = stored_video_url
        elif normalized_status == CanvasRunStatus.FAILED.value:
            await canvas_service.update_generation(
                generation,
                item,
                CanvasRunStatus.FAILED.value,
                result_payload={
                    "provider_task_id": provider_task_id,
                    "provider_response": status_payload,
                },
                error_message=status_payload.get("message") or status_payload.get("error") or generation.error_message,
            )
            await self.commit()
        elif normalized_status != generation.status:
            await canvas_service.update_generation(
                generation,
                item,
                normalized_status,
                result_payload={
                    "provider_task_id": provider_task_id,
                    "provider_response": status_payload,
                },
            )
            await self.commit()

        await self.refresh(item)
        await self.refresh(generation)
        return {
            "task_id": str(generation.id),
            "provider_task_id": provider_task_id,
            "status": generation.status,
            "result_video_url": (generation.result_payload_json or {}).get("result_video_url"),
            "error_message": generation.error_message,
            "provider_payload": generation.result_payload_json or {},
            "item": item,
        }

    async def upload_video_override(self, document_id: str, item_id: str, user_id: str, file: UploadFile) -> Dict[str, Any]:
        canvas_service = CanvasService(self.db_session)
        item = await canvas_service.get_item(item_id, user_id)
        if str(item.document_id) != str(ensure_canvas_uuid(document_id)):
            raise NotFoundError("画布节点不存在", resource_id=item_id, resource_type="canvas_item")
        self._ensure_item_type_matches(item, CanvasGenerationType.VIDEO.value)

        storage_client = await get_storage_client()
        storage_result = await storage_client.upload_file(
            user_id=user_id,
            file=file,
            metadata={
                "user_id": user_id,
                "canvas_document_id": document_id,
                "canvas_item_id": item_id,
                "file_type": "video",
            },
        )

        object_key = storage_result["object_key"]
        item.content_json = {
            **(item.content_json or {}),
            "result_video_url": object_key,
            "result_video_object_key": object_key,
        }
        item.last_run_status = CanvasRunStatus.COMPLETED.value
        item.last_run_error = None
        item.last_output_json = {
            **(item.last_output_json or {}),
            "result_video_url": object_key,
        }
        await self.flush()
        await self.refresh(item)
        return {"item": item, "storage_info": storage_result}

    async def _prepare_generation(
        self,
        item_id: str,
        user_id: str,
        generation_type: str,
        request: Dict[str, Any],
    ) -> Tuple[CanvasItem, CanvasItemGeneration]:
        canvas_service = CanvasService(self.db_session)
        item = await canvas_service.get_item(item_id, user_id)
        self._ensure_item_type_matches(item, generation_type)
        normalized_request = await self._normalize_request(item, user_id, generation_type, request)
        generation = await canvas_service.create_pending_generation(
            item,
            user_id,
            generation_type,
            normalized_request,
        )
        return item, generation

    async def _normalize_request(
        self,
        item: CanvasItem,
        user_id: str,
        generation_type: str,
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt_tokens = self._normalize_prompt_tokens(request.get("prompt_tokens") or item.content_json.get("promptTokens") or [])
        resolved_mentions = self._normalize_resolved_mentions(
            request.get("resolved_mentions")
            or item.content_json.get("resolvedMentions")
            or item.content_json.get("resolved_mentions")
            or []
        )
        prompt_plain_text = (
            request.get("prompt_plain_text")
            or item.content_json.get("promptPlainText")
            or item.content_json.get("prompt_plain_text")
            or request.get("prompt")
            or item.content_json.get("prompt")
            or ""
        ).strip()
        prompt = self._build_prompt_text(prompt_tokens, resolved_mentions, fallback=prompt_plain_text)
        if not prompt:
            type_label = {
                CanvasGenerationType.TEXT.value: "文本",
                CanvasGenerationType.IMAGE.value: "图片",
                CanvasGenerationType.VIDEO.value: "视频",
            }[generation_type]
            raise BusinessLogicError(f"{type_label}节点缺少 prompt")

        api_key_id = request.get("api_key_id") or item.generation_config_json.get("api_key_id")
        if not api_key_id:
            raise BusinessLogicError("缺少 api_key_id")

        model = request.get("model") or item.generation_config_json.get("model")
        options = dict(item.content_json.get("options") or {})
        options.update(request.get("options") or {})

        normalized = {
            "prompt": prompt,
            "prompt_plain_text": prompt_plain_text,
            "prompt_tokens": prompt_tokens,
            "resolved_mentions": resolved_mentions,
            "api_key_id": str(api_key_id),
            "model": model,
            "options": options,
        }

        reference_image_urls = self._collect_reference_image_urls(prompt_tokens, resolved_mentions)
        reference_text_ids = self._collect_reference_text_ids(resolved_mentions)

        if generation_type == CanvasGenerationType.IMAGE.value and reference_image_urls:
            normalized["options"]["reference_image_urls"] = reference_image_urls

        if generation_type == CanvasGenerationType.VIDEO.value:
            normalized["options"]["reference_image_urls"] = (
                options.get("reference_image_urls")
                or reference_image_urls
                or item.content_json.get("reference_image_urls")
                or []
            )
            normalized["options"]["reference_text_ids"] = (
                options.get("reference_text_ids")
                or reference_text_ids
                or item.content_json.get("reference_text_ids")
                or []
            )

        return normalized

    def _normalize_prompt_tokens(self, raw_tokens: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_tokens, list):
            return []
        return [dict(token) for token in raw_tokens if isinstance(token, dict)]

    def _normalize_resolved_mentions(self, raw_mentions: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_mentions, list):
            return []
        return [dict(mention) for mention in raw_mentions if isinstance(mention, dict)]

    def _build_prompt_text(
        self,
        prompt_tokens: List[Dict[str, Any]],
        resolved_mentions: List[Dict[str, Any]],
        *,
        fallback: str = "",
    ) -> str:
        if not prompt_tokens:
            return self._normalize_prompt_spacing(fallback)

        mention_by_id = {}
        mention_by_node_key = {}
        for mention in resolved_mentions:
            if str(mention.get("status") or "").strip() != "resolved":
                continue
            mention_id = str(mention.get("mentionId") or "").strip()
            if mention_id:
                mention_by_id[mention_id] = mention
            node_key = self._build_node_key(mention.get("nodeType"), mention.get("nodeId"))
            if node_key != ":" and node_key not in mention_by_node_key:
                mention_by_node_key[node_key] = mention

        sections: List[str] = []
        for token in prompt_tokens:
            token_type = str(token.get("type") or "").strip()
            if token_type == "text":
                sections.append(str(token.get("text") or ""))
                continue
            if token_type != "mention":
                continue

            mention = None
            mention_id = str(token.get("mentionId") or "").strip()
            if mention_id:
                mention = mention_by_id.get(mention_id)
            if mention is None:
                mention = mention_by_node_key.get(self._build_node_key(token.get("nodeType"), token.get("nodeId")))
            if mention is None:
                sections.append(self._format_raw_mention_title(token))
                continue

            node_type = str(mention.get("nodeType") or "").strip()
            if node_type == CanvasItemType.IMAGE.value:
                continue
            if node_type == CanvasItemType.TEXT.value:
                inline_text = self._build_resolved_text_inline_content(mention)
                if inline_text:
                    sections.append(inline_text)
                continue
            sections.append(self._format_raw_mention_title(token))

        return self._normalize_prompt_spacing("".join(sections))

    def _collect_reference_image_urls(
        self,
        prompt_tokens: List[Dict[str, Any]],
        resolved_mentions: List[Dict[str, Any]],
        *,
        limit: int = REFERENCE_IMAGE_LIMIT,
    ) -> List[str]:
        if not prompt_tokens or not resolved_mentions:
            return []

        mention_by_id = {}
        mention_by_node_key = {}
        for mention in resolved_mentions:
            if str(mention.get("status") or "").strip() != "resolved":
                continue
            mention_id = str(mention.get("mentionId") or "").strip()
            if mention_id:
                mention_by_id[mention_id] = mention
            node_key = self._build_node_key(mention.get("nodeType"), mention.get("nodeId"))
            if node_key != ":" and node_key not in mention_by_node_key:
                mention_by_node_key[node_key] = mention

        results: List[str] = []
        seen_node_ids = set()
        for token in prompt_tokens:
            if str(token.get("type") or "").strip() != "mention":
                continue
            mention = None
            mention_id = str(token.get("mentionId") or "").strip()
            if mention_id:
                mention = mention_by_id.get(mention_id)
            if mention is None:
                mention = mention_by_node_key.get(self._build_node_key(token.get("nodeType"), token.get("nodeId")))
            if mention is None:
                continue
            if str(mention.get("nodeType") or "").strip() != CanvasItemType.IMAGE.value:
                continue

            node_id = str(mention.get("nodeId") or "").strip()
            if node_id and node_id in seen_node_ids:
                continue

            resolved_content = mention.get("resolvedContent") or {}
            if not isinstance(resolved_content, dict):
                resolved_content = {}
            image_ref = str(
                resolved_content.get("object_key")
                or resolved_content.get("objectKey")
                or resolved_content.get("url")
                or ""
            ).strip()
            if not image_ref:
                continue

            results.append(image_ref)
            if node_id:
                seen_node_ids.add(node_id)
            if len(results) >= limit:
                break
        return results

    def _collect_reference_text_ids(self, resolved_mentions: List[Dict[str, Any]]) -> List[str]:
        text_ids: List[str] = []
        seen = set()
        for mention in resolved_mentions:
            if str(mention.get("status") or "").strip() != "resolved":
                continue
            if str(mention.get("nodeType") or "").strip() != CanvasItemType.TEXT.value:
                continue
            node_id = str(mention.get("nodeId") or "").strip()
            if not node_id or node_id in seen:
                continue
            text_ids.append(node_id)
            seen.add(node_id)
        return text_ids

    def _build_node_key(self, node_type: Any, node_id: Any) -> str:
        return f"{str(node_type or '').strip()}:{str(node_id or '').strip()}"

    def _format_raw_mention_title(self, token: Dict[str, Any]) -> str:
        title = str(token.get("nodeTitleSnapshot") or token.get("nodeId") or "").strip()
        return f"@{title}" if title else ""

    def _build_resolved_text_inline_content(self, mention: Dict[str, Any]) -> str:
        resolved_content = mention.get("resolvedContent") or {}
        if not isinstance(resolved_content, dict):
            resolved_content = {}
        return self._sanitize_reference_text(str(resolved_content.get("text") or ""))

    def _sanitize_reference_text(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = PROMPT_BREAK_TAG_PATTERN.sub("\n", text)
        text = PROMPT_LIST_ITEM_PATTERN.sub("- ", text)
        text = PROMPT_LIST_ITEM_CLOSE_PATTERN.sub("\n", text)
        text = PROMPT_BLOCK_TAG_PATTERN.sub("\n", text)
        text = PROMPT_HTML_TAG_PATTERN.sub("", text)
        text = html.unescape(text)

        normalized_lines: List[str] = []
        for line in text.split("\n"):
            trimmed_line = PROMPT_SPACE_PATTERN.sub(" ", line).strip()
            if not trimmed_line:
                if normalized_lines and normalized_lines[-1] != "":
                    normalized_lines.append("")
                continue
            normalized_lines.append(trimmed_line)

        normalized = "\n".join(normalized_lines).strip()
        normalized = PROMPT_BLANK_LINE_PATTERN.sub("\n\n", normalized)
        if len(normalized) <= REFERENCE_TEXT_LIMIT:
            return normalized
        return normalized[:REFERENCE_TEXT_LIMIT].rstrip() + "..."

    def _normalize_prompt_spacing(self, value: str) -> str:
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
        text = PROMPT_SPACE_PATTERN.sub(" ", text)
        text = text.replace(" \n", "\n").replace("\n ", "\n")
        text = PROMPT_BLANK_LINE_PATTERN.sub("\n\n", text)
        return text.strip()

    def _ensure_item_type_matches(self, item: CanvasItem, generation_type: str) -> None:
        expected = {
            CanvasGenerationType.TEXT.value: CanvasItemType.TEXT.value,
            CanvasGenerationType.IMAGE.value: CanvasItemType.IMAGE.value,
            CanvasGenerationType.VIDEO.value: CanvasItemType.VIDEO.value,
        }[generation_type]
        if item.item_type != expected:
            raise BusinessLogicError(f"该节点不是{generation_type}节点")

    async def _load_generation_and_item(self, generation_id: str, generation_type: str) -> Tuple[CanvasItemGeneration, CanvasItem]:
        canvas_service = CanvasService(self.db_session)
        generation = await canvas_service.get_generation(generation_id)
        item = await canvas_service.get_item_by_id(str(generation.item_id))
        if generation.generation_type != generation_type:
            raise BusinessLogicError("节点生成记录类型不匹配")
        return generation, item

    async def _resolve_api_key(self, user_id: str, request: Dict[str, Any], item: CanvasItem) -> APIKey:
        api_key_id = request.get("api_key_id") or item.generation_config_json.get("api_key_id")
        if not api_key_id:
            raise BusinessLogicError("缺少 api_key_id")
        service = APIKeyService(self.db_session)
        return await service.get_api_key_by_id(str(api_key_id), str(user_id))

    def _build_provider(self, api_key: APIKey):
        return ProviderFactory.create(
            provider=api_key.provider,
            api_key=api_key.get_api_key(),
            max_concurrency=5,
            base_url=api_key.base_url if api_key.base_url else None,
        )

    async def _iterate_text_stream(self, stream: Any) -> AsyncIterator[str]:
        if hasattr(stream, "__aiter__"):
            async for chunk in stream:
                delta = self._extract_text_delta(chunk)
                if delta:
                    yield delta
            return

        fallback_text = self._extract_completion_text(stream)
        if fallback_text:
            yield fallback_text

    def _extract_text_delta(self, chunk: Any) -> str:
        choices = chunk.get("choices") if isinstance(chunk, dict) else getattr(chunk, "choices", None)
        if not choices:
            return ""
        choice = choices[0]
        delta = choice.get("delta") if isinstance(choice, dict) else getattr(choice, "delta", None)
        if delta is None:
            return ""
        content = delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", None)
        return self._normalize_completion_content(content)

    def _extract_completion_text(self, response: Any) -> str:
        choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", None)
        if not choices:
            return ""
        choice = choices[0]
        message = choice.get("message") if isinstance(choice, dict) else getattr(choice, "message", None)
        if message is None:
            return ""
        content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
        return self._normalize_completion_content(content).strip()

    def _normalize_completion_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for entry in content:
                if isinstance(entry, str):
                    parts.append(entry)
                    continue
                if not isinstance(entry, dict):
                    continue
                text_value = entry.get("text")
                if isinstance(text_value, dict):
                    text_value = text_value.get("value") or text_value.get("text")
                if text_value:
                    parts.append(str(text_value))
                    continue
                nested_content = entry.get("content")
                if nested_content:
                    parts.append(str(nested_content))
            return "".join(parts)
        return str(content or "")

    def _serialize_generation(self, generation: CanvasItemGeneration) -> Dict[str, Any]:
        return {
            **generation.to_dict(),
            "request_payload": generation.request_payload_json,
            "result_payload": generation.result_payload_json,
        }

    def _encode_sse_event(self, event_name: str, payload: Dict[str, Any]) -> str:
        return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

    async def _resolve_image_result(self, response: Any, user_id: str) -> str:
        image_data = response.data[0]
        if hasattr(image_data, "url") and image_data.url:
            return image_data.url
        if hasattr(image_data, "b64_json") and image_data.b64_json:
            content_type = getattr(image_data, "mime", "image/png")
            raw = base64.b64decode(image_data.b64_json)
            ext = "png" if "png" in content_type else "jpg"
            storage_client = await get_storage_client()
            file_id = str(uuid.uuid4())
            upload_file = UploadFile(filename=f"{file_id}.{ext}", file=io.BytesIO(raw))
            storage = await storage_client.upload_file(
                user_id=user_id,
                file=upload_file,
                metadata={"user_id": user_id, "file_id": file_id, "file_type": content_type},
            )
            return storage["object_key"]
        raise BusinessLogicError("图片生成结果不包含可用图片")

    async def _store_remote_video(self, video_url: str, user_id: str) -> str:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
            response = await client.get(video_url)
            response.raise_for_status()

        storage_client = await get_storage_client()
        upload_file = UploadFile(filename=f"{uuid.uuid4()}.mp4", file=io.BytesIO(response.content))
        storage = await storage_client.upload_file(
            user_id=user_id,
            file=upload_file,
            metadata={"user_id": user_id, "file_type": "video/mp4"},
        )
        return storage["object_key"]

    async def _poll_video_result(self, provider: VectorEngineProvider, provider_task_id: str) -> str:
        for _ in range(60):
            status_payload = await provider.get_task_status(provider_task_id)
            state = str(status_payload.get("status") or status_payload.get("state") or "").lower()
            if state in {"completed", "succeeded", "success", "done"}:
                video_url = self._extract_video_url(status_payload)
                if video_url:
                    return video_url
                content_payload = await provider.get_video_content(provider_task_id)
                video_url = self._extract_video_url(content_payload)
                if video_url:
                    return video_url
                raise BusinessLogicError("视频任务已完成，但未返回可用 video_url")
            if state in {"failed", "error", "cancelled", "canceled"}:
                raise BusinessLogicError(status_payload.get("message") or status_payload.get("error") or "视频生成失败")
            await asyncio.sleep(5)
        raise BusinessLogicError("视频生成超时，请稍后查看任务状态")

    async def _iterate_video_progress(self, provider: VectorEngineProvider, provider_task_id: str) -> AsyncIterator[Dict[str, Any]]:
        for _ in range(60):
            status_payload = await provider.get_task_status(provider_task_id)
            state = str(status_payload.get("status") or status_payload.get("state") or "").lower()
            if state in {"completed", "succeeded", "success", "done"}:
                video_url = self._extract_video_url(status_payload)
                if not video_url:
                    content_payload = await provider.get_video_content(provider_task_id)
                    video_url = self._extract_video_url(content_payload)
                    if video_url:
                        status_payload = {**status_payload, "content": content_payload, "video_url": video_url}
                if not video_url:
                    raise BusinessLogicError("视频任务已完成，但未返回可用 video_url")
            yield status_payload
            if state in {"completed", "succeeded", "success", "done", "failed", "error", "cancelled", "canceled"}:
                return
            await asyncio.sleep(5)

    def _extract_video_url(self, payload: Dict[str, Any]) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        direct_candidates = [
            payload.get("video_url"),
            payload.get("url"),
        ]
        detail = payload.get("detail") or payload.get("data") or {}
        if isinstance(detail, dict):
            direct_candidates.extend([detail.get("video_url"), detail.get("url")])
        for candidate in direct_candidates:
            if candidate:
                return candidate
        return None

    def _normalize_video_provider_status(self, provider_status: str) -> str:
        normalized = str(provider_status or "").strip().lower()
        if normalized in {"completed", "succeeded", "success", "done"}:
            return CanvasRunStatus.COMPLETED.value
        if normalized in {"failed", "error", "cancelled", "canceled"}:
            return CanvasRunStatus.FAILED.value
        if normalized in {"processing", "running", "pending", "queued", "submitted"}:
            return CanvasRunStatus.PROCESSING.value if normalized in {"processing", "running"} else CanvasRunStatus.PENDING.value
        return CanvasRunStatus.PROCESSING.value


__all__ = ["CanvasGenerationService", "CanvasService"]
