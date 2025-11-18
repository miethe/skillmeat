"""Artifact management API endpoints.

Provides REST API for managing artifacts within collections.
"""

import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    ArtifactDeployRequest,
    ArtifactDeployResponse,
    ArtifactListResponse,
    ArtifactMetadataResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
    ArtifactUpstreamInfo,
    ArtifactUpstreamResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.deployment import DeploymentManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
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
                current_version=artifact.resolved_version
                or artifact.version_spec
                or "unknown",
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
            current_version=artifact.resolved_version
            or artifact.version_spec
            or "unknown",
            current_sha=artifact.resolved_sha or "unknown",
            upstream_version=upstream_version,
            upstream_sha=upstream_sha,
            update_available=has_update,
            has_local_modifications=(
                getattr(update_info, "has_local_modifications", False)
                if update_info
                else False
            ),
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


@router.put(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Update artifact",
    description="Update artifact metadata, tags, and aliases",
    responses={
        200: {"description": "Successfully updated artifact"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_artifact(
    artifact_id: str,
    update_request: ArtifactUpdateRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> ArtifactResponse:
    """Update an artifact's metadata, tags, and aliases.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        update_request: Update request containing new values
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection filter

    Returns:
        Updated artifact details

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(f"Updating artifact: {artifact_id} (collection={collection})")

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = artifact_id.split(":", 1)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact and its collection
        artifact = None
        collection_name = collection
        target_collection = None

        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                target_collection = collection_mgr.load_collection(collection)
                artifact = target_collection.find_artifact(artifact_name, artifact_type)
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    target_collection = collection_mgr.load_collection(coll_name)
                    artifact = target_collection.find_artifact(
                        artifact_name, artifact_type
                    )
                    collection_name = coll_name
                    break  # Found it
                except ValueError:
                    continue

        if not artifact or not target_collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Track if anything was updated
        updated = False

        # Update tags if provided
        if update_request.tags is not None:
            artifact.tags = update_request.tags
            updated = True
            logger.info(f"Updated tags for {artifact_id}: {update_request.tags}")

        # Update metadata fields if provided
        if update_request.metadata is not None:
            metadata_updates = update_request.metadata
            if metadata_updates.title is not None:
                artifact.metadata.title = metadata_updates.title
                updated = True
            if metadata_updates.description is not None:
                artifact.metadata.description = metadata_updates.description
                updated = True
            if metadata_updates.author is not None:
                artifact.metadata.author = metadata_updates.author
                updated = True
            if metadata_updates.license is not None:
                artifact.metadata.license = metadata_updates.license
                updated = True
            if metadata_updates.tags is not None:
                artifact.metadata.tags = metadata_updates.tags
                updated = True

            if updated:
                logger.info(f"Updated metadata for {artifact_id}")

        # Log warning for aliases (not yet implemented)
        if update_request.aliases is not None:
            logger.warning(
                f"Aliases update requested for {artifact_id} but aliases are not yet implemented"
            )

        # Update last_updated timestamp if anything changed
        if updated:
            artifact.last_updated = datetime.utcnow()

            # Save collection
            collection_mgr.save_collection(target_collection)

            # Update lock file (content hash may not have changed, but metadata did)
            collection_path = collection_mgr.config.get_collection_path(collection_name)
            artifact_path = collection_path / artifact.path

            # Compute content hash for lock file
            from skillmeat.utils.filesystem import compute_content_hash

            content_hash = compute_content_hash(artifact_path)
            collection_mgr.lock_mgr.update_entry(
                collection_path,
                artifact.name,
                artifact.type,
                artifact.upstream,
                artifact.resolved_sha,
                artifact.resolved_version,
                content_hash,
            )

            logger.info(f"Successfully updated artifact: {artifact_id}")
        else:
            logger.info(f"No changes made to artifact: {artifact_id}")

        return artifact_to_response(artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update artifact: {str(e)}",
        )


@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete artifact",
    description="Remove an artifact from the collection",
    responses={
        204: {"description": "Successfully deleted artifact"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_artifact(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> None:
    """Delete an artifact from the collection.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection filter

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(f"Deleting artifact: {artifact_id} (collection={collection})")

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = artifact_id.split(":", 1)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact to determine its collection if not specified
        collection_name = collection
        found = False

        if collection:
            # Check specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                target_collection = collection_mgr.load_collection(collection)
                artifact = target_collection.find_artifact(artifact_name, artifact_type)
                if artifact:
                    found = True
                    collection_name = collection
            except ValueError:
                pass  # Not found
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    target_collection = collection_mgr.load_collection(coll_name)
                    artifact = target_collection.find_artifact(
                        artifact_name, artifact_type
                    )
                    if artifact:
                        found = True
                        collection_name = coll_name
                        break
                except ValueError:
                    continue

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Remove artifact using artifact manager
        # This handles filesystem cleanup, collection update, and lock file update
        try:
            artifact_mgr.remove(artifact_name, artifact_type, collection_name)
            logger.info(f"Successfully deleted artifact: {artifact_id}")
        except ValueError as e:
            # Artifact not found (race condition)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found: {str(e)}",
            )

        # Return 204 No Content (no body)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete artifact: {str(e)}",
        )


@router.post(
    "/{artifact_id}/deploy",
    response_model=ArtifactDeployResponse,
    summary="Deploy artifact to project",
    description="Deploy artifact from collection to project's .claude/ directory",
    responses={
        200: {"description": "Artifact deployed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def deploy_artifact(
    artifact_id: str,
    request: ArtifactDeployRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> ArtifactDeployResponse:
    """Deploy artifact from collection to project.

    Copies the artifact to the project's .claude/ directory and tracks
    the deployment in .skillmeat-deployed.toml.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        request: Deployment request with project_path and overwrite flag
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        Deployment result

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(
            f"Deploying artifact: {artifact_id} to {request.project_path} (collection={collection})"
        )

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = artifact_id.split(":", 1)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Validate project path
        project_path = Path(request.project_path)
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project path does not exist: {request.project_path}",
            )

        # Get or create collection
        if collection:
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection_name = collection
        else:
            collections = collection_mgr.list_collections()
            if not collections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No collections found",
                )
            collection_name = collections[0]

        # Load collection and find artifact
        coll = collection_mgr.load_collection(collection_name)
        artifact = coll.find_artifact(artifact_name, artifact_type)

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in collection '{collection_name}'",
            )

        # Create deployment manager
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Deploy artifact
        try:
            deployments = deployment_mgr.deploy_artifacts(
                artifact_names=[artifact_name],
                collection_name=collection_name,
                project_path=project_path,
                artifact_type=artifact_type,
            )

            if not deployments:
                # Deployment was skipped (likely user declined overwrite prompt)
                return ArtifactDeployResponse(
                    success=False,
                    message=f"Deployment of '{artifact_name}' was skipped",
                    artifact_name=artifact_name,
                    artifact_type=artifact_type.value,
                    error_message="Deployment cancelled or artifact not found",
                )

            deployment = deployments[0]

            # Determine deployed path
            deployed_path = project_path / ".claude" / deployment.artifact_path
            logger.info(
                f"Artifact '{artifact_name}' deployed successfully to {deployed_path}"
            )

            return ArtifactDeployResponse(
                success=True,
                message=f"Artifact '{artifact_name}' deployed successfully",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                deployed_path=str(deployed_path),
            )

        except ValueError as e:
            # Business logic error (e.g., artifact not found)
            logger.warning(f"Deployment failed for '{artifact_name}': {e}")
            return ArtifactDeployResponse(
                success=False,
                message=f"Deployment failed: {str(e)}",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                error_message=str(e),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy artifact: {str(e)}",
        )


@router.post(
    "/{artifact_id}/undeploy",
    response_model=ArtifactDeployResponse,
    summary="Undeploy artifact from project",
    description="Remove deployed artifact from project's .claude/ directory",
    responses={
        200: {"description": "Artifact undeployed successfully"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def undeploy_artifact(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    project_path: str = Body(..., embed=True, description="Project path"),
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> ArtifactDeployResponse:
    """Remove deployed artifact from project.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        project_path: Project directory path
        collection: Optional collection name

    Returns:
        Undeploy result

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(f"Undeploying artifact: {artifact_id} from {project_path}")

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = artifact_id.split(":", 1)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Validate project path
        proj_path = Path(project_path)
        if not proj_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project path does not exist: {project_path}",
            )

        # Create deployment manager
        deployment_mgr = DeploymentManager(collection_mgr=collection_mgr)

        # Undeploy artifact
        try:
            deployment_mgr.undeploy(
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                project_path=proj_path,
            )

            logger.info(f"Artifact '{artifact_name}' undeployed successfully")

            return ArtifactDeployResponse(
                success=True,
                message=f"Artifact '{artifact_name}' undeployed successfully",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
            )

        except ValueError as e:
            # Business logic error (e.g., artifact not deployed)
            logger.warning(f"Undeploy failed for '{artifact_name}': {e}")
            return ArtifactDeployResponse(
                success=False,
                message=f"Undeploy failed: {str(e)}",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                error_message=str(e),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error undeploying artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to undeploy artifact: {str(e)}",
        )
