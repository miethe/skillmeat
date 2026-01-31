"""Collection management API endpoints (DEPRECATED).

WARNING: This router is deprecated. Use /user-collections endpoints instead.
These endpoints will be removed after 2025-06-01.

Migration guide:
- GET /collections → GET /user-collections
- GET /collections/{id} → GET /user-collections/{id}
- GET /collections/{id}/artifacts → GET /user-collections/{id}/artifacts

For full CRUD operations (create, update, delete), use /user-collections.
"""

import base64
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.collections import (
    ArtifactSummary,
    CollectionArtifactsResponse,
    CollectionListResponse,
    CollectionResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.core.artifact import ArtifactType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/collections",
    tags=["collections"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode

    Returns:
        Base64 encoded cursor string
    """
    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value

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


def add_deprecation_headers(response: Response, endpoint: str) -> None:
    """Add standard deprecation headers to response.

    Args:
        response: FastAPI Response object
        endpoint: Endpoint path (e.g., "", "/{id}", "/{id}/artifacts")
    """
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2025-06-01"
    response.headers["Link"] = (
        f'</api/v1/user-collections{endpoint}>; rel="successor-version"'
    )
    logger.warning(
        f"Deprecated endpoint called: /collections{endpoint}. "
        f"Use /user-collections{endpoint} instead. "
        f"This endpoint will be removed after 2025-06-01."
    )


@router.get(
    "",
    response_model=CollectionListResponse,
    summary="List all collections",
    description="Retrieve a paginated list of all collections with metadata",
    responses={
        200: {"description": "Successfully retrieved collections"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collections(
    response: Response,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
) -> CollectionListResponse:
    """List all collections with cursor-based pagination.

    Args:
        response: FastAPI response object for headers
        collection_mgr: Collection manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of collections

    Raises:
        HTTPException: On error
    """
    add_deprecation_headers(response, "")

    try:
        logger.info(f"Listing collections (limit={limit}, after={after})")

        # Get all collection names
        all_collection_names = collection_mgr.list_collections()

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                start_idx = all_collection_names.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: collection not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_names = all_collection_names[start_idx:end_idx]

        # Load collection details
        items: List[CollectionResponse] = []
        for name in page_names:
            try:
                collection = collection_mgr.load_collection(name)
                items.append(
                    CollectionResponse(
                        id=name,
                        name=collection.name,
                        version=collection.version,
                        artifact_count=len(collection.artifacts),
                        created=collection.created,
                        updated=collection.updated,
                    )
                )
            except Exception as e:
                logger.error(f"Error loading collection '{name}': {e}")
                continue

        # Build pagination info
        has_next = end_idx < len(all_collection_names)
        has_previous = start_idx > 0

        start_cursor = encode_cursor(page_names[0]) if page_names else None
        end_cursor = encode_cursor(page_names[-1]) if page_names else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_collection_names),
        )

        logger.info(f"Retrieved {len(items)} collections")
        return CollectionListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}",
        )


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Get collection details",
    description="Retrieve detailed information about a specific collection",
    responses={
        200: {"description": "Successfully retrieved collection"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_collection(
    collection_id: str,
    response: Response,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
) -> CollectionResponse:
    """Get details for a specific collection.

    Args:
        collection_id: Collection identifier
        response: FastAPI response object for headers
        collection_mgr: Collection manager dependency
        token: Authentication token

    Returns:
        Collection details

    Raises:
        HTTPException: If collection not found or on error
    """
    add_deprecation_headers(response, f"/{collection_id}")

    try:
        logger.info(f"Getting collection: {collection_id}")

        # Check if collection exists
        if collection_id not in collection_mgr.list_collections():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Load collection
        collection = collection_mgr.load_collection(collection_id)

        return CollectionResponse(
            id=collection_id,
            name=collection.name,
            version=collection.version,
            artifact_count=len(collection.artifacts),
            created=collection.created,
            updated=collection.updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection '{collection_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection: {str(e)}",
        )


@router.get(
    "/{collection_id}/artifacts",
    response_model=CollectionArtifactsResponse,
    summary="List artifacts in collection",
    description=(
        "Retrieve a paginated list of artifacts within a specific collection. "
        "NOTE: This endpoint uses legacy file-based collections and does NOT include "
        "collection membership information. Use /user-collections/{id}/artifacts instead "
        "for full database-backed functionality."
    ),
    responses={
        200: {"description": "Successfully retrieved artifacts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_artifacts(
    collection_id: str,
    response: Response,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
    artifact_type: Optional[str] = Query(
        default=None,
        description="Filter by artifact type (skill, command, agent)",
    ),
) -> CollectionArtifactsResponse:
    """List all artifacts in a collection with pagination.

    LIMITATION: This deprecated endpoint cannot include collection membership
    information because it operates on file-based artifacts (no database IDs).
    CollectionService.get_collection_membership_batch() requires database
    artifact IDs which don't exist in the legacy CollectionManager system.

    For collection membership info, use /user-collections/{id}/artifacts instead.

    Args:
        collection_id: Collection identifier
        response: FastAPI response object for headers
        collection_mgr: Collection manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional type filter

    Returns:
        Paginated list of artifacts (WITHOUT collection membership data)

    Raises:
        HTTPException: If collection not found or on error
    """
    add_deprecation_headers(response, f"/{collection_id}/artifacts")

    try:
        logger.info(
            f"Listing artifacts in collection '{collection_id}' "
            f"(limit={limit}, after={after}, type={artifact_type})"
        )

        # Check if collection exists
        if collection_id not in collection_mgr.list_collections():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Load collection
        collection = collection_mgr.load_collection(collection_id)

        # Filter artifacts by type if specified
        artifacts = collection.artifacts
        if artifact_type:
            try:
                type_filter = ArtifactType(artifact_type)
                artifacts = [a for a in artifacts if a.type == type_filter]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact type: {artifact_type}",
                )

        # Sort artifacts by name for consistent pagination
        artifacts = sorted(artifacts, key=lambda a: a.composite_key())

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            # Find artifact index by composite key
            artifact_keys = [a.composite_key() for a in artifacts]
            try:
                start_idx = artifact_keys.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: artifact not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_artifacts = artifacts[start_idx:end_idx]

        # NOTE: Cannot include collection memberships here because:
        # 1. This endpoint uses file-based CollectionManager (no database)
        # 2. CollectionService.get_collection_membership_batch() requires DB artifact IDs
        # 3. These Artifact objects only have name/type/source, not database IDs
        #
        # If this were database-backed (like /user-collections), the pattern would be:
        # from skillmeat.api.services import CollectionService
        # artifact_ids = [artifact.id for artifact in page_artifacts]  # Need DB IDs!
        # collection_service = CollectionService(db_session)
        # collections_map = collection_service.get_collection_membership_batch(artifact_ids)
        # Then include collections_map.get(artifact.id, []) in each ArtifactSummary

        # Convert to summary format (legacy file-based, no collection membership)
        items: List[ArtifactSummary] = [
            ArtifactSummary(
                name=artifact.name,
                type=artifact.type.value,
                version=artifact.version,
                source=artifact.source,
            )
            for artifact in page_artifacts
        ]

        # Build pagination info
        has_next = end_idx < len(artifacts)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(page_artifacts[0].composite_key()) if page_artifacts else None
        )
        end_cursor = (
            encode_cursor(page_artifacts[-1].composite_key())
            if page_artifacts
            else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(artifacts),
        )

        logger.info(
            f"Retrieved {len(items)} artifacts from collection '{collection_id}'"
        )
        return CollectionArtifactsResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error listing artifacts in collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifacts: {str(e)}",
        )
