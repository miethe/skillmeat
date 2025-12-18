"""Tag management API endpoints.

This router provides endpoints for creating and managing tags for artifact
organization. Tags support flexible categorization with unique slugs and
custom colors.

API Endpoints:
    GET /tags - List all tags with pagination
    POST /tags - Create new tag
    GET /tags/{tag_id} - Get tag by ID
    GET /tags/slug/{slug} - Get tag by slug
    PUT /tags/{tag_id} - Update tag
    DELETE /tags/{tag_id} - Delete tag
    GET /tags/search - Search tags by name

Note: Artifact-tag association endpoints (GET/POST/DELETE) should be implemented
in the artifacts router to avoid path conflicts with tag CRUD operations.
"""

import base64
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.schemas.common import PageInfo
from skillmeat.api.schemas.tags import (
    TagCreateRequest,
    TagListResponse,
    TagResponse,
    TagUpdateRequest,
)
from skillmeat.core.services import TagService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
)


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode (tag ID)

    Returns:
        Base64 encoded cursor string
    """
    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value (tag ID)

    Raises:
        HTTPException: If cursor is invalid
    """
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


# =============================================================================
# Tag CRUD Operations
# =============================================================================


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new tag",
    description="""
    Create a new tag for organizing artifacts.

    Tag names and slugs must be unique across the system. The slug should be
    a URL-friendly kebab-case identifier. Colors are optional hex codes for
    visual customization.
    """,
    responses={
        201: {"description": "Tag created successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Tag name or slug already exists"},
        500: {"description": "Internal server error"},
    },
)
async def create_tag(request: TagCreateRequest) -> TagResponse:
    """Create a new tag.

    Args:
        request: Tag creation request with name, slug, and optional color

    Returns:
        Created tag with metadata

    Raises:
        HTTPException 400: If request data is invalid
        HTTPException 409: If tag name or slug already exists
        HTTPException 500: If creation fails
    """
    service = TagService()

    try:
        logger.info(f"Creating tag: {request.name} (slug: {request.slug})")

        tag = service.create_tag(
            name=request.name,
            slug=request.slug,
            color=request.color,
        )

        logger.info(f"Created tag: {tag.id} ('{tag.name}')")

        return TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            artifact_count=service.get_tag_artifact_count(tag.id),
        )

    except ValueError as e:
        logger.warning(f"Tag creation validation error: {e}")
        # ValueError indicates duplicate name/slug
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    except Exception as e:
        logger.error(f"Failed to create tag: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tag: {str(e)}",
        )


@router.get(
    "",
    response_model=TagListResponse,
    summary="List all tags",
    description="""
    Retrieve a paginated list of all tags with artifact counts.

    Results are ordered by name (ascending) and support cursor-based pagination.
    """,
    responses={
        200: {"description": "Tags retrieved successfully"},
        400: {"description": "Invalid pagination cursor"},
        500: {"description": "Internal server error"},
    },
)
async def list_tags(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
) -> TagListResponse:
    """List all tags with cursor-based pagination.

    Args:
        limit: Number of items per page (1-100)
        after: Cursor for next page

    Returns:
        Paginated list of tags with counts

    Raises:
        HTTPException 400: If cursor is invalid
        HTTPException 500: If listing fails
    """
    service = TagService()

    try:
        logger.info(f"Listing tags (limit={limit}, after={after})")

        # Get all tags ordered by name
        all_tags = service.list_tags(order_by="name")

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_id = decode_cursor(after)
            # Find tag index by ID
            tag_ids = [tag.id for tag in all_tags]
            try:
                start_idx = tag_ids.index(cursor_id) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: tag not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_tags = all_tags[start_idx:end_idx]

        # Convert to response format with artifact counts
        items: List[TagResponse] = []
        for tag in page_tags:
            items.append(
                TagResponse(
                    id=tag.id,
                    name=tag.name,
                    slug=tag.slug,
                    color=tag.color,
                    created_at=tag.created_at,
                    updated_at=tag.updated_at,
                    artifact_count=service.get_tag_artifact_count(tag.id),
                )
            )

        # Build pagination info
        has_next = end_idx < len(all_tags)
        has_previous = start_idx > 0

        start_cursor = encode_cursor(page_tags[0].id) if page_tags else None
        end_cursor = encode_cursor(page_tags[-1].id) if page_tags else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_tags),
        )

        logger.info(f"Retrieved {len(items)} tags")
        return TagListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tags: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tags: {str(e)}",
        )


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Get tag by ID",
    description="Retrieve detailed information about a specific tag by its ID.",
    responses={
        200: {"description": "Tag retrieved successfully"},
        404: {"description": "Tag not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_tag(tag_id: str) -> TagResponse:
    """Get tag by ID.

    Args:
        tag_id: Tag identifier

    Returns:
        Tag details with artifact count

    Raises:
        HTTPException 404: If tag not found
        HTTPException 500: If retrieval fails
    """
    service = TagService()

    try:
        logger.info(f"Getting tag: {tag_id}")

        tag = service.get_tag_by_id(tag_id)

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag '{tag_id}' not found",
            )

        return TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            artifact_count=service.get_tag_artifact_count(tag.id),
        )

    except HTTPException:
        raise
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag '{tag_id}' not found",
        )
    except Exception as e:
        logger.error(f"Failed to get tag '{tag_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tag: {str(e)}",
        )


@router.get(
    "/slug/{slug}",
    response_model=TagResponse,
    summary="Get tag by slug",
    description="Retrieve detailed information about a specific tag by its URL slug.",
    responses={
        200: {"description": "Tag retrieved successfully"},
        404: {"description": "Tag not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_tag_by_slug(slug: str) -> TagResponse:
    """Get tag by slug.

    Args:
        slug: Tag URL slug (kebab-case)

    Returns:
        Tag details with artifact count

    Raises:
        HTTPException 404: If tag not found
        HTTPException 500: If retrieval fails
    """
    service = TagService()

    try:
        logger.info(f"Getting tag by slug: {slug}")

        tag = service.get_tag_by_slug(slug)

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with slug '{slug}' not found",
            )

        return TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            artifact_count=service.get_tag_artifact_count(tag.id),
        )

    except HTTPException:
        raise
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag with slug '{slug}' not found",
        )
    except Exception as e:
        logger.error(f"Failed to get tag by slug '{slug}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tag: {str(e)}",
        )


@router.put(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update tag",
    description="""
    Update tag metadata. All fields are optional for partial updates.

    If slug is updated, it must remain unique across the system.
    """,
    responses={
        200: {"description": "Tag updated successfully"},
        400: {"description": "Invalid request data"},
        404: {"description": "Tag not found"},
        409: {"description": "Updated slug already exists"},
        500: {"description": "Internal server error"},
    },
)
async def update_tag(tag_id: str, request: TagUpdateRequest) -> TagResponse:
    """Update tag metadata.

    Args:
        tag_id: Tag identifier
        request: Tag update request with optional name, slug, color

    Returns:
        Updated tag details

    Raises:
        HTTPException 400: If request data is invalid
        HTTPException 404: If tag not found
        HTTPException 409: If updated slug already exists
        HTTPException 500: If update fails
    """
    service = TagService()

    try:
        logger.info(f"Updating tag: {tag_id}")

        # Build update dict from request
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.slug is not None:
            updates["slug"] = request.slug
        if request.color is not None:
            updates["color"] = request.color

        if not updates:
            # No fields to update, just return current tag
            tag = service.get_tag_by_id(tag_id)
            if not tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tag '{tag_id}' not found",
                )
        else:
            tag = service.update_tag(tag_id, **updates)

        logger.info(f"Updated tag: {tag.id} ('{tag.name}')")

        return TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            artifact_count=service.get_tag_artifact_count(tag.id),
        )

    except ValueError as e:
        logger.warning(f"Tag update validation error: {e}")
        # ValueError indicates duplicate slug or validation failure
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag '{tag_id}' not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tag '{tag_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tag: {str(e)}",
        )


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tag",
    description="""
    Delete a tag by ID.

    This removes the tag and all associations with artifacts. Artifacts
    themselves are not affected.
    """,
    responses={
        204: {"description": "Tag deleted successfully"},
        404: {"description": "Tag not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_tag(tag_id: str) -> None:
    """Delete tag by ID.

    Args:
        tag_id: Tag identifier

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 404: If tag not found
        HTTPException 500: If deletion fails
    """
    service = TagService()

    try:
        logger.info(f"Deleting tag: {tag_id}")

        service.delete_tag(tag_id)

        logger.info(f"Deleted tag: {tag_id}")

    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag '{tag_id}' not found",
        )
    except Exception as e:
        logger.error(f"Failed to delete tag '{tag_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tag: {str(e)}",
        )


# =============================================================================
# Tag Search
# =============================================================================


@router.get(
    "/search",
    response_model=List[TagResponse],
    summary="Search tags by name",
    description="""
    Search for tags by name (case-insensitive substring match).

    Results are limited to 50 tags and ordered by name.
    """,
    responses={
        200: {"description": "Search completed successfully"},
        400: {"description": "Invalid search query"},
        500: {"description": "Internal server error"},
    },
)
async def search_tags(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search query (case-insensitive)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of results",
    ),
) -> List[TagResponse]:
    """Search tags by name.

    Args:
        q: Search query (case-insensitive substring)
        limit: Maximum number of results (1-100)

    Returns:
        List of matching tags with counts

    Raises:
        HTTPException 400: If query is invalid
        HTTPException 500: If search fails
    """
    service = TagService()

    try:
        logger.info(f"Searching tags: query='{q}', limit={limit}")

        tags = service.search_tags(query=q, limit=limit)

        results: List[TagResponse] = []
        for tag in tags:
            results.append(
                TagResponse(
                    id=tag.id,
                    name=tag.name,
                    slug=tag.slug,
                    color=tag.color,
                    created_at=tag.created_at,
                    updated_at=tag.updated_at,
                    artifact_count=service.get_tag_artifact_count(tag.id),
                )
            )

        logger.info(f"Found {len(results)} matching tags")
        return results

    except ValueError as e:
        logger.warning(f"Tag search validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to search tags: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search tags: {str(e)}",
        )


# =============================================================================
# Note: Artifact-Tag Association Endpoints
# =============================================================================
#
# The following endpoints should be implemented in the artifacts router
# to avoid path conflicts with tag CRUD operations:
#
#   GET /artifacts/{artifact_id}/tags - Get tags for artifact
#   POST /artifacts/{artifact_id}/tags/{tag_id} - Add tag to artifact
#   DELETE /artifacts/{artifact_id}/tags/{tag_id} - Remove tag from artifact
#
# See API-006 to API-008 in the tags refactor implementation plan.
