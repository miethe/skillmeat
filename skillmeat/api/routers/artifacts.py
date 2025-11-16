"""Artifact management API endpoints.

Provides REST API for managing artifacts within collections.
"""

import base64
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import (
    APIKeyDep,
    ArtifactManagerDep,
    CollectionManagerDep,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    ArtifactListResponse,
    ArtifactMetadataResponse,
    ArtifactResponse,
    ArtifactUpstreamInfo,
    ArtifactUpstreamResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.core.artifact import ArtifactType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(APIKeyDep)],  # All endpoints require API key
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


def artifact_to_response(artifact) -> ArtifactResponse:
    """Convert Artifact model to API response schema.

    Args:
        artifact: Artifact instance

    Returns:
        ArtifactResponse schema
    """
    # Convert metadata
    metadata_response = None
    if artifact.metadata:
        metadata_response = ArtifactMetadataResponse(
            title=artifact.metadata.title,
            description=artifact.metadata.description,
            author=artifact.metadata.author,
            license=artifact.metadata.license,
            version=artifact.metadata.version,
            tags=artifact.metadata.tags,
            dependencies=artifact.metadata.dependencies,
        )

    # Convert upstream info
    upstream_response = None
    if artifact.origin == "github" and artifact.upstream:
        # Check if there's an update available (compare SHAs)
        update_available = False
        if artifact.resolved_sha and artifact.version_spec == "latest":
            # For "latest" version spec, we can check if upstream has changed
            # This is a simplified check; real implementation would call check_updates
            update_available = False  # Would need to fetch actual upstream SHA

        upstream_response = ArtifactUpstreamInfo(
            tracking_enabled=True,
            current_sha=artifact.resolved_sha,
            upstream_sha=None,  # Would need to fetch from upstream
            update_available=update_available,
            has_local_modifications=False,  # Would need to check via diff
        )

    # Determine version to display
    version = artifact.version_spec or "unknown"

    return ArtifactResponse(
        id=f"{artifact.type.value}:{artifact.name}",
        name=artifact.name,
        type=artifact.type.value,
        source=artifact.upstream if artifact.origin == "github" else "local",
        version=version,
        aliases=[],  # TODO: Add alias support when implemented
        metadata=metadata_response,
        upstream=upstream_response,
        added=artifact.added,
        updated=artifact.last_updated or artifact.added,
    )


@router.get(
    "",
    response_model=ArtifactListResponse,
    summary="List all artifacts",
    description="Retrieve a paginated list of artifacts across all collections",
    responses={
        200: {"description": "Successfully retrieved artifacts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_artifacts(
    artifact_mgr: ArtifactManagerDep,
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
    collection: Optional[str] = Query(
        default=None,
        description="Filter by collection name",
    ),
    tags: Optional[str] = Query(
        default=None,
        description="Filter by tags (comma-separated)",
    ),
) -> ArtifactListResponse:
    """List all artifacts with filters and pagination.

    Args:
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional type filter
        collection: Optional collection filter
        tags: Optional tag filter (comma-separated)

    Returns:
        Paginated list of artifacts

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(
            f"Listing artifacts (limit={limit}, after={after}, "
            f"type={artifact_type}, collection={collection}, tags={tags})"
        )

        # Parse filters
        type_filter = None
        if artifact_type:
            try:
                type_filter = ArtifactType(artifact_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact type: {artifact_type}",
                )

        tag_filter = None
        if tags:
            tag_filter = [t.strip() for t in tags.split(",") if t.strip()]

        # Get artifacts from specified collection or all collections
        if collection:
            # Check if collection exists
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            artifacts = artifact_mgr.list_artifacts(
                collection_name=collection,
                artifact_type=type_filter,
                tags=tag_filter,
            )
        else:
            # Get artifacts from all collections
            all_artifacts = []
            for coll_name in collection_mgr.list_collections():
                try:
                    coll_artifacts = artifact_mgr.list_artifacts(
                        collection_name=coll_name,
                        artifact_type=type_filter,
                        tags=tag_filter,
                    )
                    all_artifacts.extend(coll_artifacts)
                except Exception as e:
                    logger.error(
                        f"Error loading artifacts from collection '{coll_name}': {e}"
                    )
                    continue
            artifacts = all_artifacts

        # Sort artifacts for consistent pagination
        artifacts = sorted(artifacts, key=lambda a: (a.type.value, a.name))

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            # Cursor format: "type:name"
            artifact_keys = [f"{a.type.value}:{a.name}" for a in artifacts]
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

        # Convert to response format
        items: List[ArtifactResponse] = [
            artifact_to_response(artifact) for artifact in page_artifacts
        ]

        # Build pagination info
        has_next = end_idx < len(artifacts)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(f"{page_artifacts[0].type.value}:{page_artifacts[0].name}")
            if page_artifacts
            else None
        )
        end_cursor = (
            encode_cursor(f"{page_artifacts[-1].type.value}:{page_artifacts[-1].name}")
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

        logger.info(f"Retrieved {len(items)} artifacts")
        return ArtifactListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifacts: {str(e)}",
        )


@router.get(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Get artifact details",
    description="Retrieve detailed information about a specific artifact",
    responses={
        200: {"description": "Successfully retrieved artifact"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> ArtifactResponse:
    """Get details for a specific artifact.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection filter

    Returns:
        Artifact details

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(f"Getting artifact: {artifact_id} (collection={collection})")

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = artifact_id.split(":", 1)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Search for artifact
        artifact = None
        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                artifact = artifact_mgr.show(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection,
                )
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    artifact = artifact_mgr.show(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type,
                        collection_name=coll_name,
                    )
                    break  # Found it
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        return artifact_to_response(artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact: {str(e)}",
        )


@router.get(
    "/{artifact_id}/upstream",
    response_model=ArtifactUpstreamResponse,
    summary="Check upstream status",
    description="Check for updates and upstream status for an artifact",
    responses={
        200: {"description": "Successfully checked upstream status"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def check_artifact_upstream(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> ArtifactUpstreamResponse:
    """Check upstream status and available updates for an artifact.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection filter

    Returns:
        Upstream status information

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(f"Checking upstream for artifact: {artifact_id}")

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = artifact_id.split(":", 1)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact
        artifact = None
        collection_name = collection
        if collection:
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                artifact = artifact_mgr.show(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection,
                )
            except ValueError:
                pass
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    artifact = artifact_mgr.show(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type,
                        collection_name=coll_name,
                    )
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Check if artifact supports upstream tracking
        if artifact.origin != "github":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Artifact origin '{artifact.origin}' does not support upstream tracking",
            )

        if not artifact.upstream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Artifact does not have upstream tracking configured",
            )

        # Fetch update information
        fetch_result = artifact_mgr.fetch_update(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
        )

        # Check for errors
        if fetch_result.error:
            logger.warning(f"Error fetching upstream: {fetch_result.error}")
            # Return current status with no update available
            return ArtifactUpstreamResponse(
                artifact_id=artifact_id,
                tracking_enabled=True,
                current_version=artifact.resolved_version or artifact.version_spec or "unknown",
                current_sha=artifact.resolved_sha or "unknown",
                upstream_version=None,
                upstream_sha=None,
                update_available=False,
                has_local_modifications=False,
                last_checked=datetime.utcnow(),
            )

        # Extract update information
        update_info = fetch_result.update_info
        has_update = fetch_result.has_update

        upstream_version = None
        upstream_sha = None
        if update_info:
            upstream_version = getattr(update_info, "upstream_version", None)
            upstream_sha = getattr(update_info, "upstream_sha", None)

        return ArtifactUpstreamResponse(
            artifact_id=artifact_id,
            tracking_enabled=True,
            current_version=artifact.resolved_version or artifact.version_spec or "unknown",
            current_sha=artifact.resolved_sha or "unknown",
            upstream_version=upstream_version,
            upstream_sha=upstream_sha,
            update_available=has_update,
            has_local_modifications=getattr(update_info, "has_local_modifications", False) if update_info else False,
            last_checked=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error checking upstream for artifact '{artifact_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check upstream status: {str(e)}",
        )
