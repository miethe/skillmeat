"""Memory items API router for CRUD, lifecycle, and merge operations.

This router provides endpoints for managing memory items -- persistent knowledge
artifacts that Claude agents accumulate during development sessions. Memory items
capture decisions, constraints, gotchas, style rules, and learnings that inform
future agent behavior.

Endpoint Groups:
    CRUD (API-2.6):
        GET    /memory-items          -- List with filters and cursor pagination
        POST   /memory-items          -- Create (with duplicate detection)
        GET    /memory-items/count    -- Count with filters
        GET    /memory-items/{id}     -- Get by ID
        PUT    /memory-items/{id}     -- Update
        DELETE /memory-items/{id}     -- Delete

    Lifecycle (API-2.7):
        POST /memory-items/{id}/promote       -- Promote to next stage
        POST /memory-items/{id}/deprecate     -- Deprecate
        POST /memory-items/bulk-promote       -- Bulk promote
        POST /memory-items/bulk-deprecate     -- Bulk deprecate

    Merge (API-2.8):
        POST /memory-items/merge              -- Merge two items
"""

import json
import logging
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query

from skillmeat.api.dependencies import require_memory_context_enabled
from skillmeat.api.schemas.memory import (
    BulkActionResponse,
    BulkDeprecateRequest,
    BulkPromoteRequest,
    DeprecateRequest,
    MemoryItemCreateRequest,
    MemoryItemListResponse,
    MemoryItemResponse,
    MemoryItemUpdateRequest,
    MemoryStatus,
    MemoryType,
    MergeRequest,
    MergeResponse,
    PromoteRequest,
)
from skillmeat.core.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/memory-items",
    tags=["memory-items"],
    dependencies=[Depends(require_memory_context_enabled)],
)


def _get_service() -> MemoryService:
    """Create a MemoryService instance using the default database path.

    Returns:
        MemoryService configured with the default SQLite database.
    """
    return MemoryService(db_path=None)


def _dict_to_response(data: dict) -> MemoryItemResponse:
    """Convert a service-layer dict to a MemoryItemResponse schema.

    Handles datetime serialization by converting datetime objects to
    ISO format strings.

    Args:
        data: Dict returned by MemoryService methods.

    Returns:
        MemoryItemResponse instance.
    """
    # Convert datetime objects to ISO strings if present
    for field in ("created_at", "updated_at", "deprecated_at"):
        val = data.get(field)
        if val is not None and hasattr(val, "isoformat"):
            data[field] = val.isoformat()

    return MemoryItemResponse(**data)


# =============================================================================
# Static routes MUST be defined before /{item_id} to avoid path conflicts
# =============================================================================


@router.get(
    "/count",
    summary="Count memory items",
    description="Get a count of memory items for a project with optional filters.",
    responses={
        200: {"description": "Count retrieved successfully"},
        400: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"},
    },
)
async def count_memory_items(
    project_id: str = Query(..., description="Project ID to scope the count"),
    status: Optional[MemoryStatus] = Query(None, description="Filter by status"),
    type: Optional[MemoryType] = Query(None, description="Filter by memory type"),
) -> dict:
    """Count memory items for a project with optional filters.

    Args:
        project_id: Required project scope.
        status: Optional status filter.
        type: Optional type filter.

    Returns:
        Dict with a single 'count' key.
    """
    try:
        project_id = unquote(project_id)
        service = _get_service()
        count = service.count(
            project_id=project_id,
            status=status.value if status else None,
            type=type.value if type else None,
        )
        return {"count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to count memory items: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.post(
    "/bulk-promote",
    response_model=BulkActionResponse,
    summary="Bulk promote memory items",
    description="Promote multiple memory items to their next lifecycle stage.",
    responses={
        200: {"description": "Bulk promote completed (may contain partial failures)"},
        500: {"description": "Internal server error"},
    },
)
async def bulk_promote_memory_items(
    request: BulkPromoteRequest,
) -> BulkActionResponse:
    """Promote multiple memory items in a single request.

    Each item is promoted independently. Individual failures do not
    prevent other items from being promoted.

    Args:
        request: List of item IDs and optional reason.

    Returns:
        BulkActionResponse with succeeded and failed lists.
    """
    try:
        service = _get_service()
        result = service.bulk_promote(
            item_ids=request.item_ids,
            reason=request.reason,
        )
        return BulkActionResponse(
            succeeded=[item["id"] for item in result["promoted"]],
            failed=result["failed"],
        )
    except Exception as e:
        logger.exception(f"Failed to bulk promote memory items: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.post(
    "/bulk-deprecate",
    response_model=BulkActionResponse,
    summary="Bulk deprecate memory items",
    description="Deprecate multiple memory items in a single request.",
    responses={
        200: {"description": "Bulk deprecate completed (may contain partial failures)"},
        500: {"description": "Internal server error"},
    },
)
async def bulk_deprecate_memory_items(
    request: BulkDeprecateRequest,
) -> BulkActionResponse:
    """Deprecate multiple memory items in a single request.

    Each item is deprecated independently. Individual failures do not
    prevent other items from being deprecated.

    Args:
        request: List of item IDs and optional reason.

    Returns:
        BulkActionResponse with succeeded and failed lists.
    """
    try:
        service = _get_service()
        result = service.bulk_deprecate(
            item_ids=request.item_ids,
            reason=request.reason,
        )
        return BulkActionResponse(
            succeeded=[item["id"] for item in result["deprecated"]],
            failed=result["failed"],
        )
    except Exception as e:
        logger.exception(f"Failed to bulk deprecate memory items: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.post(
    "/merge",
    response_model=MergeResponse,
    summary="Merge two memory items",
    description="""
    Merge a source memory item into a target item using a specified strategy.

    Strategies:
    - keep_target: Keep the target's content, deprecate the source.
    - keep_source: Replace the target's content with the source's, deprecate the source.
    - combine: Use the provided merged_content for the target, deprecate the source.

    The source item is always deprecated after a successful merge.
    """,
    responses={
        200: {"description": "Merge completed successfully"},
        400: {"description": "Invalid merge request"},
        404: {"description": "Source or target item not found"},
        500: {"description": "Internal server error"},
    },
)
async def merge_memory_items(
    request: MergeRequest,
) -> MergeResponse:
    """Merge two memory items using the specified strategy.

    Args:
        request: Merge parameters including source_id, target_id, strategy.

    Returns:
        MergeResponse with the updated target item and merged source ID.
    """
    try:
        service = _get_service()
        result = service.merge(
            source_id=request.source_id,
            target_id=request.target_id,
            strategy=request.strategy,
            merged_content=request.merged_content,
        )
        merged_source_id = result.pop("merged_source_id")
        item_response = _dict_to_response(result)
        return MergeResponse(item=item_response, merged_source_id=merged_source_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=400,
            detail=error_msg,
        )
    except Exception as e:
        logger.exception(f"Failed to merge memory items: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


# =============================================================================
# CRUD Operations (API-2.6)
# =============================================================================


@router.get(
    "",
    response_model=MemoryItemListResponse,
    summary="List memory items",
    description="""
    Retrieve a paginated list of memory items for a project.

    Supports filtering by status, type, and minimum confidence score.
    Uses cursor-based pagination for efficient traversal of large result sets.
    """,
    responses={
        200: {"description": "Successfully retrieved memory items"},
        400: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_memory_items(
    project_id: str = Query(..., description="Project ID to scope the query"),
    status: Optional[MemoryStatus] = Query(None, description="Filter by status"),
    type: Optional[MemoryType] = Query(None, description="Filter by memory type"),
    search: Optional[str] = Query(
        None, description="Case-insensitive substring match against memory content"
    ),
    min_confidence: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Minimum confidence threshold"
    ),
    limit: int = Query(
        default=50, ge=1, le=100, description="Number of items per page (max 100)"
    ),
    cursor: Optional[str] = Query(
        None, description="Cursor from previous page for pagination"
    ),
    sort_by: str = Query(
        default="created_at", description="Field to sort by"
    ),
    sort_order: str = Query(
        default="desc", description="Sort direction (asc or desc)"
    ),
) -> MemoryItemListResponse:
    """List memory items with filtering and cursor-based pagination.

    Args:
        project_id: Required project scope filter.
        status: Optional status filter.
        type: Optional type filter.
        min_confidence: Optional minimum confidence threshold.
        limit: Page size (1-100, default 50).
        cursor: Cursor from a previous response for next page.
        sort_by: Sort field (default created_at).
        sort_order: Sort direction (default desc).

    Returns:
        Paginated list of memory items.
    """
    try:
        project_id = unquote(project_id)
        service = _get_service()
        result = service.list_items(
            project_id=project_id,
            status=status.value if status else None,
            type=type.value if type else None,
            search=search,
            min_confidence=min_confidence,
            limit=limit,
            cursor=cursor,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = [_dict_to_response(item) for item in result["items"]]
        return MemoryItemListResponse(
            items=items,
            next_cursor=result["next_cursor"],
            has_more=result["has_more"],
            total=result.get("total"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to list memory items: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.post(
    "",
    response_model=MemoryItemResponse,
    status_code=201,
    summary="Create a new memory item",
    description="""
    Create a new memory item for a project.

    Includes automatic duplicate detection via content hashing.
    If a duplicate is detected, returns 409 Conflict with the existing item.
    """,
    responses={
        201: {"description": "Memory item created successfully"},
        400: {"description": "Validation error"},
        409: {"description": "Duplicate memory item detected"},
        500: {"description": "Internal server error"},
    },
)
async def create_memory_item(
    request: MemoryItemCreateRequest,
    project_id: str = Query(..., description="Project ID for the new memory item"),
) -> MemoryItemResponse:
    """Create a new memory item with duplicate detection.

    Args:
        request: Memory item creation data.
        project_id: Required project scope.

    Returns:
        The created memory item.

    Raises:
        HTTPException 409: If a duplicate content hash is detected.
    """
    try:
        project_id = unquote(project_id)
        service = _get_service()
        result = service.create(
            project_id=project_id,
            type=request.type.value,
            content=request.content,
            confidence=request.confidence,
            status=request.status.value,
            provenance=request.provenance,
            anchors=request.anchors,
            ttl_policy=request.ttl_policy,
        )

        # Handle duplicate detection
        if isinstance(result, dict) and result.get("duplicate"):
            existing_item = _dict_to_response(result["item"])
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Duplicate memory item detected",
                    "existing_item": existing_item.model_dump(),
                },
            )

        return _dict_to_response(result)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to create memory item: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get(
    "/{item_id}",
    response_model=MemoryItemResponse,
    summary="Get a memory item by ID",
    description="Retrieve a single memory item by its ID. Increments access count.",
    responses={
        200: {"description": "Successfully retrieved memory item"},
        404: {"description": "Memory item not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_memory_item(item_id: str) -> MemoryItemResponse:
    """Get a single memory item by ID.

    Access count is automatically incremented on each read.

    Args:
        item_id: Memory item identifier.

    Returns:
        The requested memory item.
    """
    try:
        service = _get_service()
        result = service.get(item_id)
        return _dict_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to get memory item {item_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.put(
    "/{item_id}",
    response_model=MemoryItemResponse,
    summary="Update a memory item",
    description="""
    Update an existing memory item. Only provided fields are changed.

    Updatable fields: type, content, confidence, status, provenance, anchors, ttl_policy.
    """,
    responses={
        200: {"description": "Memory item updated successfully"},
        400: {"description": "Validation error or disallowed field"},
        404: {"description": "Memory item not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_memory_item(
    item_id: str,
    request: MemoryItemUpdateRequest,
) -> MemoryItemResponse:
    """Update a memory item's fields.

    Only the fields provided in the request body are updated.
    JSON fields (provenance, anchors, ttl_policy) are serialized
    before passing to the service layer.

    Args:
        item_id: Memory item identifier.
        request: Update request with optional fields.

    Returns:
        The updated memory item.
    """
    try:
        service = _get_service()

        # Build update kwargs, mapping schema fields to service-layer field names
        update_fields = {}
        if request.type is not None:
            update_fields["type"] = request.type.value
        if request.content is not None:
            update_fields["content"] = request.content
        if request.confidence is not None:
            update_fields["confidence"] = request.confidence
        if request.status is not None:
            update_fields["status"] = request.status.value
        if request.provenance is not None:
            update_fields["provenance_json"] = json.dumps(request.provenance)
        if request.anchors is not None:
            update_fields["anchors_json"] = json.dumps(request.anchors)
        if request.ttl_policy is not None:
            update_fields["ttl_policy_json"] = json.dumps(request.ttl_policy)

        if not update_fields:
            raise ValueError("No updatable fields provided")

        result = service.update(item_id, **update_fields)
        return _dict_to_response(result)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.exception(f"Failed to update memory item {item_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.delete(
    "/{item_id}",
    status_code=204,
    summary="Delete a memory item",
    description="Permanently delete a memory item by ID.",
    responses={
        204: {"description": "Memory item deleted successfully"},
        404: {"description": "Memory item not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_memory_item(item_id: str) -> None:
    """Delete a memory item.

    Args:
        item_id: Memory item identifier.

    Raises:
        HTTPException 404: If the item does not exist.
    """
    try:
        service = _get_service()
        deleted = service.delete(item_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Memory item not found: {item_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete memory item {item_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


# =============================================================================
# Lifecycle Operations (API-2.7)
# =============================================================================


@router.post(
    "/{item_id}/promote",
    response_model=MemoryItemResponse,
    summary="Promote a memory item",
    description="""
    Promote a memory item to the next lifecycle stage.

    State machine: candidate -> active -> stable.
    Items that are already stable or deprecated cannot be promoted.
    """,
    responses={
        200: {"description": "Memory item promoted successfully"},
        400: {"description": "Invalid promotion (wrong status)"},
        404: {"description": "Memory item not found"},
        500: {"description": "Internal server error"},
    },
)
async def promote_memory_item(
    item_id: str,
    request: PromoteRequest,
) -> MemoryItemResponse:
    """Promote a memory item to the next lifecycle stage.

    Args:
        item_id: Memory item identifier.
        request: Optional promotion reason.

    Returns:
        The promoted memory item.
    """
    try:
        service = _get_service()
        result = service.promote(item_id, reason=request.reason)
        return _dict_to_response(result)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.exception(f"Failed to promote memory item {item_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.post(
    "/{item_id}/deprecate",
    response_model=MemoryItemResponse,
    summary="Deprecate a memory item",
    description="""
    Deprecate a memory item regardless of its current lifecycle stage.

    Any non-deprecated status can transition to deprecated. The deprecated_at
    timestamp is set automatically by the repository layer.
    """,
    responses={
        200: {"description": "Memory item deprecated successfully"},
        400: {"description": "Item is already deprecated"},
        404: {"description": "Memory item not found"},
        500: {"description": "Internal server error"},
    },
)
async def deprecate_memory_item(
    item_id: str,
    request: DeprecateRequest,
) -> MemoryItemResponse:
    """Deprecate a memory item.

    Args:
        item_id: Memory item identifier.
        request: Optional deprecation reason.

    Returns:
        The deprecated memory item.
    """
    try:
        service = _get_service()
        result = service.deprecate(item_id, reason=request.reason)
        return _dict_to_response(result)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.exception(f"Failed to deprecate memory item {item_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
