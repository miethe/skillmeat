"""Pydantic schemas for context module and context packing endpoints.

This module defines request/response models for:
- Context module CRUD operations (create, read, update, delete)
- Memory item association management within modules
- Context pack preview and generation

Context modules are named groupings of memory items with selector criteria
that define how memories are assembled into contextual knowledge. Context
packs are token-budget-aware compilations of memory items into structured
markdown suitable for agent prompt injection.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Context Module Schemas
# =============================================================================


class ContextModuleCreateRequest(BaseModel):
    """Request body for creating a new context module.

    Attributes:
        name: Human-readable module name (1-255 characters).
        description: Optional description of the module's purpose.
        selectors: Optional selector criteria dict. Allowed keys:
            memory_types (list), min_confidence (float),
            file_patterns (list), workflow_stages (list).
        priority: Module priority for ordering (0-100, default 5).
    """

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    selectors: Optional[Dict[str, Any]] = None
    priority: int = Field(default=5, ge=0, le=100)


class ContextModuleUpdateRequest(BaseModel):
    """Request body for updating an existing context module.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Updated module name (1-255 characters).
        description: Updated description.
        selectors: Updated selector criteria dict.
        priority: Updated priority (0-100).
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    selectors: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(default=None, ge=0, le=100)


class ContextModuleResponse(BaseModel):
    """Response body for a single context module.

    Attributes:
        id: Unique module identifier.
        project_id: Project this module belongs to.
        name: Human-readable module name.
        description: Module purpose description.
        selectors: Selector criteria dict (parsed from JSON).
        priority: Module priority for ordering.
        content_hash: SHA-256 hash for change detection.
        created_at: ISO 8601 creation timestamp.
        updated_at: ISO 8601 last-update timestamp.
        memory_items: Associated memory items (only when include_items=true).
    """

    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    selectors: Optional[Dict[str, Any]] = None
    priority: int = 5
    content_hash: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    memory_items: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)


class ContextModuleListResponse(BaseModel):
    """Paginated list response for context modules.

    Attributes:
        items: List of context module responses.
        next_cursor: Cursor for fetching the next page (None if no more).
        has_more: Whether more pages are available.
        total: Total count (None if not computed for performance).
    """

    items: List[ContextModuleResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: Optional[int] = None


class AddMemoryToModuleRequest(BaseModel):
    """Request body for adding a memory item to a context module.

    Attributes:
        memory_id: ID of the memory item to associate.
        ordering: Display/priority order within the module (default 0).
    """

    memory_id: str
    ordering: int = 0


# =============================================================================
# Context Packing Schemas
# =============================================================================


class ContextPackPreviewRequest(BaseModel):
    """Request body for previewing a context pack (read-only).

    Attributes:
        module_id: Optional module whose selectors define filter criteria.
        budget_tokens: Maximum token budget for the pack (100-100000).
        filters: Optional additional filters dict. Supported keys:
            type (str), min_confidence (float).
    """

    module_id: Optional[str] = None
    budget_tokens: int = Field(default=4000, ge=100, le=100000)
    filters: Optional[Dict[str, Any]] = None


class ContextPackPreviewResponse(BaseModel):
    """Response body for a context pack preview.

    Attributes:
        items: List of selected item dicts with id, type, content,
            confidence, and tokens fields.
        total_tokens: Sum of estimated tokens for all selected items.
        budget_tokens: The token budget that was requested.
        utilization: Fraction of budget used (0.0-1.0).
        items_included: Number of items that fit within budget.
        items_available: Total number of candidate items before budget cut.
    """

    items: List[Dict[str, Any]]
    total_tokens: int
    budget_tokens: int
    utilization: float
    items_included: int
    items_available: int


class ContextPackGenerateRequest(BaseModel):
    """Request body for generating a full context pack with markdown.

    Attributes:
        module_id: Optional module whose selectors define filter criteria.
        budget_tokens: Maximum token budget for the pack (100-100000).
        filters: Optional additional filters dict. Supported keys:
            type (str), min_confidence (float).
    """

    module_id: Optional[str] = None
    budget_tokens: int = Field(default=4000, ge=100, le=100000)
    filters: Optional[Dict[str, Any]] = None


class ContextPackGenerateResponse(BaseModel):
    """Response body for a generated context pack.

    Extends the preview response with markdown output and a generation
    timestamp.

    Attributes:
        items: List of selected item dicts.
        total_tokens: Sum of estimated tokens for all selected items.
        budget_tokens: The token budget that was requested.
        utilization: Fraction of budget used (0.0-1.0).
        items_included: Number of items that fit within budget.
        items_available: Total number of candidate items before budget cut.
        markdown: Formatted markdown context pack grouped by memory type.
        generated_at: ISO 8601 timestamp of generation.
    """

    items: List[Dict[str, Any]]
    total_tokens: int
    budget_tokens: int
    utilization: float
    items_included: int
    items_available: int
    markdown: str
    generated_at: str
