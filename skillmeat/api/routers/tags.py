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

from skillmeat.api.dependencies import CollectionManagerDep
from skillmeat.api.schemas.common import PageInfo
from skillmeat.api.schemas.tags import (
    TagCreateRequest,
    TagListResponse,
    TagResponse,
    TagUpdateRequest,
)

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
    from skillmeat.core.services import TagService

    service = TagService()

    try:
        logger.info(f"Creating tag: {request.name} (slug: {request.slug})")

        tag = service.create_tag(request)

        logger.info(f"Created tag: {tag.id} ('{tag.name}')")

        return tag

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
    from skillmeat.core.services import TagService

    service = TagService()

    try:
        logger.info(f"Listing tags (limit={limit}, after={after})")

        # Decode cursor if provided
        after_cursor = None
        if after:
            after_cursor = decode_cursor(after)

        # Get tags with pagination from service
        response = service.list_tags(limit=limit, after_cursor=after_cursor)

        logger.info(f"Retrieved {len(response.items)} tags")
        return response

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
    from skillmeat.core.services import TagService

    service = TagService()

    try:
        logger.info(f"Getting tag: {tag_id}")

        tag = service.get_tag(tag_id)

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag '{tag_id}' not found",
            )

        return tag

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
    from skillmeat.core.services import TagService

    service = TagService()

    try:
        logger.info(f"Getting tag by slug: {slug}")

        tag = service.get_tag_by_slug(slug)

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with slug '{slug}' not found",
            )

        return tag

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
async def update_tag(
    tag_id: str, request: TagUpdateRequest, collection_mgr: CollectionManagerDep
) -> TagResponse:
    """Update tag metadata.

    If the tag name is changing, the rename is written back to filesystem
    sources (collection.toml and artifact frontmatter) so the change
    persists through cache refreshes.

    Args:
        tag_id: Tag identifier
        request: Tag update request with optional name, slug, color
        collection_mgr: Injected CollectionManager for filesystem write-back

    Returns:
        Updated tag details

    Raises:
        HTTPException 400: If request data is invalid
        HTTPException 404: If tag not found
        HTTPException 409: If updated slug already exists
        HTTPException 500: If update fails
    """
    from skillmeat.core.services import TagService
    from skillmeat.core.services.tag_write_service import TagWriteService

    service = TagService()
    write_service = TagWriteService()

    try:
        logger.info(f"Updating tag: {tag_id}")

        affected_artifacts = []

        # If name is changing, write-back to filesystem
        if request.name is not None:
            existing_tag = service.get_tag(tag_id)
            if existing_tag and existing_tag.name != request.name:
                result = write_service.rename_tag(
                    old_name=existing_tag.name,
                    new_name=request.name,
                    collection_manager=collection_mgr,
                )
                affected_artifacts = result.get("affected_artifacts", [])
                if affected_artifacts:
                    logger.info(
                        f"Renamed tag '{existing_tag.name}' -> '{request.name}' "
                        f"in {len(affected_artifacts)} artifacts on filesystem"
                    )

        # Update tag in DB via service
        tag = service.update_tag(tag_id, request)

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag '{tag_id}' not found",
            )

        # Update tags_json cache for affected artifacts
        if affected_artifacts:
            write_service.update_tags_json_cache(affected_artifacts)

        logger.info(f"Updated tag: {tag.id} ('{tag.name}')")

        return tag

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
async def delete_tag(tag_id: str, collection_mgr: CollectionManagerDep) -> None:
    """Delete tag by ID.

    The tag is first removed from filesystem sources (collection.toml and
    artifact frontmatter) so the deletion persists through cache refreshes,
    then deleted from the database (CASCADE removes artifact_tags rows).

    Args:
        tag_id: Tag identifier
        collection_mgr: Injected CollectionManager for filesystem write-back

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 404: If tag not found
        HTTPException 500: If deletion fails
    """
    from skillmeat.core.services import TagService
    from skillmeat.core.services.tag_write_service import TagWriteService

    service = TagService()
    write_service = TagWriteService()

    try:
        logger.info(f"Deleting tag: {tag_id}")

        # Look up tag name before deleting
        tag = service.get_tag(tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag '{tag_id}' not found",
            )

        # Write-back: remove tag from filesystem sources
        result = write_service.delete_tag(
            tag_name=tag.name,
            collection_manager=collection_mgr,
        )
        if result["affected_artifacts"]:
            logger.info(
                f"Removed tag '{tag.name}' from {len(result['affected_artifacts'])} "
                f"artifacts on filesystem"
            )

        # Delete from DB (CASCADE removes artifact_tags rows)
        service.delete_tag(tag_id)

        # Update tags_json cache for affected artifacts
        if result["affected_artifacts"]:
            write_service.update_tags_json_cache(result["affected_artifacts"])

        logger.info(f"Deleted tag: {tag_id}")

    except HTTPException:
        raise
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
    from skillmeat.core.services import TagService

    service = TagService()

    try:
        logger.info(f"Searching tags: query='{q}', limit={limit}")

        results = service.search_tags(query=q, limit=limit)

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
