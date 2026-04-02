from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import PaginatedResponse, SuccessResponse, UUIDMixin


class CanvasDocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class CanvasDocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class CanvasDocumentResponse(UUIDMixin):
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict):
        for field in ("created_at", "updated_at"):
            if field in data and hasattr(data[field], "isoformat"):
                data[field] = data[field].isoformat()
        return cls(**data)


class CanvasDocumentListResponse(PaginatedResponse):
    documents: List[CanvasDocumentResponse]


class CanvasItemPayload(BaseModel):
    id: UUID
    item_type: str
    title: str = ""
    position_x: float = 0
    position_y: float = 0
    width: float = 320
    height: float = 220
    z_index: int = 0
    content: Dict[str, Any] = Field(default_factory=dict)
    generation_config: Dict[str, Any] = Field(default_factory=dict)
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
    last_output: Dict[str, Any] = Field(default_factory=dict)


class CanvasConnectionPayload(BaseModel):
    id: UUID
    source_item_id: UUID
    target_item_id: UUID
    source_handle: str
    target_handle: str


class CanvasItemCreate(BaseModel):
    item_type: str
    title: str = ""
    position_x: float = 0
    position_y: float = 0
    width: float = 320
    height: float = 220
    z_index: int = 0
    content: Dict[str, Any] = Field(default_factory=dict)
    generation_config: Dict[str, Any] = Field(default_factory=dict)


class CanvasItemUpdate(BaseModel):
    title: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    z_index: Optional[int] = None
    content: Optional[Dict[str, Any]] = None
    generation_config: Optional[Dict[str, Any]] = None
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
    last_output: Optional[Dict[str, Any]] = None


class CanvasConnectionCreate(BaseModel):
    source_item_id: UUID
    target_item_id: UUID
    source_handle: str
    target_handle: str


class CanvasPreviewItemsRequest(BaseModel):
    item_ids: List[UUID] = Field(default_factory=list)


class CanvasStageDocumentResponse(BaseModel):
    id: UUID
    title: str


class CanvasStageSnapshotResponse(BaseModel):
    document: CanvasStageDocumentResponse
    items: List[CanvasItemPayload] = Field(default_factory=list)
    connections: List[CanvasConnectionPayload] = Field(default_factory=list)


class CanvasPreviewItemsResponse(BaseModel):
    items: List[CanvasItemPayload] = Field(default_factory=list)


class CanvasGraphUpdate(BaseModel):
    items: List[CanvasItemPayload] = Field(default_factory=list)
    connections: List[CanvasConnectionPayload] = Field(default_factory=list)


class CanvasGraphResponse(BaseModel):
    document: CanvasDocumentResponse
    items: List[CanvasItemPayload] = Field(default_factory=list)
    connections: List[CanvasConnectionPayload] = Field(default_factory=list)


class CanvasGenerationResponse(UUIDMixin):
    id: UUID
    item_id: UUID
    document_id: UUID
    user_id: UUID
    generation_type: str
    status: str
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    result_payload: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict):
        for field in ("created_at", "updated_at"):
            if field in data and hasattr(data[field], "isoformat"):
                data[field] = data[field].isoformat()
        return cls(**data)


class CanvasGenerationListResponse(PaginatedResponse):
    generations: List[CanvasGenerationResponse]


class CanvasGenerateRequest(BaseModel):
    api_key_id: Optional[UUID] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    prompt_plain_text: Optional[str] = None
    prompt_tokens: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_mentions: List[Dict[str, Any]] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)


class CanvasGenerateResultResponse(SuccessResponse):
    generation_id: UUID
    status: str
    item: CanvasItemPayload
    generation: CanvasGenerationResponse


class CanvasApplyGenerationResponse(SuccessResponse):
    item: CanvasItemPayload
    generation: CanvasGenerationResponse


class CanvasVideoTaskResponse(BaseModel):
    task_id: str
    provider_task_id: Optional[str] = None
    status: str
    result_video_url: Optional[str] = None
    error_message: Optional[str] = None
    provider_payload: Dict[str, Any] = Field(default_factory=dict)
    item: CanvasItemPayload


class CanvasVideoUploadResponse(SuccessResponse):
    status: str
    item: CanvasItemPayload
    storage_info: Dict[str, Any] = Field(default_factory=dict)
