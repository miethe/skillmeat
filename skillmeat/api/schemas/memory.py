"""Pydantic schemas for memory item API endpoints.

Defines request/response models for memory item CRUD, lifecycle management,
and merge operations. These schemas map between the HTTP layer and the
MemoryService business logic layer.

Schema Groups:
    - Enums: MemoryType, MemoryStatus (constrain allowed values)
    - CRUD: Create, Update, Response, ListResponse
    - Lifecycle: Promote, Deprecate, Bulk actions
    - Merge: MergeRequest, MergeResponse
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# Enums
# =============================================================================


class MemoryType(str, Enum):
    """Allowed memory item types matching DB CHECK constraint."""

    DECISION = "decision"
    CONSTRAINT = "constraint"
    GOTCHA = "gotcha"
    STYLE_RULE = "style_rule"
    LEARNING = "learning"


class MemoryStatus(str, Enum):
    """Allowed memory item lifecycle statuses matching DB CHECK constraint."""

    CANDIDATE = "candidate"
    ACTIVE = "active"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class MemoryShareScope(str, Enum):
    """Allowed cross-project share scope values."""

    PRIVATE = "private"
    PROJECT = "project"
    GLOBAL_CANDIDATE = "global_candidate"


# =============================================================================
# CRUD Schemas
# =============================================================================


class AnchorCreate(BaseModel):
    """Structured anchor payload for create/update requests."""

    path: str = Field(min_length=1)
    type: Literal["code", "plan", "doc", "config", "test"]
    line_start: Optional[int] = Field(default=None, ge=1)
    line_end: Optional[int] = Field(default=None, ge=1)
    commit_sha: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_line_range(self) -> "AnchorCreate":
        if self.line_end is not None and self.line_start is None:
            raise ValueError("line_start is required when line_end is provided")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class AnchorResponse(BaseModel):
    """Structured anchor in memory item responses."""

    path: str
    type: Literal["code", "plan", "doc", "config", "test"]
    line_start: Optional[int] = Field(default=None, ge=1)
    line_end: Optional[int] = Field(default=None, ge=1)
    commit_sha: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_line_range(self) -> "AnchorResponse":
        if self.line_end is not None and self.line_start is None:
            raise ValueError("line_start is required when line_end is provided")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class MemoryItemCreateRequest(BaseModel):
    """Request body for creating a new memory item."""

    type: MemoryType
    content: str = Field(min_length=1, max_length=10000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: MemoryStatus = MemoryStatus.CANDIDATE
    share_scope: MemoryShareScope = MemoryShareScope.PROJECT
    provenance: Optional[Dict[str, Any]] = None
    anchors: Optional[List[Union[AnchorCreate, str]]] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None
    source_type: Optional[str] = None
    ttl_policy: Optional[Dict[str, Any]] = None


class MemoryItemUpdateRequest(BaseModel):
    """Request body for updating a memory item. All fields optional."""

    type: Optional[MemoryType] = None
    content: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[MemoryStatus] = None
    share_scope: Optional[MemoryShareScope] = None
    provenance: Optional[Dict[str, Any]] = None
    anchors: Optional[List[Union[AnchorCreate, str]]] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None
    source_type: Optional[str] = None
    ttl_policy: Optional[Dict[str, Any]] = None


class MemoryItemResponse(BaseModel):
    """Response model for a single memory item."""

    id: str
    project_id: str
    type: str
    content: str
    confidence: float
    status: str
    share_scope: str
    project_name: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    anchors: Optional[List[Union[AnchorResponse, str]]] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None
    source_type: Optional[str] = None
    ttl_policy: Optional[Dict[str, Any]] = None
    content_hash: Optional[str] = None
    access_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deprecated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MemoryItemListResponse(BaseModel):
    """Response model for paginated memory item listing."""

    items: List[MemoryItemResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: Optional[int] = None


class MemorySearchResponse(BaseModel):
    """Response model for memory search operations."""

    items: List[MemoryItemResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: Optional[int] = None


class ExtractionCandidate(BaseModel):
    """A preview extraction candidate."""

    type: MemoryType
    content: str
    confidence: float
    status: MemoryStatus = MemoryStatus.CANDIDATE
    duplicate_of: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    anchors: Optional[List[AnchorResponse]] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None
    source_type: Optional[str] = None


class MemoryExtractionPreviewRequest(BaseModel):
    """Request for extraction preview."""

    text_corpus: str = Field(min_length=1, max_length=500000)
    profile: str = Field(default="balanced", pattern="^(strict|balanced|aggressive)$")
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    commit_sha: Optional[str] = None
    use_llm: bool = Field(
        default=False, description="Enable LLM-based semantic classification"
    )
    llm_provider: Optional[str] = Field(
        default=None, pattern="^(anthropic|openai|ollama|openai-compatible)$"
    )
    llm_model: Optional[str] = Field(default=None)
    llm_base_url: Optional[str] = Field(default=None)


class MemoryExtractionPreviewResponse(BaseModel):
    """Preview response for extraction."""

    candidates: List[ExtractionCandidate]
    total_candidates: int


class MemoryExtractionApplyRequest(MemoryExtractionPreviewRequest):
    """Request for applying extraction output."""


class MemoryExtractionApplyResponse(BaseModel):
    """Apply response for extraction."""

    created: List[MemoryItemResponse]
    skipped_duplicates: List[ExtractionCandidate]
    preview_total: int


# =============================================================================
# Lifecycle Schemas
# =============================================================================


class PromoteRequest(BaseModel):
    """Request body for promoting a memory item to the next lifecycle stage."""

    reason: Optional[str] = None


class DeprecateRequest(BaseModel):
    """Request body for deprecating a memory item."""

    reason: Optional[str] = None


class BulkPromoteRequest(BaseModel):
    """Request body for promoting multiple memory items at once."""

    item_ids: List[str]
    reason: Optional[str] = None


class BulkDeprecateRequest(BaseModel):
    """Request body for deprecating multiple memory items at once."""

    item_ids: List[str]
    reason: Optional[str] = None


class BulkActionResponse(BaseModel):
    """Response model for bulk lifecycle operations."""

    succeeded: List[str]
    failed: List[Dict[str, str]]  # [{"id": ..., "error": ...}]


# =============================================================================
# Merge Schemas
# =============================================================================


class MergeRequest(BaseModel):
    """Request body for merging two memory items."""

    source_id: str
    target_id: str
    strategy: str = Field(
        default="keep_target",
        pattern="^(keep_target|keep_source|combine)$",
    )
    merged_content: Optional[str] = None


class MergeResponse(BaseModel):
    """Response model for a completed merge operation."""

    item: MemoryItemResponse
    merged_source_id: str
