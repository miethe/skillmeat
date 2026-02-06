"""Context modules API router for the Memory & Context Intelligence System.

This router provides endpoints for managing context modules — named groupings
of memory items with selector criteria that define how memories are assembled
into contextual knowledge for different workflows.

Context modules support:
- CRUD operations scoped by project
- Selector validation (memory_types, min_confidence, file_patterns, workflow_stages)
- Memory item association management (add/remove memories from modules)
- Cursor-based paginated listings

API Endpoints:
    GET    /context-modules                          - List modules for project
    POST   /context-modules                          - Create new module
    GET    /context-modules/{module_id}               - Get module by ID
    PUT    /context-modules/{module_id}               - Update module
    DELETE /context-modules/{module_id}               - Delete module
    POST   /context-modules/{module_id}/memories      - Add memory to module
    DELETE /context-modules/{module_id}/memories/{memory_id} - Remove memory
    GET    /context-modules/{module_id}/memories      - List module's memories
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import require_memory_context_enabled
from skillmeat.api.schemas.context_module import (
    AddMemoryToModuleRequest,
    ContextModuleCreateRequest,
    ContextModuleListResponse,
    ContextModuleResponse,
    ContextModuleUpdateRequest,
)
from skillmeat.core.services.context_module_service import ContextModuleService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/context-modules",
    tags=["context-modules"],
    dependencies=[Depends(require_memory_context_enabled)],
)


def _get_service() -> ContextModuleService:
    """Get a ContextModuleService instance with default database path.

    Returns:
        Initialized ContextModuleService.
    """
    return ContextModuleService(db_path=None)


# =============================================================================
# Context Module CRUD Operations
# =============================================================================


@router.get(
    "",
    response_model=ContextModuleListResponse,
    summary="List context modules for a project",
    description="""
    Retrieve a paginated list of context modules scoped to a project.

    Results are ordered by module ID and support cursor-based pagination.
    """,
    responses={
        200: {"description": "Successfully retrieved context modules"},
        400: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_context_modules(
    project_id: str = Query(..., description="Project ID to list modules for"),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Cursor from previous page for pagination",
    ),
) -> ContextModuleListResponse:
    """List context modules for a project with cursor-based pagination.

    Args:
        project_id: Project scope to list modules for.
        limit: Maximum number of modules per page.
        cursor: Cursor from previous page.

    Returns:
        Paginated list of context modules.
    """
    try:
        service = _get_service()
        result = service.list_by_project(project_id, limit=limit, cursor=cursor)

        items = [ContextModuleResponse(**m) for m in result["items"]]

        return ContextModuleListResponse(
            items=items,
            next_cursor=result.get("next_cursor"),
            has_more=result.get("has_more", False),
            total=result.get("total"),
        )
    except ValueError as e:
        logger.warning(f"Validation error listing context modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error listing context modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "",
    response_model=ContextModuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new context module",
    description="""
    Create a new context module for a project with optional selector criteria.

    Selectors define how memory items are filtered when the module is used
    for context packing. Allowed selector keys: memory_types, min_confidence,
    file_patterns, workflow_stages.
    """,
    responses={
        201: {"description": "Context module created successfully"},
        400: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def create_context_module(
    request: ContextModuleCreateRequest,
    project_id: str = Query(..., description="Project ID to create module in"),
) -> ContextModuleResponse:
    """Create a new context module.

    Args:
        request: Module creation request body.
        project_id: Project scope for the module.

    Returns:
        Created context module.
    """
    try:
        service = _get_service()
        module = service.create(
            project_id=project_id,
            name=request.name,
            description=request.description,
            selectors=request.selectors,
            priority=request.priority,
        )

        return ContextModuleResponse(**module)
    except ValueError as e:
        logger.warning(f"Validation error creating context module: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to create context module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{module_id}",
    response_model=ContextModuleResponse,
    summary="Get a context module by ID",
    description="""
    Retrieve detailed information about a specific context module.

    Use include_items=true to also retrieve associated memory items.
    """,
    responses={
        200: {"description": "Successfully retrieved context module"},
        404: {"description": "Context module not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_context_module(
    module_id: str,
    include_items: bool = Query(
        default=False,
        description="Include associated memory items in response",
    ),
) -> ContextModuleResponse:
    """Get a single context module by ID.

    Args:
        module_id: Context module identifier.
        include_items: Whether to include associated memory items.

    Returns:
        Context module details.
    """
    try:
        service = _get_service()
        module = service.get(module_id, include_items=include_items)
        return ContextModuleResponse(**module)
    except ValueError as e:
        logger.warning(f"Context module not found: {module_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error getting context module '{module_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/{module_id}",
    response_model=ContextModuleResponse,
    summary="Update a context module",
    description="""
    Update an existing context module. All fields are optional — only
    provided fields will be updated. Updated selectors are validated.
    """,
    responses={
        200: {"description": "Context module updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Context module not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_context_module(
    module_id: str,
    request: ContextModuleUpdateRequest,
) -> ContextModuleResponse:
    """Update a context module's fields.

    Args:
        module_id: Context module identifier.
        request: Update request with optional fields.

    Returns:
        Updated context module.
    """
    try:
        service = _get_service()

        # Build kwargs from non-None fields
        update_fields = {}
        if request.name is not None:
            update_fields["name"] = request.name
        if request.description is not None:
            update_fields["description"] = request.description
        if request.selectors is not None:
            update_fields["selectors"] = request.selectors
        if request.priority is not None:
            update_fields["priority"] = request.priority

        module = service.update(module_id, **update_fields)
        return ContextModuleResponse(**module)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            logger.warning(f"Context module not found for update: {module_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        logger.warning(f"Validation error updating context module: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        logger.exception(f"Failed to update context module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete(
    "/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a context module",
    description="""
    Delete a context module and its memory item associations.
    This is a permanent operation.
    """,
    responses={
        204: {"description": "Context module deleted successfully"},
        404: {"description": "Context module not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_context_module(module_id: str) -> None:
    """Delete a context module.

    Args:
        module_id: Context module identifier.
    """
    try:
        service = _get_service()
        deleted = service.delete(module_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context module not found: {module_id}",
            )
        logger.info(f"Deleted context module: {module_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete context module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# =============================================================================
# Memory Item Association Operations
# =============================================================================


@router.post(
    "/{module_id}/memories",
    response_model=ContextModuleResponse,
    summary="Add a memory item to a context module",
    description="""
    Associate a memory item with a context module. If the memory is already
    linked, the operation is idempotent and returns the current state.
    """,
    responses={
        200: {"description": "Memory item added (or already linked)"},
        400: {"description": "Validation error (module or memory not found)"},
        500: {"description": "Internal server error"},
    },
)
async def add_memory_to_module(
    module_id: str,
    request: AddMemoryToModuleRequest,
) -> ContextModuleResponse:
    """Add a memory item to a context module.

    Args:
        module_id: Context module identifier.
        request: Request with memory_id and optional ordering.

    Returns:
        Updated context module with memory items.
    """
    try:
        service = _get_service()
        result = service.add_memory(
            module_id=module_id,
            memory_id=request.memory_id,
            ordering=request.ordering,
        )
        return ContextModuleResponse(**result)
    except ValueError as e:
        logger.warning(f"Error adding memory to module: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to add memory to module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete(
    "/{module_id}/memories/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a memory item from a context module",
    description="""
    Remove the association between a memory item and a context module.
    The memory item itself is not deleted.
    """,
    responses={
        204: {"description": "Memory item removed from module"},
        404: {"description": "Association not found"},
        500: {"description": "Internal server error"},
    },
)
async def remove_memory_from_module(
    module_id: str,
    memory_id: str,
) -> None:
    """Remove a memory item from a context module.

    Args:
        module_id: Context module identifier.
        memory_id: Memory item identifier to remove.
    """
    try:
        service = _get_service()
        removed = service.remove_memory(module_id, memory_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory item '{memory_id}' not linked to module '{module_id}'",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Failed to remove memory {memory_id} from module {module_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{module_id}/memories",
    summary="List memory items in a context module",
    description="""
    Retrieve all memory items associated with a context module, ordered
    by their position within the module.
    """,
    responses={
        200: {"description": "Successfully retrieved module's memory items"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def list_module_memories(
    module_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return",
    ),
) -> List[dict]:
    """Get all memory items in a context module.

    Args:
        module_id: Context module identifier.
        limit: Maximum number of items to return.

    Returns:
        List of memory item dicts.
    """
    try:
        service = _get_service()
        items = service.get_memories(module_id, limit=limit)
        return items
    except ValueError as e:
        logger.warning(f"Error listing module memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error listing memories for module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
