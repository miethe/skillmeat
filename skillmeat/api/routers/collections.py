"""Collection management API endpoints.

Provides REST API for managing collections of Claude artifacts.
"""

import base64
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
        collection_mgr: Collection manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of collections

    Raises:
        HTTPException: On error
    """
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
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
) -> CollectionResponse:
    """Get details for a specific collection.

    Args:
        collection_id: Collection identifier
        collection_mgr: Collection manager dependency
        token: Authentication token

    Returns:
        Collection details

    Raises:
        HTTPException: If collection not found or on error
    """
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
    description="Retrieve a paginated list of artifacts within a specific collection",
    responses={
        200: {"description": "Successfully retrieved artifacts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_artifacts(
    collection_id: str,
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

    Args:
        collection_id: Collection identifier
        collection_mgr: Collection manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional type filter

    Returns:
        Paginated list of artifacts

    Raises:
        HTTPException: If collection not found or on error
    """
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

        # Convert to summary format
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

        logger.info(f"Retrieved {len(items)} artifacts from collection '{collection_id}'")
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
