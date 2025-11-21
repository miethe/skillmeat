"""Artifact management API endpoints.

Provides REST API for managing artifacts within collections.
"""

import base64
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    SyncManagerDep,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    ArtifactDeployRequest,
    ArtifactDeployResponse,
    ArtifactListResponse,
    ArtifactMetadataResponse,
    ArtifactResponse,
    ArtifactSyncRequest,
    ArtifactSyncResponse,
    ArtifactUpdateRequest,
    ArtifactUpstreamInfo,
    ArtifactUpstreamResponse,
    ArtifactVersionInfo,
    ConflictInfo,
    DeploymentStatistics,
    ProjectDeploymentInfo,
    VersionGraphNodeResponse,
    VersionGraphResponse,
)
from skillmeat.api.schemas.artifact_diff import ArtifactDiffResponse, ArtifactFileDiff
from skillmeat.api.schemas.artifact_versions import (
    ArtifactTierVersion,
    ArtifactVersionsResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.deployment import DeploymentManager
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash
from skillmeat.core.diff_engine import DiffEngine
from skillmeat.core.sync import SyncManager

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


def _get_artifact_paths(
    artifact_type: ArtifactType,
    artifact_name: str,
    collection_mgr: CollectionManager,
    collection: Optional[str],
    project_path: Optional[str],
    sync_mgr: SyncManager,
) -> tuple[Path, Optional[Path]]:
    """Return collection and project artifact paths."""
    collection_obj = collection_mgr.get_collection(collection)
    plural = sync_mgr._get_artifact_type_plural(artifact_type.value)  # noqa: SLF001
    coll_base = collection_obj.path / plural
    coll_path = coll_base / artifact_name
    if artifact_type.value in {"command", "agent"} and coll_path.is_dir():
        possible_file = coll_base / f"{artifact_name}.md"
        if possible_file.exists():
            coll_path = possible_file
    if not coll_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found in collection at {coll_path}",
        )

    proj_path = None
    if project_path:
        base = Path(project_path) / ".claude" / plural
        if artifact_type.value in {"command", "agent"}:
            proj_candidate = base / f"{artifact_name}.md"
        else:
            proj_candidate = base / artifact_name
        if proj_candidate.exists():
            proj_path = proj_candidate
    return coll_path, proj_path


async def build_deployment_statistics(
    artifact_name: str,
    artifact_type: ArtifactType,
) -> DeploymentStatistics:
    """Build deployment statistics for an artifact across all projects.

    Scans all discoverable projects to find deployments of this artifact
    and compiles statistics about deployment count and modification status.

    Args:
        artifact_name: Name of the artifact
        artifact_type: Type of the artifact

    Returns:
        DeploymentStatistics with per-project information

    Note:
        This function scans the filesystem for projects, which may be slow
        for large directory structures. Consider implementing caching.
    """
    from skillmeat.api.routers.projects import discover_projects

    # Discover all projects
    project_paths = discover_projects()

    total_deployments = 0
    modified_deployments = 0
    projects_info: List[ProjectDeploymentInfo] = []

    for project_path in project_paths:
        try:
            # Load deployments for this project
            deployments = DeploymentTracker.read_deployments(project_path)

            # Find our artifact
            for deployment in deployments:
                if (
                    deployment.artifact_name == artifact_name
                    and deployment.artifact_type == artifact_type.value
                ):
                    total_deployments += 1

                    # Check if modified
                    artifact_full_path = (
                        project_path / ".claude" / deployment.artifact_path
                    )
                    is_modified = False

                    if artifact_full_path.exists():
                        try:
                            current_sha = compute_content_hash(artifact_full_path)
                            is_modified = current_sha != deployment.collection_sha
                        except Exception as e:
                            logger.warning(
                                f"Failed to check modification for {artifact_name} in {project_path}: {e}"
                            )

                    if is_modified:
                        modified_deployments += 1

                    projects_info.append(
                        ProjectDeploymentInfo(
                            project_name=project_path.name,
                            project_path=str(project_path),
                            is_modified=is_modified,
                            deployed_at=deployment.deployed_at,
                        )
                    )
                    break  # Only one deployment of this artifact per project

        except Exception as e:
            logger.warning(f"Error processing project {project_path}: {e}")
            continue

    return DeploymentStatistics(
        total_deployments=total_deployments,
        modified_deployments=modified_deployments,
        projects=projects_info,
    )


async def build_version_graph(
    artifact_name: str,
    artifact_type: ArtifactType,
    collection_name: Optional[str] = None,
    collection_mgr = None,
) -> VersionGraphResponse:
    """Build version graph for an artifact showing deployment hierarchy.

    Creates a tree structure with the collection version as the root and
    project deployments as children, tracking content hashes and modifications.

    Args:
        artifact_name: Name of the artifact
        artifact_type: Type of the artifact
        collection_name: Optional collection filter
        collection_mgr: Collection manager for accessing collection data

    Returns:
        VersionGraphResponse with complete hierarchy and statistics
    """
    from skillmeat.api.routers.projects import discover_projects

    # Find the artifact in collection (root node)
    root_node: Optional[VersionGraphNodeResponse] = None
    collection_sha: Optional[str] = None

    if collection_mgr:
        # Search for artifact in collection
        collections_to_search = (
            [collection_name] if collection_name else collection_mgr.list_collections()
        )

        for coll_name in collections_to_search:
            try:
                coll = collection_mgr.load_collection(coll_name)
                artifact = coll.find_artifact(artifact_name, artifact_type)

                if artifact:
                    # Compute collection version SHA
                    collection_path = collection_mgr.config.get_collection_path(
                        coll_name
                    )
                    artifact_path = collection_path / artifact.path

                    if artifact_path.exists():
                        collection_sha = compute_content_hash(artifact_path)

                        # Create root version info
                        version_info = ArtifactVersionInfo(
                            artifact_name=artifact_name,
                            artifact_type=artifact_type.value,
                            location=coll_name,
                            location_type="collection",
                            content_sha=collection_sha,
                            parent_sha=None,  # Collection is root
                            is_modified=False,
                            created_at=artifact.added,
                            metadata={"collection_name": coll_name},
                        )

                        root_node = VersionGraphNodeResponse(
                            id=f"collection:{coll_name}:{collection_sha[:8]}",
                            artifact_name=artifact_name,
                            artifact_type=artifact_type.value,
                            version_info=version_info,
                            children=[],
                            metadata={"collection_name": coll_name},
                        )
                        break  # Found in this collection

            except Exception as e:
                logger.warning(
                    f"Error loading artifact from collection {coll_name}: {e}"
                )
                continue

    # Discover all project deployments
    project_paths = discover_projects()
    total_deployments = 0
    modified_count = 0
    unmodified_count = 0

    children: List[VersionGraphNodeResponse] = []

    for project_path in project_paths:
        try:
            # Load deployments for this project
            deployments = DeploymentTracker.read_deployments(project_path)

            # Find our artifact
            for deployment in deployments:
                if (
                    deployment.artifact_name == artifact_name
                    and deployment.artifact_type == artifact_type.value
                ):
                    total_deployments += 1

                    # Compute current SHA
                    artifact_full_path = (
                        project_path / ".claude" / deployment.artifact_path
                    )

                    if not artifact_full_path.exists():
                        continue

                    current_sha = compute_content_hash(artifact_full_path)
                    is_modified = current_sha != deployment.collection_sha

                    if is_modified:
                        modified_count += 1
                    else:
                        unmodified_count += 1

                    # Create child node
                    child_version_info = ArtifactVersionInfo(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type.value,
                        location=str(project_path),
                        location_type="project",
                        content_sha=current_sha,
                        parent_sha=collection_sha,  # Parent is collection
                        is_modified=is_modified,
                        created_at=deployment.deployed_at,
                        metadata={
                            "project_name": project_path.name,
                            "deployed_at": deployment.deployed_at.isoformat(),
                            "modification_detected_at": (
                                deployment.modification_detected_at.isoformat()
                                if deployment.modification_detected_at
                                else None
                            ),
                        },
                    )

                    child_node = VersionGraphNodeResponse(
                        id=f"project:{project_path}",
                        artifact_name=artifact_name,
                        artifact_type=artifact_type.value,
                        version_info=child_version_info,
                        children=[],  # Projects don't have children
                        metadata={"project_name": project_path.name},
                    )

                    children.append(child_node)
                    break  # Only one deployment per project

        except Exception as e:
            logger.warning(f"Error processing project {project_path}: {e}")
            continue

    # Add children to root node if it exists
    if root_node:
        root_node.children = children

    # Build statistics
    statistics = {
        "total_deployments": total_deployments,
        "modified_count": modified_count,
        "unmodified_count": unmodified_count,
        "orphaned_count": 0,  # No orphaned nodes in current implementation
    }

    return VersionGraphResponse(
        artifact_name=artifact_name,
        artifact_type=artifact_type.value,
        root=root_node,
        statistics=statistics,
        last_updated=datetime.utcnow(),
    )


def artifact_to_response(
    artifact,
    drift_status: Optional[str] = None,
    has_local_modifications: Optional[bool] = None,
) -> ArtifactResponse:
    """Convert Artifact model to API response schema.

    Args:
        artifact: Artifact instance
        drift_status: Optional drift status ("none", "modified", "deleted", "added")
        has_local_modifications: Optional flag indicating local modifications

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
            has_local_modifications=has_local_modifications or False,
            drift_status=drift_status or "none",
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
    sync_mgr: SyncManagerDep,
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
    check_drift: bool = Query(
        default=False,
        description="Check for local modifications and drift status (may impact performance)",
    ),
    project_path: Optional[str] = Query(
        default=None,
        description="Project path for drift detection (required if check_drift=true)",
    ),
) -> ArtifactListResponse:
    """List all artifacts with filters and pagination.

    Args:
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        sync_mgr: Sync manager dependency
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional type filter
        collection: Optional collection filter
        tags: Optional tag filter (comma-separated)
        check_drift: Whether to check for drift and local modifications
        project_path: Project path for drift detection

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

        # Check drift if requested
        drift_map = {}
        if check_drift:
            # Validate project_path is provided
            if not project_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="project_path is required when check_drift=true",
                )

            project_path_obj = Path(project_path)
            if not project_path_obj.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project path does not exist: {project_path}",
                )

            try:
                # Check drift for the project
                drift_results = sync_mgr.check_drift(
                    project_path=project_path_obj,
                    collection_name=collection,
                )

                # Build drift map: artifact_key -> (drift_status, has_modifications)
                for drift in drift_results:
                    artifact_key = f"{drift.artifact_type}:{drift.artifact_name}"
                    has_modifications = drift.drift_type in ("modified", "added")
                    drift_map[artifact_key] = (drift.drift_type, has_modifications)

                logger.debug(f"Detected drift for {len(drift_results)} artifacts")
            except Exception as e:
                logger.warning(f"Failed to check drift: {e}")
                # Continue without drift info rather than failing the request

        # Convert to response format
        items: List[ArtifactResponse] = []
        for artifact in page_artifacts:
            artifact_key = f"{artifact.type.value}:{artifact.name}"
            drift_status = None
            has_modifications = None

            if artifact_key in drift_map:
                drift_status, has_modifications = drift_map[artifact_key]

            items.append(
                artifact_to_response(
                    artifact,
                    drift_status=drift_status,
                    has_local_modifications=has_modifications,
                )
            )

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
    include_deployments: bool = Query(
        default=False,
        description="Include deployment statistics across all projects",
    ),
) -> ArtifactResponse:
    """Get details for a specific artifact.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection filter
        include_deployments: Whether to include deployment statistics

    Returns:
        Artifact details with optional deployment statistics

    Raises:
        HTTPException: If artifact not found or on error

    Example:
        GET /api/v1/artifacts/skill:pdf-processor?include_deployments=true

        Returns artifact details including deployment_stats field with
        information about all projects where this artifact is deployed.
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

        # Build base response
        response = artifact_to_response(artifact)

        # Add deployment statistics if requested
        if include_deployments:
            try:
                deployment_stats = await build_deployment_statistics(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                )
                response.deployment_stats = deployment_stats
            except Exception as e:
                logger.warning(
                    f"Failed to build deployment statistics for {artifact_id}: {e}"
                )
                # Continue without deployment stats rather than failing

        return response

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
            # Ensure artifact has metadata object
            if artifact.metadata is None:
                from skillmeat.core.artifact import ArtifactMetadata
                artifact.metadata = ArtifactMetadata()

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
    "/{artifact_id}/sync",
    response_model=ArtifactSyncResponse,
    summary="Sync artifact from project to collection",
    description="Pull changes from project back to collection, with conflict resolution",
    responses={
        200: {"description": "Artifact synced successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def sync_artifact(
    artifact_id: str,
    request: ArtifactSyncRequest,
    sync_mgr: SyncManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> ArtifactSyncResponse:
    """Sync artifact from project to collection.

    Pulls changes from a deployed artifact in a project back to the collection.
    This is useful for capturing local modifications made to deployed artifacts.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        request: Sync request with project_path, force flag, and strategy
        sync_mgr: Sync manager dependency
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection name

    Returns:
        Sync result with conflicts and updated version info

    Raises:
        HTTPException: If artifact not found, validation fails, or on error
    """
    try:
        logger.info(
            f"Syncing artifact: {artifact_id} from {request.project_path or 'upstream'} (collection={collection})"
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

        # Handle upstream sync (no project_path provided)
        if not request.project_path:
            logger.info(f"Syncing {artifact_id} from upstream source")
            # TODO: Implement upstream sync - fetch from GitHub and update collection
            # For now, return a placeholder response
            return ArtifactSyncResponse(
                success=False,
                message="Upstream sync not yet implemented. Use update endpoint or provide project_path for reverse sync.",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                conflicts=None,
                updated_version=None,
                synced_files_count=None,
            )

        # Validate project path
        project_path = Path(request.project_path)
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project path does not exist: {request.project_path}",
            )

        # Validate strategy
        valid_strategies = {"theirs", "ours", "manual"}
        if request.strategy not in valid_strategies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy '{request.strategy}'. Must be one of: {', '.join(valid_strategies)}",
            )

        # Map request strategy to SyncManager strategy
        # "theirs" = take upstream (collection) -> "overwrite"
        # "ours" = keep local (project) -> this means pull from project, so "overwrite"
        # "manual" = preserve conflicts -> "merge"
        strategy_map = {
            "theirs": "overwrite",  # Pull from project and overwrite collection
            "ours": "overwrite",     # Same as theirs in pull context
            "manual": "merge",       # Use merge with conflict markers
        }
        sync_strategy = strategy_map[request.strategy]

        # Check for deployment metadata
        deployment_metadata = sync_mgr._load_deployment_metadata(project_path)
        if not deployment_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployment metadata found at {request.project_path}. Deploy artifacts first.",
            )

        # Get collection name from metadata if not provided
        if not collection:
            collection_name = deployment_metadata.collection
        else:
            collection_name = collection

        # Verify collection exists
        if collection_name not in collection_mgr.list_collections():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Load collection and verify artifact exists
        coll = collection_mgr.load_collection(collection_name)
        artifact = coll.find_artifact(artifact_name, artifact_type)

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in collection '{collection_name}'",
            )

        # Check if artifact is deployed in project
        deployed_artifact = None
        for deployed in deployment_metadata.artifacts:
            if deployed.name == artifact_name and deployed.artifact_type == artifact_type.value:
                deployed_artifact = deployed
                break

        if not deployed_artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in project deployment metadata",
            )

        # Perform sync using sync_from_project
        try:
            sync_result = sync_mgr.sync_from_project(
                project_path=project_path,
                artifact_names=[artifact_name],
                strategy=sync_strategy,
                dry_run=False,
                interactive=False,
            )

            # Extract conflicts if any
            conflicts_list = None
            if sync_result.conflicts:
                conflicts_list = [
                    ConflictInfo(
                        file_path=conflict_file,
                        conflict_type="modified"
                    )
                    for conflict_result in sync_result.conflicts
                    for conflict_file in (conflict_result.conflict_files if hasattr(conflict_result, 'conflict_files') else [])
                ]

            # Determine success based on sync result status
            success = sync_result.status in ("success", "partial")

            # Get updated version from artifact if available
            updated_version = None
            if success:
                # Reload artifact to get updated version
                updated_coll = collection_mgr.load_collection(collection_name)
                updated_artifact = updated_coll.find_artifact(artifact_name, artifact_type)
                if updated_artifact and updated_artifact.metadata:
                    updated_version = updated_artifact.metadata.version

            # Count synced files (approximate based on artifact path)
            synced_files_count = None
            if success and artifact_name in sync_result.artifacts_synced:
                collection_path = collection_mgr.config.get_collection_path(collection_name)
                artifact_path = collection_path / artifact.path
                if artifact_path.exists():
                    synced_files_count = len(list(artifact_path.rglob("*")))

            logger.info(
                f"Artifact '{artifact_name}' sync completed: status={sync_result.status}, "
                f"conflicts={len(conflicts_list) if conflicts_list else 0}"
            )

            return ArtifactSyncResponse(
                success=success,
                message=sync_result.message,
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                conflicts=conflicts_list if conflicts_list else None,
                updated_version=updated_version,
                synced_files_count=synced_files_count,
            )

        except ValueError as e:
            # Business logic error (e.g., sync preconditions not met)
            logger.warning(f"Sync failed for '{artifact_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync artifact: {str(e)}",
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
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    project_path: str = Body(..., embed=True, description="Project path"),
    _collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> ArtifactDeployResponse:
    """Remove deployed artifact from project.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        project_path: Project directory path
        _collection: Optional collection name (unused, reserved for future use)

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


@router.get(
    "/{artifact_id}/version-graph",
    response_model=VersionGraphResponse,
    summary="Get artifact version graph",
    description="Build and return version graph showing deployment hierarchy across all projects",
    responses={
        200: {
            "description": "Successfully retrieved version graph",
            "headers": {
                "Cache-Control": {
                    "description": "Caching directives",
                    "schema": {"type": "string", "example": "max-age=300"},
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_version_graph(
    artifact_id: str,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Filter to specific collection",
    ),
) -> VersionGraphResponse:
    """Get complete version graph for an artifact.

    Returns a hierarchical tree structure showing:
    - Collection version as root node
    - Project deployments as child nodes
    - Content hashes and modification status at each node
    - Aggregated statistics

    The graph enables visualization of how an artifact has been
    deployed across projects and which deployments have local modifications.

    Results are cached for 5 minutes (Cache-Control header).

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        VersionGraphResponse with complete hierarchy

    Raises:
        HTTPException: If artifact not found or on error

    Example:
        GET /api/v1/artifacts/skill:pdf-processor/version-graph?collection=default

        Returns:
        {
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "root": {
                "id": "collection:default:abc123",
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "version_info": {...},
                "children": [
                    {
                        "id": "project:/Users/me/project1",
                        "version_info": {...},
                        "children": []
                    }
                ]
            },
            "statistics": {
                "total_deployments": 2,
                "modified_count": 1,
                "unmodified_count": 1,
                "orphaned_count": 0
            },
            "last_updated": "2025-11-20T16:00:00Z"
        }
    """
    try:
        logger.info(
            f"Building version graph for artifact: {artifact_id} (collection={collection})"
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

        # Build version graph
        version_graph = await build_version_graph(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection,
            collection_mgr=collection_mgr,
        )

        # Check if we found the artifact anywhere
        if version_graph.root is None and version_graph.statistics["total_deployments"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in any collection or project",
            )

        logger.info(
            f"Version graph built: {version_graph.statistics['total_deployments']} deployments, "
            f"{version_graph.statistics['modified_count']} modified"
        )

        # Note: FastAPI Response with Cache-Control header would be set here
        # For now, the response model handles the data structure
        # To add caching headers, we would need to use Response directly

        return version_graph

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error building version graph for '{artifact_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build version graph: {str(e)}",
        )


@router.get(
    "/{artifact_id}/versions",
    response_model=ArtifactVersionsResponse,
    summary="Get artifact versions across tiers",
    responses={
        200: {"description": "Versions returned"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
    },
)
async def get_artifact_versions(
    artifact_id: str,
    collection: Optional[str] = Query(default=None, description="Collection override"),
    project_path: Optional[str] = Query(
        default=None, description="Project path for project tier metadata"
    ),
    sync_mgr: SyncManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep = None,
) -> ArtifactVersionsResponse:
    """Return upstream/collection/project hashes and metadata for an artifact."""
    try:
        artifact_type_str, artifact_name = artifact_id.split(":", 1)
        artifact_type = ArtifactType(artifact_type_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid artifact ID format. Expected 'type:name'",
        )

    coll_path, proj_path = _get_artifact_paths(
        artifact_type, artifact_name, collection_mgr, collection, project_path, sync_mgr
    )
    collection_hash = compute_content_hash(coll_path)
    coll_ts = datetime.fromtimestamp(coll_path.stat().st_mtime, tz=datetime.now().astimezone().tzinfo)

    project_hash = None
    project_ts = None
    sync_status = None
    if project_path and proj_path:
        project_hash = compute_content_hash(proj_path)
        project_ts = datetime.fromtimestamp(proj_path.stat().st_mtime, tz=datetime.now().astimezone().tzinfo)
        # derive sync status from drift detection if available
        try:
            drift_results = sync_mgr.check_drift(Path(project_path), collection_name=collection)
            match = next((d for d in drift_results if d.artifact_name == artifact_name), None)
            if match and hasattr(match, "sync_status"):
                sync_status = match.sync_status.value if hasattr(match.sync_status, "value") else match.sync_status
        except Exception:
            sync_status = None

    return ArtifactVersionsResponse(
        artifact_name=artifact_name,
        artifact_type=artifact_type.value,
        upstream=ArtifactTierVersion(tier="upstream", hash=None, timestamp=None, source=None, sync_status=None),
        collection=ArtifactTierVersion(
            tier="collection",
            hash=collection_hash,
            timestamp=coll_ts,
            source=str(coll_path),
            sync_status="synced" if sync_status is None else sync_status,
        ),
        project=ArtifactTierVersion(
            tier="project",
            hash=project_hash,
            timestamp=project_ts,
            source=str(proj_path) if proj_path else None,
            sync_status=sync_status,
        ),
    )


@router.get(
    "/{artifact_id}/diff",
    response_model=ArtifactDiffResponse,
    summary="Get diff between tiers for an artifact",
    responses={
        200: {"description": "Diff returned"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
    },
)
async def diff_artifact_tiers(
    artifact_id: str,
    lhs: str = Query(default="collection", description="Left tier (collection|project)"),
    rhs: str = Query(default="project", description="Right tier (collection|project)"),
    collection: Optional[str] = Query(default=None, description="Collection override"),
    project_path: Optional[str] = Query(default=None, description="Project path for project tier"),
    sync_mgr: SyncManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep = None,
) -> ArtifactDiffResponse:
    """Return diffs between two tiers for an artifact."""
    try:
        artifact_type_str, artifact_name = artifact_id.split(":", 1)
        artifact_type = ArtifactType(artifact_type_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid artifact ID format. Expected 'type:name'",
        )

    if "project" in {lhs, rhs} and not project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_path is required when comparing with project",
        )

    coll_path, proj_path = _get_artifact_paths(
        artifact_type, artifact_name, collection_mgr, collection, project_path, sync_mgr
    )

    lhs_path = coll_path if lhs == "collection" else proj_path
    rhs_path = proj_path if rhs == "project" else coll_path
    if lhs_path is None or rhs_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested tier path not found",
        )

    engine = DiffEngine()
    files: List[ArtifactFileDiff] = []
    truncated = False
    download_path = None

    if lhs_path.is_dir() and rhs_path.is_dir():
        diff_result = engine.diff_directories(lhs_path, rhs_path)
        for path in diff_result.files_added:
            files.append(ArtifactFileDiff(path=path, status="added", lines_added=0, lines_removed=0))
        for path in diff_result.files_removed:
            files.append(ArtifactFileDiff(path=path, status="removed", lines_added=0, lines_removed=0))
        for fd in diff_result.files_modified:
            files.append(
                ArtifactFileDiff(
                    path=fd.path,
                    status=fd.status,
                    lines_added=fd.lines_added,
                    lines_removed=fd.lines_removed,
                    unified_diff=fd.unified_diff,
                )
            )
        files_added = len(diff_result.files_added)
        files_removed = len(diff_result.files_removed)
        files_modified = len(diff_result.files_modified)
        total_lines_added = diff_result.total_lines_added
        total_lines_removed = diff_result.total_lines_removed
    else:
        fd = engine.diff_files(lhs_path, rhs_path)
        files.append(
            ArtifactFileDiff(
                path=fd.path,
                status=fd.status,
                lines_added=fd.lines_added,
                lines_removed=fd.lines_removed,
                unified_diff=fd.unified_diff,
            )
        )
        files_added = 0
        files_removed = 0
        files_modified = 1 if fd.status != "unchanged" else 0
        total_lines_added = fd.lines_added
        total_lines_removed = fd.lines_removed

    diff_size = sum(len(f.unified_diff or "") for f in files)
    if diff_size > 1_000_000:
        truncated = True
        combined = "\n\n".join([f.unified_diff for f in files if f.unified_diff])
        tmp_dir = tempfile.mkdtemp(prefix="skillmeat-diff-")
        diff_file = Path(tmp_dir) / f"{artifact_name}-{lhs}-vs-{rhs}.diff"
        diff_file.write_text(combined or "", encoding="utf-8")
        download_path = str(diff_file)
        for f in files:
            f.unified_diff = None

    return ArtifactDiffResponse(
        artifact_name=artifact_name,
        artifact_type=artifact_type.value,
        lhs=lhs,
        rhs=rhs,
        files_added=files_added,
        files_removed=files_removed,
        files_modified=files_modified,
        total_lines_added=total_lines_added,
        total_lines_removed=total_lines_removed,
        truncated=truncated,
        download_path=download_path,
        files=files,
    )
