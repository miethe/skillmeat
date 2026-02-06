"""Context packing API router for the Memory & Context Intelligence System.

This router provides endpoints for composing context packs from memory items.
Context packs are token-budget-aware compilations of memory items into
structured markdown suitable for injection into agent prompts.

Two modes of operation:
- Preview: read-only selection showing what items would be included and
  estimated token usage without generating markdown.
- Generate: full pack with structured markdown grouped by memory type,
  including confidence annotations and a generation timestamp.

API Endpoints:
    POST /context-packs/preview   - Preview pack contents (read-only)
    POST /context-packs/generate  - Generate full pack with markdown
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from skillmeat.api.schemas.context_module import (
    ContextPackGenerateRequest,
    ContextPackGenerateResponse,
    ContextPackPreviewRequest,
    ContextPackPreviewResponse,
)
from skillmeat.core.services.context_packer_service import ContextPackerService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/context-packs",
    tags=["context-packs"],
)


def _get_service() -> ContextPackerService:
    """Get a ContextPackerService instance with default database path.

    Returns:
        Initialized ContextPackerService.
    """
    return ContextPackerService(db_path=None)


# =============================================================================
# Context Pack Operations
# =============================================================================


@router.post(
    "/preview",
    response_model=ContextPackPreviewResponse,
    summary="Preview a context pack (read-only)",
    description="""
    Preview what a context pack would contain without generating markdown.

    Performs read-only selection of memory items based on module selectors,
    additional filters, and token budget constraints. Items are selected by
    confidence (descending) then recency (descending).

    Use this to estimate token usage and see which items would be included
    before committing to a full generation.
    """,
    responses={
        200: {"description": "Successfully generated pack preview"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"},
    },
)
async def preview_context_pack(
    request: ContextPackPreviewRequest,
    project_id: str = Query(..., description="Project ID to build pack for"),
) -> ContextPackPreviewResponse:
    """Preview what a context pack would contain.

    Args:
        request: Pack preview request with optional module, budget, and filters.
        project_id: Project scope for the pack.

    Returns:
        Preview response with selected items and token statistics.
    """
    try:
        service = _get_service()
        result = service.preview_pack(
            project_id=project_id,
            module_id=request.module_id,
            budget_tokens=request.budget_tokens,
            filters=request.filters,
        )
        return ContextPackPreviewResponse(**result)
    except ValueError as e:
        logger.warning(f"Validation error previewing context pack: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to preview context pack: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/generate",
    response_model=ContextPackGenerateResponse,
    summary="Generate a context pack with markdown",
    description="""
    Generate a full context pack with structured markdown output.

    Performs the same selection as preview, then generates markdown grouped
    by memory type with confidence annotations. The generated markdown is
    suitable for direct injection into agent prompts or CLAUDE.md files.

    Confidence tiers in output:
    - High (>= 0.85): no label
    - Medium (0.60 - 0.84): [medium confidence]
    - Low (< 0.60): [low confidence]
    """,
    responses={
        200: {"description": "Successfully generated context pack"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"},
    },
)
async def generate_context_pack(
    request: ContextPackGenerateRequest,
    project_id: str = Query(..., description="Project ID to build pack for"),
) -> ContextPackGenerateResponse:
    """Generate a full context pack with markdown.

    Args:
        request: Pack generation request with optional module, budget, and filters.
        project_id: Project scope for the pack.

    Returns:
        Generated pack with items, statistics, and formatted markdown.
    """
    try:
        service = _get_service()
        result = service.generate_pack(
            project_id=project_id,
            module_id=request.module_id,
            budget_tokens=request.budget_tokens,
            filters=request.filters,
        )
        return ContextPackGenerateResponse(**result)
    except ValueError as e:
        logger.warning(f"Validation error generating context pack: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to generate context pack: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
