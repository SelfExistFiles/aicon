from __future__ import annotations

from typing import Any

from src.assistant.types import ToolEffect


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


class CanvasAssistantCanvasInspectionTools:
    def __init__(self, service: Any | None = None) -> None:
        self.service = service

    async def inspect_graph(self, document_id: str, user_id: str) -> dict[str, Any]:
        # inspect_graph 返回“可再压缩”的事实快照；真正进 prompt 前还会二次裁剪。
        if self.service is None:
            return {"document": {"id": document_id}, "items": [], "connections": [], "counts": {"items": 0, "connections": 0}}
        graph = await self.service.get_graph(document_id, user_id)
        items = [self._serialize_item(item) for item in list(graph.get("items") or [])]
        connections = [self._serialize_connection(connection) for connection in list(graph.get("connections") or [])]
        return {
            "document": self._serialize_document(graph.get("document")),
            "items": items,
            "connections": connections,
            "counts": {"items": len(items), "connections": len(connections)},
        }

    async def find_items(self, document_id: str, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        snapshot = await self.inspect_graph(document_id, user_id)
        normalized_query = _normalize_text(query)
        if not normalized_query:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in list(snapshot.get("items") or []):
            title = _normalize_text(item.get("title"))
            item_type = _normalize_text(item.get("item_type"))
            content = item.get("content") or {}
            text_blob = " ".join(
                [
                    title,
                    item_type,
                    _normalize_text(content.get("text")),
                    _normalize_text(content.get("prompt")),
                    _normalize_text(content.get("text_preview")),
                ]
            )
            score = 0
            if title and normalized_query in title:
                score += 5
            if item_type and normalized_query in item_type:
                score += 3
            if normalized_query in text_blob:
                score += 2
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]

    async def read_item_detail(self, document_id: str, user_id: str, item_id: str) -> dict[str, Any]:
        if self.service is None:
            return {"id": item_id}
        item = await self.service.get_item(item_id, user_id)
        serialized = self._serialize_item(item)
        serialized["document_id"] = document_id
        return serialized

    async def read_neighbors(self, document_id: str, user_id: str, item_ids: list[str]) -> dict[str, Any]:
        snapshot = await self.inspect_graph(document_id, user_id)
        id_set = {str(item_id).strip() for item_id in item_ids if str(item_id).strip()}
        connections = list(snapshot.get("connections") or [])
        neighbor_ids = set()
        for connection in connections:
            source_item_id = str(connection.get("source_item_id") or "").strip()
            target_item_id = str(connection.get("target_item_id") or "").strip()
            if source_item_id in id_set and target_item_id:
                neighbor_ids.add(target_item_id)
            if target_item_id in id_set and source_item_id:
                neighbor_ids.add(source_item_id)
        items = [item for item in list(snapshot.get("items") or []) if str(item.get("id") or "").strip() in neighbor_ids]
        return {"items": items, "connections": connections}

    def _serialize_document(self, document: Any) -> dict[str, Any]:
        if document is None:
            return {}
        if isinstance(document, dict):
            return dict(document)
        if hasattr(document, "to_dict"):
            return dict(document.to_dict())
        return {"id": getattr(document, "id", ""), "title": getattr(document, "title", "")}

    def _serialize_item(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return {
                "id": str(item.get("id") or ""),
                "item_type": item.get("item_type"),
                "title": item.get("title", ""),
                "content": dict(item.get("content") or {}),
            }
        base = dict(item.to_dict()) if hasattr(item, "to_dict") else {}
        return {
            "id": str(base.get("id", getattr(item, "id", ""))),
            "item_type": base.get("item_type", getattr(item, "item_type", "")),
            "title": base.get("title", getattr(item, "title", "")),
            "content": dict(base.get("content_json", getattr(item, "content_json", {})) or {}),
        }

    def _serialize_connection(self, connection: Any) -> dict[str, Any]:
        if isinstance(connection, dict):
            return {
                **connection,
                "id": str(connection.get("id") or ""),
                "source_item_id": str(connection.get("source_item_id") or ""),
                "target_item_id": str(connection.get("target_item_id") or ""),
            }
        if hasattr(connection, "to_dict"):
            payload = dict(connection.to_dict())
            payload["id"] = str(payload.get("id") or "")
            payload["source_item_id"] = str(payload.get("source_item_id") or "")
            payload["target_item_id"] = str(payload.get("target_item_id") or "")
            return payload
        return {
            "id": str(getattr(connection, "id", "")),
            "source_item_id": str(getattr(connection, "source_item_id", "")),
            "target_item_id": str(getattr(connection, "target_item_id", "")),
            "source_handle": getattr(connection, "source_handle", ""),
            "target_handle": getattr(connection, "target_handle", ""),
        }


class CanvasAssistantCanvasExecutionTools:
    def __init__(self, service: Any | None = None) -> None:
        self.service = service

    async def _commit_if_possible(self) -> None:
        commit = getattr(self.service, "commit", None)
        if callable(commit):
            await commit()

    async def create_item(self, document_id: str, user_id: str, item: dict[str, Any]) -> dict[str, Any]:
        # 执行工具统一返回标准化 effect，前端和 observation 节点只依赖这个结构，不猜测具体结果形状。
        created = item if self.service is None else await self.service.create_item(document_id, user_id, item)
        await self._commit_if_possible()
        item_id = str(created.get("id") or "") if isinstance(created, dict) else str(getattr(created, "id", ""))
        effect = ToolEffect(mutated=True, created_item_ids=[item_id] if item_id else [], summary="已创建节点。")
        return {"item": created, "effect": effect}

    def _normalize_batch_item(self, item: dict[str, Any], *, source_item_id: str = "", index: int = 0) -> dict[str, Any]:
        payload = dict(item or {})
        item_type = str(payload.get("item_type") or payload.get("node_type") or "text").strip() or "text"
        content = payload.get("content")
        if isinstance(content, str):
            content = {"text": content}
        elif not isinstance(content, dict):
            content = {}

        references = list(payload.get("references") or [])
        if source_item_id and not references:
            references = [source_item_id]
        if references:
            content["assistant_references"] = [
                {"item_id": str(reference if not isinstance(reference, dict) else reference.get("item_id") or "").strip()}
                if not isinstance(reference, dict)
                else {
                    "item_id": str(reference.get("item_id") or reference.get("source_item_id") or "").strip(),
                    **{key: value for key, value in reference.items() if key not in {"item_id", "source_item_id"}},
                }
                for reference in references
                if str(reference if not isinstance(reference, dict) else reference.get("item_id") or reference.get("source_item_id") or "").strip()
            ]
        purpose = str(payload.get("purpose") or "").strip()
        if purpose:
            content.setdefault("assistant_purpose", purpose)
        next_step = str(payload.get("next_step") or "").strip()
        if next_step:
            content.setdefault("assistant_next_step", next_step)

        return {
            "client_id": str(payload.get("client_id") or payload.get("key") or f"item-{index + 1}").strip(),
            "title": str(payload.get("title") or "").strip(),
            "item_type": item_type,
            "content": content,
            "width": payload.get("width", 320),
            "height": payload.get("height", 220),
            "z_index": payload.get("z_index", index),
            "connections": list(payload.get("connections") or []),
        }

    def _apply_layout(self, items: list[dict[str, Any]], layout: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not items:
            return []
        layout = dict(layout or {})
        mode = str(layout.get("mode") or "column").strip().lower()
        start_x = float(layout.get("start_x", 80))
        start_y = float(layout.get("start_y", 80))
        gap_x = float(layout.get("gap_x", 48))
        gap_y = float(layout.get("gap_y", 32))
        columns = max(1, int(layout.get("columns", 2 if mode == "grid" else 1)))
        positioned: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            width = float(item.get("width", 320) or 320)
            height = float(item.get("height", 220) or 220)
            if mode == "row":
                position_x = start_x + index * (width + gap_x)
                position_y = start_y
            elif mode == "grid":
                row = index // columns
                col = index % columns
                position_x = start_x + col * (width + gap_x)
                position_y = start_y + row * (height + gap_y)
            else:
                position_x = start_x
                position_y = start_y + index * (height + gap_y)
            positioned.append(
                {
                    **item,
                    "position_x": item.get("position_x", position_x),
                    "position_y": item.get("position_y", position_y),
                }
            )
        return positioned

    async def create_items(
        self,
        document_id: str,
        user_id: str,
        items: list[dict[str, Any]],
        layout: dict[str, Any] | None = None,
        source_item_id: str = "",
    ) -> dict[str, Any]:
        normalized_items = [
            self._normalize_batch_item(item, source_item_id=str(source_item_id or "").strip(), index=index)
            for index, item in enumerate(list(items or []))
        ]
        positioned_items = self._apply_layout(normalized_items, layout)

        created_items: list[Any] = []
        created_connections: list[Any] = []
        references: list[dict[str, Any]] = []
        client_id_to_item_id: dict[str, str] = {}

        for item in positioned_items:
            created = item if self.service is None else await self.service.create_item(
                document_id,
                user_id,
                {
                    "title": item.get("title", ""),
                    "item_type": item.get("item_type", "text"),
                    "content": item.get("content", {}),
                    "position_x": item.get("position_x", 0),
                    "position_y": item.get("position_y", 0),
                    "width": item.get("width", 320),
                    "height": item.get("height", 220),
                    "z_index": item.get("z_index", 0),
                },
            )
            created_items.append(created)
            created_item_id = str(created.get("id") or "") if isinstance(created, dict) else str(getattr(created, "id", ""))
            client_id_to_item_id[str(item.get("client_id") or "").strip()] = created_item_id

            for reference in list((item.get("content") or {}).get("assistant_references") or []):
                references.append(
                    {
                        "item_id": created_item_id,
                        "source_item_id": str(reference.get("item_id") or "").strip(),
                    }
                )

        if self.service is not None:
            for index, item in enumerate(positioned_items):
                source_id = client_id_to_item_id.get(str(item.get("client_id") or "").strip(), "")
                if source_item_id and source_id:
                    connection = await self.service.create_connection(
                        document_id,
                        user_id,
                        {
                            "source_item_id": source_item_id,
                            "target_item_id": source_id,
                            "source_handle": "right",
                            "target_handle": "left",
                        },
                    )
                    created_connections.append(connection)
                for raw_connection in list(item.get("connections") or []):
                    connection_data = raw_connection if isinstance(raw_connection, dict) else {"target_item_id": raw_connection}
                    target_item_id = str(
                        connection_data.get("target_item_id")
                        or client_id_to_item_id.get(str(connection_data.get("target_client_id") or "").strip(), "")
                        or ""
                    ).strip()
                    if not source_id or not target_item_id:
                        continue
                    connection = await self.service.create_connection(
                        document_id,
                        user_id,
                        {
                            "source_item_id": source_id,
                            "target_item_id": target_item_id,
                            "source_handle": str(connection_data.get("source_handle") or "right"),
                            "target_handle": str(connection_data.get("target_handle") or "left"),
                        },
                    )
                    created_connections.append(connection)

        await self._commit_if_possible()
        created_item_ids = [
            str(item.get("id") or "") if isinstance(item, dict) else str(getattr(item, "id", ""))
            for item in created_items
        ]
        created_connection_ids = [
            str(connection.get("id") or "") if isinstance(connection, dict) else str(getattr(connection, "id", ""))
            for connection in created_connections
        ]
        effect = ToolEffect(
            mutated=bool(created_item_ids or created_connection_ids),
            created_item_ids=[item_id for item_id in created_item_ids if item_id],
            created_connection_ids=[connection_id for connection_id in created_connection_ids if connection_id],
            summary="已批量创建节点。",
        )
        return {
            "items": created_items,
            "references": references,
            "connections": created_connections,
            "effect": effect,
        }

    async def update_item(self, document_id: str, user_id: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        updated = {"id": item_id, **patch} if self.service is None else await self.service.update_item(document_id, item_id, user_id, patch)
        await self._commit_if_possible()
        normalized_id = str(updated.get("id") or "") if isinstance(updated, dict) else str(getattr(updated, "id", item_id))
        effect = ToolEffect(mutated=True, updated_item_ids=[normalized_id] if normalized_id else [], summary="已更新节点。")
        return {"item": updated, "effect": effect}

    async def update_items(self, document_id: str, user_id: str, updates: list[dict[str, Any]]) -> dict[str, Any]:
        updated_items: list[Any] = []
        updated_item_ids: list[str] = []
        for update in list(updates or []):
            item_id = str(update.get("item_id") or "").strip()
            patch = dict(update.get("patch") or {})
            if not item_id or not patch:
                continue
            updated = {"id": item_id, **patch} if self.service is None else await self.service.update_item(document_id, item_id, user_id, patch)
            updated_items.append(updated)
            normalized_id = str(updated.get("id") or "") if isinstance(updated, dict) else str(getattr(updated, "id", item_id))
            if normalized_id:
                updated_item_ids.append(normalized_id)
        await self._commit_if_possible()
        effect = ToolEffect(mutated=bool(updated_item_ids), updated_item_ids=updated_item_ids, summary="已批量更新节点。")
        return {"items": updated_items, "effect": effect}

    async def delete_items(self, document_id: str, user_id: str, item_ids: list[str]) -> dict[str, Any]:
        if self.service is not None:
            for item_id in item_ids:
                await self.service.delete_item(document_id, item_id, user_id)
            await self._commit_if_possible()
        effect = ToolEffect(mutated=True, deleted_item_ids=item_ids, summary="已删除节点。")
        return {"deleted_item_ids": item_ids, "effect": effect}

    async def create_connection(self, document_id: str, user_id: str, connection: dict[str, Any]) -> dict[str, Any]:
        created = connection if self.service is None else await self.service.create_connection(document_id, user_id, connection)
        await self._commit_if_possible()
        connection_id = str(created.get("id") or "") if isinstance(created, dict) else str(getattr(created, "id", ""))
        effect = ToolEffect(mutated=True, created_connection_ids=[connection_id] if connection_id else [], summary="已创建连线。")
        return {"connection": created, "effect": effect}

    async def delete_connections(self, document_id: str, user_id: str, connection_ids: list[str]) -> dict[str, Any]:
        if self.service is not None:
            for connection_id in connection_ids:
                await self.service.delete_connection(document_id, connection_id, user_id)
            await self._commit_if_possible()
        effect = ToolEffect(mutated=True, deleted_connection_ids=connection_ids, summary="已删除连线。")
        return {"deleted_connection_ids": connection_ids, "effect": effect}
