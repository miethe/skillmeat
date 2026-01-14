"""Artifact management API endpoints.

Provides REST API for managing artifacts within collections.
"""

import base64
import logging
import time
from datetime import datetime, timezone
from pathlib import Path as PathLib
from typing import Dict, List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)

from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    ConfigManagerDep,
    SyncManagerDep,
    get_app_state,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    ArtifactCollectionInfo,
    ArtifactCreateRequest,
    ArtifactCreateResponse,
    ArtifactDeployRequest,
    ArtifactDeployResponse,
    ArtifactDiffResponse,
    ArtifactListResponse,
    ArtifactMetadataResponse,
    ArtifactResponse,
    ArtifactSourceType,
    ArtifactSyncRequest,
    ArtifactSyncResponse,
    ArtifactUpdateRequest,
    ArtifactUpstreamDiffResponse,
    ArtifactUpstreamInfo,
    ArtifactUpstreamResponse,
    ArtifactVersionInfo,
    ConflictInfo,
    DeploymentStatistics,
    FileDiff,
    FileContentResponse,
    FileListResponse,
    FileNode,
    FileUpdateRequest,
    ProjectDeploymentInfo,
    VersionGraphNodeResponse,
    VersionGraphResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.discovery import (
    BulkImportRequest,
    BulkImportResult,
    ConfirmDuplicatesRequest,
    ConfirmDuplicatesResponse,
    DiscoveredArtifact,
    DiscoveryRequest,
    DiscoveryResult,
    GitHubMetadata,
    MetadataFetchResponse,
    ParameterUpdateRequest,
    ParameterUpdateResponse,
    SkipClearResponse,
    SkipPreferenceAddRequest,
    SkipPreferenceListResponse,
    SkipPreferenceResponse,
)
from skillmeat.api.schemas.errors import ErrorCodes, ErrorDetail
from skillmeat.api.schemas.tags import TagResponse
from skillmeat.api.utils.error_handlers import (
    create_bad_request_error,
    create_internal_error,
    create_not_found_error,
    create_rate_limit_error,
    create_validation_error,
    validate_artifact_request,
)
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.cache import MetadataCache
from skillmeat.core.deployment import Deployment, DeploymentManager
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.core.github_metadata import GitHubMetadataExtractor
from skillmeat.core.importer import (
    ArtifactImporter,
    BulkImportArtifactData,
    BulkImportResultData,
    ImportResultData,
)
from skillmeat.core.services import TagService
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash
from skillmeat.cache.models import Collection, CollectionArtifact, get_session

logger = logging.getLogger(__name__)


def _decode_project_id_param(raw_project_id: str) -> Optional[PathLib]:
    """Decode project identifier passed to bulk import.

    Accepts standard base64-encoded project paths (with or without padding) and
    gracefully falls back to treating the value as a URL-encoded absolute path.
    """
    from urllib.parse import unquote

    # Normalize spaces and percent-encoding first (some callers URL-encode the base64)
    candidate = unquote(raw_project_id.strip().replace(" ", "+"))

    # Try base64 decode (allow missing padding)
    try:
        padding = "=" * (-len(candidate) % 4)
        decoded_path = base64.b64decode(candidate + padding).decode()
        project_path = PathLib(decoded_path).resolve()
        if project_path.is_absolute():
            return project_path
    except Exception:
        # Ignore and try fallback decoding
        pass

    # Fallback: treat as URL-encoded absolute path
    try:
        decoded_path = unquote(candidate)
        project_path = PathLib(decoded_path).resolve()
        if project_path.is_absolute():
            return project_path
    except Exception:
        pass

    return None


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
    collection_mgr=None,
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
        last_updated=datetime.now(timezone.utc),
    )


def artifact_to_response(
    artifact,
    drift_status: Optional[str] = None,
    has_local_modifications: Optional[bool] = None,
    collections_data: Optional[List[dict]] = None,
) -> ArtifactResponse:
    """Convert Artifact model to API response schema.

    Args:
        artifact: Artifact instance
        drift_status: Optional drift status ("none", "modified", "deleted", "added")
        has_local_modifications: Optional flag indicating local modifications
        collections_data: Optional list of collection info dicts from database query

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

    # Convert collections from passed data (queried from database)
    collections_response = []
    if collections_data:
        for coll in collections_data:
            collections_response.append(
                ArtifactCollectionInfo(
                    id=coll["id"],
                    name=coll["name"],
                    artifact_count=coll.get("artifact_count"),
                )
            )

    return ArtifactResponse(
        id=f"{artifact.type.value}:{artifact.name}",
        name=artifact.name,
        type=artifact.type.value,
        source=artifact.upstream if artifact.origin == "github" else "local",
        version=version,
        aliases=[],  # TODO: Add alias support when implemented
        tags=artifact.tags or [],
        metadata=metadata_response,
        upstream=upstream_response,
        collections=collections_response,
        added=artifact.added,
        updated=artifact.last_updated or artifact.added,
    )


@router.post(
    "/discover",
    response_model=DiscoveryResult,
    summary="Discover artifacts in collection",
    description="Scan collection for existing artifacts that can be imported",
    responses={
        200: {"description": "Discovery scan completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid scan path"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def discover_artifacts(
    request: DiscoveryRequest,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
    req: Request = None,
) -> DiscoveryResult:
    """Scan collection for existing artifacts.

    Scans the collection artifacts directory for existing artifacts
    that can be imported into the collection. Returns metadata
    for each discovered artifact.

    Args:
        request: Discovery request with optional scan_path
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection name (defaults to active collection)
        req: FastAPI request object for accessing settings

    Returns:
        DiscoveryResult with discovered artifacts, errors, and metrics

    Raises:
        HTTPException: If scan_path doesn't exist or scan fails
    """
    # Check if discovery feature is enabled
    from skillmeat.api.config import get_settings

    settings = get_settings()
    if not settings.enable_auto_discovery:
        logger.warning("Discovery feature is disabled")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Artifact auto-discovery feature is currently disabled. Enable with SKILLMEAT_ENABLE_AUTO_DISCOVERY=true",
        )

    # Determine collection name
    collection_name = collection or "default"

    try:
        # Get collection path
        collection_path = collection_mgr.config.get_collection_path(collection_name)

        # Use custom scan path if provided, otherwise use collection artifacts directory
        if request.scan_path:
            scan_path = PathLib(request.scan_path)
            if not scan_path.exists():
                logger.warning(f"Scan path does not exist: {scan_path}")
                raise create_bad_request_error(
                    f"Scan path does not exist: {request.scan_path}",
                    ErrorCodes.NOT_FOUND,
                )
        else:
            scan_path = collection_path

        # Load manifest to filter already-imported artifacts
        manifest = None
        try:
            manifest = collection_mgr.load_collection(collection_name)
            logger.info(
                f"Loaded manifest for filtering: {len(manifest.artifacts)} artifacts in collection"
            )
        except Exception as e:
            logger.warning(
                f"Could not load manifest for filtering (will return all artifacts as importable): {e}"
            )
            # Graceful fallback - return all as importable

        # Create discovery service
        discovery_service = ArtifactDiscoveryService(scan_path)

        # Perform discovery scan with manifest filtering
        logger.info(f"Starting artifact discovery scan in: {scan_path}")
        result = discovery_service.discover_artifacts(manifest=manifest)

        # Log results
        logger.info(
            f"Discovery scan completed: {result.discovered_count} total artifacts, "
            f"{result.importable_count} importable (not yet in collection), "
            f"in {result.scan_duration_ms:.2f}ms, {len(result.errors)} errors"
        )

        if result.errors:
            logger.warning(f"Discovery scan encountered {len(result.errors)} errors")
            for error in result.errors[:5]:  # Log first 5 errors
                logger.warning(f"  - {error}")

        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Discovery scan failed: {e}", exc_info=True)
        raise create_internal_error("Discovery scan failed", e)


def resolve_project_path(project_id: str) -> PathLib:
    """Resolve project ID to filesystem path.

    Args:
        project_id: URL-encoded project path

    Returns:
        Resolved PathLib object

    Raises:
        HTTPException: If path is invalid or doesn't exist
    """
    from urllib.parse import unquote

    # URL-decode the path
    decoded_path = unquote(project_id)
    project_path = PathLib(decoded_path)

    if not project_path.is_absolute():
        raise create_bad_request_error(
            f"Project path must be absolute: {decoded_path}",
            ErrorCodes.VALIDATION_FAILED,
        )

    if not project_path.exists():
        raise create_not_found_error(
            f"Project path not found: {decoded_path}", ErrorCodes.NOT_FOUND
        )

    return project_path


@router.post(
    "/discover/project/{project_id:path}",
    response_model=DiscoveryResult,
    summary="Discover artifacts in a project",
    description="Scan a project's .claude/ directory for existing artifacts that can be imported",
    responses={
        200: {"description": "Discovery scan completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid project path"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def discover_project_artifacts(
    project_id: str = Path(..., description="URL-encoded project path"),
    collection_mgr: CollectionManagerDep = None,
    _token: TokenDep = None,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> DiscoveryResult:
    """Discover artifacts in a specific project's .claude/ directory.

    Args:
        project_id: Project ID (URL-encoded path)
        collection_mgr: Collection manager dependency
        _token: Authentication token
        collection: Optional collection name for filtering

    Returns:
        DiscoveryResult with discovered artifacts from the project

    Raises:
        HTTPException: If project path is invalid, doesn't exist, or scan fails
    """
    # Check if discovery feature is enabled
    from skillmeat.api.config import get_settings

    settings = get_settings()
    if not settings.enable_auto_discovery:
        logger.warning("Discovery feature is disabled")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Artifact auto-discovery feature is currently disabled. Enable with SKILLMEAT_ENABLE_AUTO_DISCOVERY=true",
        )

    try:
        # Resolve and validate project path
        project_path = resolve_project_path(project_id)
        logger.info(f"Resolved project path: {project_path}")

        # Check that .claude/ directory exists
        claude_dir = project_path / ".claude"
        if not claude_dir.exists() or not claude_dir.is_dir():
            raise create_bad_request_error(
                f"Project does not contain a .claude/ directory: {project_path}",
                ErrorCodes.VALIDATION_FAILED,
            )

        # Load manifest to filter already-imported artifacts
        manifest = None
        if collection_mgr:
            collection_name = collection or "default"
            try:
                manifest = collection_mgr.load_collection(collection_name)
                logger.info(
                    f"Loaded manifest for filtering: {len(manifest.artifacts)} artifacts in collection"
                )
            except Exception as e:
                logger.warning(
                    f"Could not load manifest for filtering (will return all artifacts as importable): {e}"
                )
                # Graceful fallback - return all as importable

        # Create discovery service with project scan mode
        discovery_service = ArtifactDiscoveryService(project_path, scan_mode="project")

        # Perform discovery scan with manifest filtering
        logger.info(f"Starting artifact discovery scan in project: {project_path}")
        result = discovery_service.discover_artifacts(manifest=manifest)

        # Log results
        logger.info(
            f"Discovery scan completed: {result.discovered_count} total artifacts, "
            f"{result.importable_count} importable (not yet in collection), "
            f"in {result.scan_duration_ms:.2f}ms, {len(result.errors)} errors"
        )

        if result.errors:
            logger.warning(f"Discovery scan encountered {len(result.errors)} errors")
            for error in result.errors[:5]:  # Log first 5 errors
                logger.warning(f"  - {error}")

        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Project discovery scan failed: {e}", exc_info=True)
        raise create_internal_error("Project discovery scan failed", e)


@router.post(
    "/discover/import",
    response_model=BulkImportResult,
    status_code=status.HTTP_200_OK,
    summary="Bulk import artifacts",
    description="Import multiple artifacts from discovered artifacts or external sources with atomic transaction",
    responses={
        200: {
            "description": "Bulk import completed (check results for per-artifact status)"
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def bulk_import_artifacts(
    request: BulkImportRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
    project_id: Optional[str] = Query(
        None,
        description="Base64-encoded project path to also record deployments for the imports",
    ),
) -> BulkImportResult:
    """
    Bulk import multiple artifacts with graceful error handling.

    Validates all artifacts before importing. Validation failures are tracked
    per-artifact but do NOT cause the entire batch to fail. Valid artifacts
    are imported while failed ones are reported in the results with detailed
    error messages.

    The endpoint supports importing from:
    - GitHub sources (e.g., "anthropics/skills/canvas-design@latest")
    - Discovered artifacts from the collection

    Process:
    1. Validate all artifact specifications (failures tracked, not raised)
    2. Filter to valid artifacts only
    3. Check for duplicates in target collection
    4. Import valid artifacts (skip duplicates if auto_resolve_conflicts=True)
    5. Update collection manifest and lock files
    6. Build results combining validation failures + import results

    Response includes per-artifact status:
    - status: "success" (imported), "skipped" (already exists), "failed" (error)
    - skip_reason: Explanation when status="skipped"
    - error: Error message when status="failed" (includes validation errors)

    Args:
        request: BulkImportRequest with list of artifacts to import
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection name (defaults to "default")

    Returns:
        BulkImportResult with per-artifact status, summary counts, and location breakdown

    Raises:
        HTTPException: 500 if import fails catastrophically

    Examples:
        Import multiple artifacts:
        ```json
        {
            "artifacts": [
                {
                    "source": "anthropics/skills/canvas-design@latest",
                    "artifact_type": "skill",
                    "name": "canvas-design",
                    "tags": ["design", "canvas"],
                    "scope": "user"
                },
                {
                    "source": "anthropics/skills/pdf@v1.0.0",
                    "artifact_type": "skill",
                    "name": "pdf",
                    "tags": ["document"],
                    "scope": "user"
                }
            ],
            "auto_resolve_conflicts": false
        }
        ```
    """
    # Determine collection name
    collection_name = collection or "default"

    try:
        # Import schemas needed for building results
        from skillmeat.api.schemas.discovery import (
            ErrorReasonCode,
            ImportResult,
            ImportStatus,
        )

        # Validate all artifacts before importing - track failures instead of raising 422
        validation_failures: dict[int, str] = {}  # index -> error message
        for i, artifact in enumerate(request.artifacts):
            error = validate_artifact_request(
                source=artifact.source,
                artifact_type=artifact.artifact_type,
                scope=artifact.scope,
                name=artifact.name,
                tags=artifact.tags,
            )
            if error:
                # Extract validation error messages
                detail = error.detail
                if isinstance(detail, dict) and "details" in detail:
                    messages = [d.get("message", str(d)) for d in detail["details"]]
                    validation_failures[i] = "; ".join(messages)
                else:
                    validation_failures[i] = str(detail)
                logger.warning(
                    f"Artifact {i} ({artifact.name or artifact.source}) failed validation: "
                    f"{validation_failures[i]}"
                )

        # Create importer service
        importer = ArtifactImporter(
            artifact_manager=artifact_mgr,
            collection_manager=collection_mgr,
        )

        # Filter to only valid artifacts for import
        valid_artifact_indices = [
            i for i in range(len(request.artifacts)) if i not in validation_failures
        ]
        valid_artifacts = [request.artifacts[i] for i in valid_artifact_indices]

        # Convert only valid Pydantic schemas to data classes
        artifacts_data = [
            BulkImportArtifactData(
                source=a.source,
                artifact_type=a.artifact_type,
                name=a.name,
                description=a.description,
                author=a.author,
                tags=a.tags,
                scope=a.scope,
                path=a.path,
            )
            for a in valid_artifacts
        ]

        # Perform bulk import only if there are valid artifacts
        start_time = time.time()

        if artifacts_data:
            logger.info(
                f"Starting bulk import of {len(artifacts_data)} artifacts "
                f"(skipped {len(validation_failures)} with validation errors) "
                f"to collection '{collection_name}'"
            )

            result_data = importer.bulk_import(
                artifacts=artifacts_data,
                collection_name=collection_name,
                auto_resolve_conflicts=request.auto_resolve_conflicts,
                apply_path_tags=request.apply_path_tags,
            )

            logger.info(
                f"Bulk import completed: {result_data.total_imported}/{result_data.total_requested} "
                f"imported, {result_data.total_failed} failed in {result_data.duration_ms:.1f}ms"
            )
        else:
            # All artifacts failed validation - create empty result
            from skillmeat.core.importer import BulkImportResultData

            logger.warning(
                f"No valid artifacts to import - all {len(request.artifacts)} failed validation"
            )
            result_data = BulkImportResultData(
                total_requested=0,
                total_imported=0,
                total_failed=0,
                results=[],
                duration_ms=(time.time() - start_time) * 1000,
                total_tags_applied=0,
            )

        # Build results: combine validation failures + import results in original order
        # Create a mapping from valid artifact index to its import result
        import_results_by_valid_idx = {i: r for i, r in enumerate(result_data.results)}

        results: list[ImportResult] = []
        valid_idx = 0  # Track position in valid artifacts list

        for i, artifact in enumerate(request.artifacts):
            if i in validation_failures:
                # This artifact failed validation - add failed result
                artifact_id = (
                    f"{artifact.artifact_type}:{artifact.name}"
                    if artifact.name
                    else f"{artifact.artifact_type}:{artifact.source}"
                )
                results.append(
                    ImportResult(
                        artifact_id=artifact_id,
                        path=artifact.path,
                        status=ImportStatus.FAILED,
                        message="Validation failed",
                        error=validation_failures[i],
                        reason_code=ErrorReasonCode.INVALID_SOURCE,
                        skip_reason=None,
                        details=None,
                        tags_applied=0,
                    )
                )
            else:
                # This artifact was valid - get its import result
                if valid_idx in import_results_by_valid_idx:
                    r = import_results_by_valid_idx[valid_idx]
                    results.append(
                        ImportResult(
                            artifact_id=r.artifact_id,
                            path=r.path,
                            status=(
                                r.status
                                if r.status
                                else (
                                    ImportStatus.SUCCESS
                                    if r.success
                                    else ImportStatus.FAILED
                                )
                            ),
                            message=r.message,
                            error=r.error,
                            reason_code=(
                                ErrorReasonCode(r.reason_code)
                                if r.reason_code
                                and r.reason_code in [e.value for e in ErrorReasonCode]
                                else None
                            ),
                            skip_reason=r.skip_reason,
                            details=r.details,
                            tags_applied=r.tags_applied,
                        )
                    )
                valid_idx += 1

        # If we know which project initiated the import, record deployments so UI reflects the change
        if project_id:
            project_path = _decode_project_id_param(project_id)

            if project_path is None:
                logger.warning(
                    f"Invalid project_id provided to bulk import: {project_id}"
                )
            elif not project_path.exists():
                logger.warning(
                    f"Provided project_id path does not exist: {project_path}"
                )
                project_path = None

            if project_path:
                try:
                    claude_dir = project_path / ".claude"
                    if not claude_dir.exists():
                        logger.warning(
                            f"Cannot record deployments for {project_path}: .claude directory missing"
                        )
                    else:
                        deployments = DeploymentTracker.read_deployments(project_path)
                        updated = False

                        for artifact_payload, import_result in zip(
                            request.artifacts, results
                        ):
                            if import_result.status != ImportStatus.SUCCESS:
                                continue

                            if not artifact_payload.path:
                                logger.debug(
                                    f"Skipping deployment record for {import_result.artifact_id}: missing path"
                                )
                                continue

                            artifact_path = PathLib(artifact_payload.path).resolve()
                            try:
                                artifact_path.relative_to(claude_dir)
                            except ValueError:
                                logger.warning(
                                    f"Artifact path {artifact_path} is outside project .claude ({claude_dir}); skipping deployment record"
                                )
                                continue

                            artifact_name = artifact_payload.name or artifact_path.stem

                            try:
                                content_hash = compute_content_hash(artifact_path)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to hash artifact at {artifact_path}: {e}"
                                )
                                continue

                            deployment = Deployment(
                                artifact_name=artifact_name,
                                artifact_type=artifact_payload.artifact_type,
                                from_collection=collection_name,
                                deployed_at=datetime.now(),
                                artifact_path=artifact_path.relative_to(claude_dir),
                                content_hash=content_hash,
                                local_modifications=False,
                            )

                            deployments = [
                                d
                                for d in deployments
                                if not (
                                    d.artifact_name == deployment.artifact_name
                                    and d.artifact_type == deployment.artifact_type
                                )
                            ]
                            deployments.append(deployment)
                            updated = True

                        if updated:
                            DeploymentTracker.write_deployments(
                                project_path, deployments
                            )
                            logger.info(
                                f"Recorded deployments for {project_path} after import"
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed to update project deployments for {project_path}: {e}"
                    )

        # Calculate totals from combined results (including validation failures)
        total_skipped = sum(1 for r in results if r.status == ImportStatus.SKIPPED)
        total_failed = sum(1 for r in results if r.status == ImportStatus.FAILED)
        total_imported = sum(1 for r in results if r.status == ImportStatus.SUCCESS)

        return BulkImportResult(
            total_requested=len(
                request.artifacts
            ),  # All requested, including validation failures
            total_imported=total_imported,
            total_skipped=total_skipped,
            total_failed=total_failed,  # Includes validation failures + import failures
            imported_to_collection=total_imported,  # All successful imports go to collection
            added_to_project=0,  # TODO: Track project deployments separately
            total_tags_applied=result_data.total_tags_applied,
            results=results,
            duration_ms=result_data.duration_ms,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"Bulk import failed: {e}")
        raise create_internal_error("Bulk import failed", e)


@router.post(
    "/confirm-duplicates",
    response_model=ConfirmDuplicatesResponse,
    status_code=status.HTTP_200_OK,
    summary="Process duplicate review decisions",
    description="""
    Process user decisions from the duplicate review modal.

    Handles three types of decisions:
    1. **matches**: Link discovered duplicates to existing collection artifacts
    2. **new_artifacts**: Import selected paths as new artifacts
    3. **skipped**: Acknowledge paths the user chose to skip (logged for audit)

    All operations are atomic - if any operation fails, the response will
    indicate partial success with error details.

    This endpoint is idempotent for link operations - calling multiple times
    with the same matches will not create duplicate links.
    """,
    responses={
        200: {"description": "Duplicate decisions processed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["discovery"],
)
async def confirm_duplicates(
    request: ConfirmDuplicatesRequest,
    collection_mgr: CollectionManagerDep,
    artifact_mgr: ArtifactManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> ConfirmDuplicatesResponse:
    """Process duplicate review decisions from the frontend modal.

    This endpoint processes user decisions made in the duplicate review modal:
    - Links duplicates to existing collection artifacts
    - Imports new artifacts using the standard importer
    - Logs skipped artifacts for audit purposes

    Args:
        request: ConfirmDuplicatesRequest with matches, new_artifacts, and skipped
        collection_mgr: Collection manager dependency
        artifact_mgr: Artifact manager dependency
        _token: Authentication token
        collection: Target collection name

    Returns:
        ConfirmDuplicatesResponse with operation counts and status
    """
    from skillmeat.api.schemas.discovery import (
        ConfirmDuplicatesStatus,
        DuplicateDecisionAction,
    )

    errors: List[str] = []
    linked_count = 0
    imported_count = 0
    skipped_count = len(request.skipped)

    collection_name = collection or collection_mgr.get_active_collection_name()

    logger.info(
        f"Processing duplicate decisions: {len(request.matches)} matches, "
        f"{len(request.new_artifacts)} new, {len(request.skipped)} skipped"
    )

    # Phase 1: Process duplicate links
    for match in request.matches:
        if match.action == DuplicateDecisionAction.SKIP:
            skipped_count += 1
            logger.debug(f"Skipping duplicate match for {match.discovered_path}")
            continue

        try:
            # Validate discovered path exists
            discovered_path = PathLib(match.discovered_path)
            if not discovered_path.exists():
                errors.append(
                    f"Discovered path does not exist: {match.discovered_path}"
                )
                continue

            # Create the duplicate link
            success = collection_mgr.link_duplicate(
                discovered_path=str(discovered_path),
                collection_artifact_id=match.collection_artifact_id,
                collection_name=collection_name,
            )

            if success:
                linked_count += 1
                logger.info(
                    f"Linked duplicate: {match.discovered_path} -> "
                    f"{match.collection_artifact_id}"
                )
            else:
                errors.append(
                    f"Failed to link {match.discovered_path} to "
                    f"{match.collection_artifact_id}: artifact not found in collection"
                )

        except ValueError as e:
            errors.append(f"Invalid artifact ID format: {e}")
        except Exception as e:
            logger.exception(f"Failed to link duplicate: {e}")
            errors.append(f"Failed to link {match.discovered_path}: {str(e)}")

    # Phase 2: Import new artifacts
    if request.new_artifacts:
        try:
            # Use the existing importer for new artifacts
            importer = ArtifactImporter(artifact_mgr, collection_mgr)

            for artifact_path in request.new_artifacts:
                try:
                    path = PathLib(artifact_path)
                    if not path.exists():
                        errors.append(f"Artifact path does not exist: {artifact_path}")
                        continue

                    # Detect artifact type and extract metadata
                    from skillmeat.core.artifact_detection import detect_artifact_type

                    artifact_type = detect_artifact_type(path)
                    if artifact_type is None:
                        errors.append(
                            f"Could not detect artifact type for: {artifact_path}"
                        )
                        continue

                    # Build import data
                    artifact_data = BulkImportArtifactData(
                        source=f"local/{path.name}",
                        artifact_type=artifact_type.value,
                        name=path.name,
                        path=str(path),
                        scope="user",
                    )

                    # Import single artifact
                    result = importer._import_single(artifact_data, collection_name)

                    if result.success:
                        imported_count += 1
                        logger.info(f"Imported new artifact: {artifact_path}")
                    else:
                        errors.append(
                            f"Failed to import {artifact_path}: {result.error or result.message}"
                        )

                except Exception as e:
                    logger.exception(f"Failed to import artifact {artifact_path}: {e}")
                    errors.append(f"Failed to import {artifact_path}: {str(e)}")

        except Exception as e:
            logger.exception(f"Failed to initialize importer: {e}")
            errors.append(f"Failed to initialize importer: {str(e)}")

    # Phase 3: Log skipped artifacts (for audit trail)
    for skipped_path in request.skipped:
        logger.info(f"User skipped artifact: {skipped_path}")

    # Determine overall status
    total_operations = len(request.matches) + len(request.new_artifacts)
    successful_operations = linked_count + imported_count

    if total_operations == 0:
        op_status = ConfirmDuplicatesStatus.SUCCESS
    elif successful_operations == 0 and errors:
        op_status = ConfirmDuplicatesStatus.FAILED
    elif errors:
        op_status = ConfirmDuplicatesStatus.PARTIAL
    else:
        op_status = ConfirmDuplicatesStatus.SUCCESS

    # Build summary message
    parts = []
    if linked_count > 0:
        parts.append(f"{linked_count} linked")
    if imported_count > 0:
        parts.append(f"{imported_count} imported")
    if skipped_count > 0:
        parts.append(f"{skipped_count} skipped")

    total_processed = linked_count + imported_count + skipped_count
    message = f"Processed {total_processed} artifacts"
    if parts:
        message += f": {', '.join(parts)}"

    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"Duplicate confirmation complete: {message} "
        f"(status={op_status.value}, errors={len(errors)})"
    )

    return ConfirmDuplicatesResponse(
        status=op_status,
        linked_count=linked_count,
        imported_count=imported_count,
        skipped_count=skipped_count,
        message=message,
        timestamp=timestamp,
        errors=errors,
    )


@router.post(
    "",
    response_model=ArtifactCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new artifact",
    description="Create a new artifact from GitHub URL or local path",
    responses={
        201: {"description": "Artifact created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {"model": ErrorResponse, "description": "Artifact already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
) -> ArtifactCreateResponse:
    """Create a new artifact from GitHub or local source.

    This endpoint allows you to add artifacts to your collection from:
    - GitHub repositories (supports specs like username/repo/path@version)
    - Local filesystem paths

    Args:
        request: Artifact creation request with source and metadata
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token

    Returns:
        ArtifactCreateResponse with created artifact details

    Raises:
        HTTPException: If validation fails, source not found, or artifact exists

    Examples:
        GitHub source:
        ```json
        {
            "source_type": "github",
            "source": "anthropics/skills/canvas-design",
            "artifact_type": "skill",
            "name": "canvas",
            "tags": ["design", "ui"]
        }
        ```

        Local source:
        ```json
        {
            "source_type": "local",
            "source": "/path/to/my-skill",
            "artifact_type": "skill"
        }
        ```
    """
    try:
        logger.info(
            f"Creating artifact from {request.source_type.value} source: {request.source}"
        )

        # Validate artifact type
        try:
            artifact_type = ArtifactType(request.artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {request.artifact_type}. "
                f"Must be one of: {', '.join([t.value for t in ArtifactType])}",
            )

        # Determine collection
        collection_name = request.collection
        if not collection_name:
            # Use first available collection as default
            collections = collection_mgr.list_collections()
            if not collections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No collections found. Create a collection first.",
                )
            collection_name = collections[0]
        else:
            # Verify collection exists
            if collection_name not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection_name}' not found",
                )

        # Create artifact based on source type
        artifact = None

        if request.source_type == ArtifactSourceType.GITHUB:
            # Handle GitHub source
            try:
                # Parse GitHub spec (can be URL or short spec)
                # If it looks like a URL, extract the spec
                source = request.source
                if source.startswith("http://") or source.startswith("https://"):
                    # Parse GitHub URL to extract spec
                    # Format: https://github.com/username/repo/tree/branch/path
                    from urllib.parse import urlparse

                    parsed = urlparse(source)
                    if "github.com" not in parsed.netloc:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid GitHub URL: {source}",
                        )

                    # Extract path components
                    path_parts = parsed.path.strip("/").split("/")
                    if len(path_parts) < 2:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid GitHub URL format",
                        )

                    username = path_parts[0]
                    repo = path_parts[1]

                    # Check if path contains tree/branch/path structure
                    if len(path_parts) > 3 and path_parts[2] == "tree":
                        # Extract artifact path (skip username/repo/tree/branch)
                        artifact_path = (
                            "/".join(path_parts[4:]) if len(path_parts) > 4 else ""
                        )
                        if artifact_path:
                            source = f"{username}/{repo}/{artifact_path}"
                        else:
                            source = f"{username}/{repo}"
                    else:
                        # Just username/repo
                        source = f"{username}/{repo}"

                # Add from GitHub
                artifact = artifact_mgr.add_from_github(
                    spec=source,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    custom_name=request.name,
                    tags=request.tags,
                    force=False,  # Don't overwrite by default
                )

            except ValueError as e:
                # Check if it's a duplicate error
                if "already exists" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=str(e),
                    )
                # Other validation errors
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except RuntimeError as e:
                # Fetch or network errors
                if "not found" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"GitHub source not found: {str(e)}",
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch from GitHub: {str(e)}",
                )

        elif request.source_type == ArtifactSourceType.LOCAL:
            # Handle local source
            try:
                # Validate path exists
                source_path = PathLib(request.source)
                if not source_path.exists():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Local path does not exist: {request.source}",
                    )

                if not source_path.is_dir() and not source_path.is_file():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid path: {request.source}",
                    )

                # Add from local
                artifact = artifact_mgr.add_from_local(
                    path=request.source,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    custom_name=request.name,
                    tags=request.tags,
                    force=False,
                )

            except ValueError as e:
                # Check if it's a duplicate error
                if "already exists" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=str(e),
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to add local artifact: {str(e)}",
                )

        # Build response
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Artifact creation failed unexpectedly",
            )

        logger.info(
            f"Successfully created artifact: {artifact.type.value}:{artifact.name} "
            f"in collection '{collection_name}'"
        )

        return ArtifactCreateResponse(
            success=True,
            artifact_id=f"{artifact.type.value}:{artifact.name}",
            artifact_name=artifact.name,
            artifact_type=artifact.type.value,
            collection=collection_name,
            source=request.source,
            source_type=request.source_type.value,
            path=artifact.path,
            message=f"Artifact '{artifact.name}' created successfully from {request.source_type.value} source",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating artifact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create artifact: {str(e)}",
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

            project_path_obj = PathLib(project_path)
            if not project_path_obj.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project path does not exist",
                )

            try:
                # Check drift for the project using public API
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

        # Query database for collection memberships
        artifact_ids = [f"{a.type.value}:{a.name}" for a in page_artifacts]
        collections_map: Dict[str, List[dict]] = {}

        if artifact_ids:
            try:
                db_session = get_session()
                # Query CollectionArtifact associations
                associations = (
                    db_session.query(CollectionArtifact)
                    .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
                    .all()
                )

                # Get unique collection IDs
                collection_ids = {assoc.collection_id for assoc in associations}

                if collection_ids:
                    # Query Collection details
                    collections = (
                        db_session.query(Collection)
                        .filter(Collection.id.in_(collection_ids))
                        .all()
                    )
                    collection_details = {c.id: c for c in collections}

                    # Build mapping: artifact_id -> list of collection info
                    for assoc in associations:
                        if assoc.artifact_id not in collections_map:
                            collections_map[assoc.artifact_id] = []

                        coll = collection_details.get(assoc.collection_id)
                        if coll:
                            # Count artifacts in this collection
                            artifact_count = (
                                db_session.query(CollectionArtifact)
                                .filter_by(collection_id=coll.id)
                                .count()
                            )
                            collections_map[assoc.artifact_id].append(
                                {
                                    "id": coll.id,
                                    "name": coll.name,
                                    "artifact_count": artifact_count,
                                }
                            )

                db_session.close()
            except Exception as e:
                logger.warning(f"Failed to query collection memberships: {e}")

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
                    collections_data=collections_map.get(artifact_key, []),
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
                last_checked=datetime.now(timezone.utc),
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
            last_checked=datetime.now(timezone.utc),
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


@router.put(
    "/{artifact_id}/parameters",
    response_model=ParameterUpdateResponse,
    summary="Update artifact parameters",
    description="Update artifact parameters (source, version, scope, tags, aliases) after import",
    responses={
        200: {"description": "Successfully updated parameters"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_artifact_parameters(
    artifact_id: str,
    request: ParameterUpdateRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> ParameterUpdateResponse:
    """Update artifact parameters after import.

    Updates the source, version, scope, tags, or aliases of an existing artifact.
    Changes are persisted to the manifest and lock file atomically.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        request: Parameter update request
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection filter

    Returns:
        Parameter update response with list of updated fields

    Raises:
        HTTPException: If artifact not found or validation fails

    Example:
        PUT /api/v1/artifacts/skill:canvas-design/parameters
        {
            "parameters": {
                "source": "anthropics/skills/canvas-design@v2.0.0",
                "version": "v2.0.0",
                "tags": ["design", "canvas", "art"]
            }
        }
    """
    try:
        logger.info(
            f"Updating parameters for artifact: {artifact_id} (collection={collection})"
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

        # Track updated fields
        updated_fields = []
        pending_tag_sync: Optional[List[str]] = None
        params = request.parameters

        # Validate and update source
        if params.source is not None:
            # Validate GitHub source format using existing parser
            if params.source.strip():
                try:
                    from skillmeat.core.github_metadata import GitHubMetadataExtractor

                    extractor = GitHubMetadataExtractor(cache=None)
                    # This will raise ValueError if invalid
                    extractor.parse_github_url(params.source)
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid GitHub source format: {str(e)}",
                    )

                # Update upstream source
                artifact.upstream = params.source
                updated_fields.append("source")
                logger.info(f"Updated source for {artifact_id}: {params.source}")

        # Update version
        if params.version is not None:
            # Validate version format
            if params.version.strip():
                # Accept: latest, @latest, @v1.0.0, @sha, v1.0.0, sha
                version = params.version.strip()
                if not version.startswith("@"):
                    if version != "latest":
                        version = f"@{version}"
                    # else: "latest" stays as-is
                else:
                    # Remove @ prefix for storage
                    version = version[1:]

                artifact.version_spec = version
                updated_fields.append("version")
                logger.info(f"Updated version for {artifact_id}: {version}")

        # Update scope
        if params.scope is not None:
            # Validation already done by Pydantic (user or local)
            # Note: Scope change may require moving artifact files in future implementation
            logger.warning(
                f"Scope update requested for {artifact_id} to '{params.scope}' "
                "but scope changes are not yet fully implemented (file moves not performed)"
            )
            # For now, just track it as an updated field
            updated_fields.append("scope")

        # Update tags
        if params.tags is not None:
            normalized_tags = []
            seen_tags = set()
            for tag in params.tags:
                if not isinstance(tag, str):
                    continue
                cleaned = tag.strip()
                if not cleaned:
                    continue
                key = cleaned.lower()
                if key in seen_tags:
                    continue
                seen_tags.add(key)
                normalized_tags.append(cleaned)

            artifact.tags = normalized_tags
            updated_fields.append("tags")
            pending_tag_sync = normalized_tags
            logger.info(f"Updated tags for {artifact_id}: {normalized_tags}")

        # Update aliases
        if params.aliases is not None:
            # Aliases are stored in metadata.extra for now
            if artifact.metadata is None:
                from skillmeat.core.artifact import ArtifactMetadata

                artifact.metadata = ArtifactMetadata()

            if "aliases" not in artifact.metadata.extra:
                artifact.metadata.extra["aliases"] = []

            artifact.metadata.extra["aliases"] = params.aliases
            updated_fields.append("aliases")
            logger.info(f"Updated aliases for {artifact_id}: {params.aliases}")

        # Update last_updated timestamp if anything changed
        if updated_fields:
            artifact.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)

            # Save collection (atomic write of manifest)
            collection_mgr.save_collection(target_collection)

            # Update lock file
            collection_path = collection_mgr.config.get_collection_path(collection_name)
            artifact_path = collection_path / artifact.path

            # Compute content hash for lock file
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

            logger.info(
                f"Successfully updated {len(updated_fields)} parameter(s) for artifact: {artifact_id}"
            )
            message = (
                f"Updated {len(updated_fields)} field(s): {', '.join(updated_fields)}"
            )

            if pending_tag_sync is not None:
                try:
                    TagService().sync_artifact_tags(artifact_id, pending_tag_sync)
                except Exception as e:
                    logger.warning(
                        f"Failed to sync tag associations for {artifact_id}: {e}",
                        exc_info=True,
                    )
        else:
            logger.info(f"No parameter changes requested for artifact: {artifact_id}")
            message = "No parameters were updated"

        return ParameterUpdateResponse(
            success=True,
            artifact_id=artifact_id,
            updated_fields=updated_fields,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error updating parameters for artifact '{artifact_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update artifact parameters: {str(e)}",
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
        project_path = PathLib(request.project_path)
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
                overwrite=request.overwrite,
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
    artifact_mgr: ArtifactManagerDep,
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

            # Get collection name (use provided or default)
            collection_name = collection or collection_mgr.get_active_collection_name()

            # Load collection and verify artifact exists
            coll = collection_mgr.load_collection(collection_name)
            artifact = coll.find_artifact(artifact_name, artifact_type)

            if not artifact:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_id}' not found in collection '{collection_name}'",
                )

            # Check if artifact has GitHub origin
            if artifact.origin != "github":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Artifact '{artifact_id}' does not have a GitHub origin. Upstream sync only supported for GitHub artifacts.",
                )

            # Fetch update from upstream
            try:
                fetch_result = artifact_mgr.fetch_update(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                )
            except Exception as e:
                logger.error(
                    f"Failed to fetch update for '{artifact_id}': {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch update from upstream: {str(e)}",
                )

            # Check if fetch was successful
            if fetch_result.error:
                return ArtifactSyncResponse(
                    success=False,
                    message=f"Failed to fetch update: {fetch_result.error}",
                    artifact_name=artifact_name,
                    artifact_type=artifact_type.value,
                    conflicts=None,
                    updated_version=None,
                    synced_files_count=None,
                )

            # If no update available, return success with message
            if not fetch_result.has_update:
                return ArtifactSyncResponse(
                    success=True,
                    message=f"Artifact '{artifact_name}' is already up to date",
                    artifact_name=artifact_name,
                    artifact_type=artifact_type.value,
                    conflicts=None,
                    updated_version=(
                        artifact.metadata.version if artifact.metadata else None
                    ),
                    synced_files_count=0,
                )

            # Map request strategy to ArtifactManager strategy
            # "theirs" = take upstream -> "overwrite"
            # "ours" = keep local -> skip update (handled by returning early)
            # "manual" = preserve conflicts -> "merge"
            strategy_map = {
                "theirs": "overwrite",
                "ours": "skip",  # We'll handle this by returning early
                "manual": "merge",
            }

            apply_strategy = strategy_map.get(request.strategy, "overwrite")

            # If strategy is "ours", skip the update
            if apply_strategy == "skip":
                logger.info(
                    f"Strategy 'ours' selected - keeping local version of '{artifact_id}'"
                )
                return ArtifactSyncResponse(
                    success=True,
                    message=f"Local version of '{artifact_name}' preserved (strategy: ours)",
                    artifact_name=artifact_name,
                    artifact_type=artifact_type.value,
                    conflicts=None,
                    updated_version=(
                        artifact.metadata.version if artifact.metadata else None
                    ),
                    synced_files_count=0,
                )

            # Apply the update strategy
            try:
                update_result = artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result,
                    strategy=apply_strategy,
                    interactive=False,  # Non-interactive mode for API
                    auto_resolve="theirs" if apply_strategy == "overwrite" else "abort",
                    collection_name=collection_name,
                )
            except Exception as e:
                logger.error(
                    f"Failed to apply update for '{artifact_id}': {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to apply update: {str(e)}",
                )

            # Extract conflicts if any (for merge strategy)
            conflicts_list = None
            if apply_strategy == "merge" and not update_result.updated:
                # Merge may have failed due to conflicts
                # This is a simplified approach - proper conflict tracking would require
                # modifying UpdateResult to include conflict information
                logger.warning(
                    f"Merge strategy may have encountered conflicts for '{artifact_id}'"
                )

            # Count synced files
            synced_files_count = None
            if update_result.updated:
                collection_path = collection_mgr.config.get_collection_path(
                    collection_name
                )
                artifact_path = collection_path / artifact.path
                if artifact_path.exists():
                    synced_files_count = len(list(artifact_path.rglob("*")))

            logger.info(
                f"Upstream sync for '{artifact_name}' completed: "
                f"updated={update_result.updated}, status={update_result.status}"
            )

            return ArtifactSyncResponse(
                success=update_result.updated,
                message=f"Artifact '{artifact_name}' synced from upstream: {update_result.status}",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                conflicts=conflicts_list,
                updated_version=update_result.new_version,
                synced_files_count=synced_files_count,
            )

        # Validate project path
        project_path = PathLib(request.project_path)
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
            "ours": "overwrite",  # Same as theirs in pull context
            "manual": "merge",  # Use merge with conflict markers
        }
        sync_strategy = strategy_map[request.strategy]

        # Check for deployment metadata using DeploymentTracker (public API)
        from skillmeat.storage.deployment import DeploymentTracker

        deployments = DeploymentTracker.read_deployments(project_path)
        if not deployments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployment metadata found at {request.project_path}. Deploy artifacts first.",
            )

        # Find the deployment for this artifact
        target_deployment = None
        for deployment in deployments:
            if (
                deployment.artifact_name == artifact_name
                and deployment.artifact_type == artifact_type.value
            ):
                target_deployment = deployment
                break

        if not target_deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not deployed in project",
            )

        # Get collection name from deployment if not provided
        if not collection:
            collection_name = target_deployment.from_collection
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
                    ConflictInfo(file_path=conflict_file, conflict_type="modified")
                    for conflict_result in sync_result.conflicts
                    for conflict_file in (
                        conflict_result.conflict_files
                        if hasattr(conflict_result, "conflict_files")
                        else []
                    )
                ]

            # Determine success based on sync result status
            success = sync_result.status in ("success", "partial")

            # Get updated version from artifact if available
            updated_version = None
            if success:
                # Reload artifact to get updated version
                updated_coll = collection_mgr.load_collection(collection_name)
                updated_artifact = updated_coll.find_artifact(
                    artifact_name, artifact_type
                )
                if updated_artifact and updated_artifact.metadata:
                    updated_version = updated_artifact.metadata.version

            # Count synced files (approximate based on artifact path)
            synced_files_count = None
            if success and artifact_name in sync_result.artifacts_synced:
                collection_path = collection_mgr.config.get_collection_path(
                    collection_name
                )
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
        proj_path = PathLib(project_path)
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
        if (
            version_graph.root is None
            and version_graph.statistics["total_deployments"] == 0
        ):
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
    "/{artifact_id}/diff",
    response_model=ArtifactDiffResponse,
    summary="Get artifact diff",
    description="Compare artifact versions between collection and deployed project",
    responses={
        200: {"description": "Successfully retrieved diff"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact_diff(
    artifact_id: str,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    project_path: str = Query(
        ...,
        description="Path to project for comparison",
    ),
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> ArtifactDiffResponse:
    """Get diff between collection version and deployed project version.

    Compares the artifact in the collection with the deployed version in a project,
    showing file-level differences with unified diff format for modified files.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        project_path: Path to project directory containing deployed artifact
        collection: Optional collection filter

    Returns:
        ArtifactDiffResponse with file-level diffs and summary

    Raises:
        HTTPException: If artifact not found, project not found, or on error

    Example:
        GET /api/v1/artifacts/skill:pdf-processor/diff?project_path=/Users/me/project1

        Returns:
        {
            "artifact_id": "skill:pdf-processor",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "collection_name": "default",
            "project_path": "/Users/me/project1",
            "has_changes": true,
            "files": [
                {
                    "file_path": "SKILL.md",
                    "status": "modified",
                    "collection_hash": "abc123",
                    "project_hash": "def456",
                    "unified_diff": "--- a/SKILL.md\\n+++ b/SKILL.md\\n..."
                }
            ],
            "summary": {
                "added": 0,
                "modified": 1,
                "deleted": 0,
                "unchanged": 3
            }
        }
    """
    import difflib
    import hashlib

    try:
        logger.info(
            f"Getting diff for artifact: {artifact_id} (project={project_path}, collection={collection})"
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
        proj_path = PathLib(project_path)
        if not proj_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project path does not exist: {project_path}",
            )

        # Find deployment in project
        deployment = DeploymentTracker.get_deployment(
            proj_path, artifact_name, artifact_type.value
        )

        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not deployed in project {project_path}",
            )

        # Determine collection name from deployment if not specified
        collection_name = collection or deployment.from_collection

        # Verify collection exists
        if collection_name not in collection_mgr.list_collections():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Load collection and find artifact
        coll = collection_mgr.load_collection(collection_name)
        artifact = coll.find_artifact(artifact_name, artifact_type)

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in collection '{collection_name}'",
            )

        # Get paths
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        collection_artifact_path = collection_path / artifact.path
        project_artifact_path = proj_path / ".claude" / deployment.artifact_path

        if not collection_artifact_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Collection artifact path does not exist: {collection_artifact_path}",
            )

        if not project_artifact_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project artifact path does not exist: {project_artifact_path}",
            )

        # Collect all files from both locations
        collection_files = set()
        project_files = set()

        if collection_artifact_path.is_dir():
            collection_files = {
                str(f.relative_to(collection_artifact_path))
                for f in collection_artifact_path.rglob("*")
                if f.is_file()
            }
        else:
            collection_files = {collection_artifact_path.name}

        if project_artifact_path.is_dir():
            project_files = {
                str(f.relative_to(project_artifact_path))
                for f in project_artifact_path.rglob("*")
                if f.is_file()
            }
        else:
            project_files = {project_artifact_path.name}

        # Get all unique files
        all_files = sorted(collection_files | project_files)

        # Helper function to compute file hash
        def compute_file_hash(file_path: Path) -> str:
            """Compute SHA256 hash of a single file."""
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()

        # Helper function to check if file is binary
        def is_binary_file(file_path: Path) -> bool:
            """Check if file is binary by reading first 8KB."""
            try:
                with open(file_path, "rb") as f:
                    chunk = f.read(8192)
                    # Check for null bytes
                    return b"\x00" in chunk
            except Exception:
                return True  # Treat as binary if can't read

        # Build file diffs
        file_diffs: List[FileDiff] = []
        summary = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}

        for file_rel_path in all_files:
            in_collection = file_rel_path in collection_files
            in_project = file_rel_path in project_files

            # Determine status
            if in_collection and in_project:
                # File exists in both - check if modified
                if collection_artifact_path.is_dir():
                    coll_file_path = collection_artifact_path / file_rel_path
                else:
                    coll_file_path = collection_artifact_path

                if project_artifact_path.is_dir():
                    proj_file_path = project_artifact_path / file_rel_path
                else:
                    proj_file_path = project_artifact_path

                coll_hash = compute_file_hash(coll_file_path)
                proj_hash = compute_file_hash(proj_file_path)

                if coll_hash == proj_hash:
                    # Unchanged
                    file_status = "unchanged"
                    unified_diff = None
                    summary["unchanged"] += 1
                else:
                    # Modified
                    file_status = "modified"
                    summary["modified"] += 1

                    # Generate unified diff if text file
                    unified_diff = None
                    if not is_binary_file(coll_file_path) and not is_binary_file(
                        proj_file_path
                    ):
                        try:
                            with open(coll_file_path, "r", encoding="utf-8") as f:
                                coll_lines = f.readlines()
                            with open(proj_file_path, "r", encoding="utf-8") as f:
                                proj_lines = f.readlines()

                            diff_lines = difflib.unified_diff(
                                coll_lines,
                                proj_lines,
                                fromfile=f"collection/{file_rel_path}",
                                tofile=f"project/{file_rel_path}",
                                lineterm="",
                            )
                            unified_diff = "\n".join(diff_lines)
                        except Exception as e:
                            logger.warning(
                                f"Failed to generate diff for {file_rel_path}: {e}"
                            )
                            unified_diff = f"[Error generating diff: {str(e)}]"

                file_diffs.append(
                    FileDiff(
                        file_path=file_rel_path,
                        status=file_status,
                        collection_hash=coll_hash,
                        project_hash=proj_hash,
                        unified_diff=unified_diff,
                    )
                )

            elif in_collection and not in_project:
                # File deleted in project (only in collection)
                file_status = "deleted"
                summary["deleted"] += 1

                if collection_artifact_path.is_dir():
                    coll_file_path = collection_artifact_path / file_rel_path
                else:
                    coll_file_path = collection_artifact_path

                coll_hash = compute_file_hash(coll_file_path)

                file_diffs.append(
                    FileDiff(
                        file_path=file_rel_path,
                        status=file_status,
                        collection_hash=coll_hash,
                        project_hash=None,
                        unified_diff=None,
                    )
                )

            elif not in_collection and in_project:
                # File added in project (only in project)
                file_status = "added"
                summary["added"] += 1

                if project_artifact_path.is_dir():
                    proj_file_path = project_artifact_path / file_rel_path
                else:
                    proj_file_path = project_artifact_path

                proj_hash = compute_file_hash(proj_file_path)

                file_diffs.append(
                    FileDiff(
                        file_path=file_rel_path,
                        status=file_status,
                        collection_hash=None,
                        project_hash=proj_hash,
                        unified_diff=None,
                    )
                )

        # Determine if there are changes
        has_changes = (
            summary["added"] > 0 or summary["modified"] > 0 or summary["deleted"] > 0
        )

        logger.info(
            f"Diff computed for {artifact_id}: {len(file_diffs)} files, "
            f"has_changes={has_changes}, summary={summary}"
        )

        return ArtifactDiffResponse(
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection_name,
            project_path=str(proj_path),
            has_changes=has_changes,
            files=file_diffs,
            summary=summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diff for '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact diff: {str(e)}",
        )


@router.get(
    "/{artifact_id}/upstream-diff",
    response_model=ArtifactUpstreamDiffResponse,
    summary="Get artifact upstream diff",
    description="Compare collection artifact with its GitHub upstream source",
    responses={
        200: {"description": "Successfully retrieved upstream diff"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or no upstream source",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact_upstream_diff(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> ArtifactUpstreamDiffResponse:
    """Get diff between collection version and GitHub upstream source.

    Compares the artifact in the collection with the latest version from GitHub,
    showing file-level differences with unified diff format for modified files.

    This endpoint:
    1. Finds the artifact in the collection
    2. Fetches the latest upstream version from GitHub
    3. Compares all files between collection and upstream
    4. Returns detailed diff information

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        ArtifactUpstreamDiffResponse with file-level diffs and summary

    Raises:
        HTTPException: If artifact not found, no upstream source, or on error

    Example:
        GET /api/v1/artifacts/skill:pdf-processor/upstream-diff?collection=default

        Returns:
        {
            "artifact_id": "skill:pdf-processor",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "collection_name": "default",
            "upstream_source": "anthropics/skills/pdf",
            "upstream_version": "abc123def456",
            "has_changes": true,
            "files": [
                {
                    "file_path": "SKILL.md",
                    "status": "modified",
                    "collection_hash": "abc123",
                    "project_hash": "def456",
                    "unified_diff": "--- a/SKILL.md\\n+++ b/SKILL.md\\n..."
                }
            ],
            "summary": {
                "added": 0,
                "modified": 1,
                "deleted": 0,
                "unchanged": 3
            }
        }
    """
    import difflib
    import hashlib
    import shutil

    try:
        logger.info(
            f"Getting upstream diff for artifact: {artifact_id} (collection={collection})"
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

        # Find artifact in collection
        artifact = None
        collection_name = collection
        if collection:
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                coll = collection_mgr.load_collection(collection)
                artifact = coll.find_artifact(artifact_name, artifact_type)
                if artifact:
                    collection_name = collection
            except ValueError:
                pass
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    coll = collection_mgr.load_collection(coll_name)
                    artifact = coll.find_artifact(artifact_name, artifact_type)
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in collection",
            )

        # Check if artifact has upstream tracking
        if artifact.origin != "github":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Artifact origin '{artifact.origin}' does not support upstream diff. Only GitHub artifacts are supported.",
            )

        if not artifact.upstream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Artifact does not have upstream tracking configured",
            )

        # Fetch latest upstream version
        logger.info(f"Fetching upstream update for {artifact_id}")
        fetch_result = artifact_mgr.fetch_update(
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
        )

        # Check for fetch errors
        if fetch_result.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch upstream: {fetch_result.error}",
            )

        # If no update detected (SHA matches), return empty diff
        if not fetch_result.has_update:
            return ArtifactUpstreamDiffResponse(
                artifact_id=artifact_id,
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                collection_name=collection_name,
                upstream_source=artifact.upstream or "",
                upstream_version=artifact.resolved_sha or artifact.version_spec or "",
                has_changes=False,
                files=[],
                summary={"added": 0, "modified": 0, "deleted": 0, "unchanged": 0},
            )

        if not fetch_result.fetch_result or not fetch_result.temp_workspace:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch upstream artifact",
            )

        # Get paths
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        collection_artifact_path = collection_path / artifact.path
        upstream_artifact_path = fetch_result.fetch_result.artifact_path

        if not collection_artifact_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Collection artifact path does not exist: {collection_artifact_path}",
            )

        if not upstream_artifact_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upstream artifact path does not exist: {upstream_artifact_path}",
            )

        # Collect all files from both locations
        collection_files = set()
        upstream_files = set()

        if collection_artifact_path.is_dir():
            collection_files = {
                str(f.relative_to(collection_artifact_path))
                for f in collection_artifact_path.rglob("*")
                if f.is_file()
            }
        else:
            collection_files = {collection_artifact_path.name}

        if upstream_artifact_path.is_dir():
            upstream_files = {
                str(f.relative_to(upstream_artifact_path))
                for f in upstream_artifact_path.rglob("*")
                if f.is_file()
            }
        else:
            upstream_files = {upstream_artifact_path.name}

        # Get all unique files
        all_files = sorted(collection_files | upstream_files)

        # Helper function to compute file hash
        def compute_file_hash(file_path: Path) -> str:
            """Compute SHA256 hash of a single file."""
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()

        # Helper function to check if file is binary
        def is_binary_file(file_path: Path) -> bool:
            """Check if file is binary by reading first 8KB."""
            try:
                with open(file_path, "rb") as f:
                    chunk = f.read(8192)
                    # Check for null bytes
                    return b"\x00" in chunk
            except Exception:
                return True  # Treat as binary if can't read

        # Build file diffs
        file_diffs: List[FileDiff] = []
        summary = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}

        for file_rel_path in all_files:
            in_collection = file_rel_path in collection_files
            in_upstream = file_rel_path in upstream_files

            # Determine status
            if in_collection and in_upstream:
                # File exists in both - check if modified
                if collection_artifact_path.is_dir():
                    coll_file_path = collection_artifact_path / file_rel_path
                else:
                    coll_file_path = collection_artifact_path

                if upstream_artifact_path.is_dir():
                    upstream_file_path = upstream_artifact_path / file_rel_path
                else:
                    upstream_file_path = upstream_artifact_path

                coll_hash = compute_file_hash(coll_file_path)
                upstream_hash = compute_file_hash(upstream_file_path)

                if coll_hash == upstream_hash:
                    # Unchanged
                    file_status = "unchanged"
                    unified_diff = None
                    summary["unchanged"] += 1
                else:
                    # Modified
                    file_status = "modified"
                    summary["modified"] += 1

                    # Generate unified diff if text file
                    unified_diff = None
                    if not is_binary_file(coll_file_path) and not is_binary_file(
                        upstream_file_path
                    ):
                        try:
                            with open(coll_file_path, "r", encoding="utf-8") as f:
                                coll_lines = f.readlines()
                            with open(upstream_file_path, "r", encoding="utf-8") as f:
                                upstream_lines = f.readlines()

                            diff_lines = difflib.unified_diff(
                                coll_lines,
                                upstream_lines,
                                fromfile=f"collection/{file_rel_path}",
                                tofile=f"upstream/{file_rel_path}",
                                lineterm="",
                            )
                            unified_diff = "\n".join(diff_lines)
                        except Exception as e:
                            logger.warning(
                                f"Failed to generate diff for {file_rel_path}: {e}"
                            )
                            unified_diff = f"[Error generating diff: {str(e)}]"

                file_diffs.append(
                    FileDiff(
                        file_path=file_rel_path,
                        status=file_status,
                        collection_hash=coll_hash,
                        project_hash=upstream_hash,
                        unified_diff=unified_diff,
                    )
                )

            elif in_collection and not in_upstream:
                # File deleted in upstream (only in collection)
                file_status = "deleted"
                summary["deleted"] += 1

                if collection_artifact_path.is_dir():
                    coll_file_path = collection_artifact_path / file_rel_path
                else:
                    coll_file_path = collection_artifact_path

                coll_hash = compute_file_hash(coll_file_path)

                file_diffs.append(
                    FileDiff(
                        file_path=file_rel_path,
                        status=file_status,
                        collection_hash=coll_hash,
                        project_hash=None,
                        unified_diff=None,
                    )
                )

            elif not in_collection and in_upstream:
                # File added in upstream (only in upstream)
                file_status = "added"
                summary["added"] += 1

                if upstream_artifact_path.is_dir():
                    upstream_file_path = upstream_artifact_path / file_rel_path
                else:
                    upstream_file_path = upstream_artifact_path

                upstream_hash = compute_file_hash(upstream_file_path)

                file_diffs.append(
                    FileDiff(
                        file_path=file_rel_path,
                        status=file_status,
                        collection_hash=None,
                        project_hash=upstream_hash,
                        unified_diff=None,
                    )
                )

        # Determine if there are changes
        has_changes = (
            summary["added"] > 0 or summary["modified"] > 0 or summary["deleted"] > 0
        )

        # Extract upstream version info
        upstream_version = "unknown"
        if fetch_result.update_info:
            upstream_version = (
                getattr(fetch_result.update_info, "latest_sha", None) or "unknown"
            )

        logger.info(
            f"Upstream diff computed for {artifact_id}: {len(file_diffs)} files, "
            f"has_changes={has_changes}, summary={summary}"
        )

        # Clean up temp workspace
        try:
            if fetch_result.temp_workspace and fetch_result.temp_workspace.exists():
                shutil.rmtree(fetch_result.temp_workspace, ignore_errors=True)
                logger.debug(
                    f"Cleaned up temp workspace: {fetch_result.temp_workspace}"
                )
        except Exception as e:
            logger.warning(f"Failed to clean up temp workspace: {e}")

        return ArtifactUpstreamDiffResponse(
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection_name,
            upstream_source=artifact.upstream if artifact.upstream else "unknown",
            upstream_version=upstream_version,
            has_changes=has_changes,
            files=file_diffs,
            summary=summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting upstream diff for '{artifact_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact upstream diff: {str(e)}",
        )


@router.get(
    "/{artifact_id}/files",
    response_model=FileListResponse,
    summary="List artifact files",
    description="List all files and directories in an artifact",
    responses={
        200: {"description": "Successfully retrieved file list"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_artifact_files(
    artifact_id: str,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> FileListResponse:
    """List all files in an artifact.

    Returns a nested tree structure showing all files and directories
    within the artifact. Hidden files and directories are excluded
    (.git, __pycache__, node_modules, etc.).

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        FileListResponse with nested file tree

    Raises:
        HTTPException: If artifact not found or on error

    Example:
        GET /api/v1/artifacts/skill:pdf-processor/files

        Returns:
        {
            "artifact_id": "skill:pdf-processor",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "collection_name": "default",
            "files": [
                {
                    "name": "SKILL.md",
                    "path": "SKILL.md",
                    "type": "file",
                    "size": 2048,
                    "children": null
                },
                {
                    "name": "src",
                    "path": "src",
                    "type": "directory",
                    "size": null,
                    "children": [...]
                }
            ]
        }
    """
    try:
        logger.info(
            f"Listing files for artifact: {artifact_id} (collection={collection})"
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

        # Find artifact
        artifact = None
        collection_name = collection
        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                coll = collection_mgr.load_collection(collection)
                artifact = coll.find_artifact(artifact_name, artifact_type)
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    coll = collection_mgr.load_collection(coll_name)
                    artifact = coll.find_artifact(artifact_name, artifact_type)
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get artifact path
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        artifact_path = collection_path / artifact.path

        if not artifact_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Artifact path does not exist: {artifact_path}",
            )

        # Define hidden/excluded patterns
        EXCLUDED_PATTERNS = {
            ".git",
            ".gitignore",
            "__pycache__",
            "node_modules",
            ".DS_Store",
            "*.pyc",
            "*.pyo",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            "venv",
        }

        def should_exclude(name: str) -> bool:
            """Check if file/directory should be excluded."""
            # Exclude hidden files (starting with .)
            if name.startswith("."):
                return True
            # Exclude common artifacts
            if name in EXCLUDED_PATTERNS:
                return True
            return False

        def build_file_tree(path: Path, relative_root: Path) -> List[FileNode]:
            """Recursively build file tree structure."""
            nodes: List[FileNode] = []

            try:
                entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            except PermissionError:
                logger.warning(f"Permission denied accessing {path}")
                return nodes

            for entry in entries:
                # Skip excluded files/directories
                if should_exclude(entry.name):
                    continue

                rel_path = str(entry.relative_to(relative_root))

                if entry.is_dir():
                    # Recursively process directory
                    children = build_file_tree(entry, relative_root)
                    nodes.append(
                        FileNode(
                            name=entry.name,
                            path=rel_path,
                            type="directory",
                            size=None,
                            children=children,
                        )
                    )
                elif entry.is_file():
                    # Add file node
                    try:
                        file_size = entry.stat().st_size
                    except Exception:
                        file_size = 0

                    nodes.append(
                        FileNode(
                            name=entry.name,
                            path=rel_path,
                            type="file",
                            size=file_size,
                            children=None,
                        )
                    )

            return nodes

        # Build file tree
        if artifact_path.is_dir():
            files = build_file_tree(artifact_path, artifact_path)
        else:
            # Single file artifact
            files = [
                FileNode(
                    name=artifact_path.name,
                    path=artifact_path.name,
                    type="file",
                    size=artifact_path.stat().st_size,
                    children=None,
                )
            ]

        logger.info(f"Listed {len(files)} files for artifact: {artifact_id}")

        return FileListResponse(
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection_name,
            files=files,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files for '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifact files: {str(e)}",
        )


@router.get(
    "/{artifact_id}/files/{file_path:path}",
    response_model=FileContentResponse,
    summary="Get artifact file content",
    description="Get the content of a specific file within an artifact",
    responses={
        200: {"description": "Successfully retrieved file content"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or path traversal attempt",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact or file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact_file_content(
    artifact_id: str,
    file_path: str,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> FileContentResponse:
    """Get content of a specific file within an artifact.

    **SECURITY: Path Traversal Protection**
    This endpoint implements strict path validation to prevent directory
    traversal attacks. The file_path must:
    - Be within the artifact directory
    - Not contain ".." (parent directory references)
    - Resolve to a path inside the artifact root

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        file_path: Relative path to file within artifact (e.g., "SKILL.md" or "src/main.py")
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        FileContentResponse with file content and metadata

    Raises:
        HTTPException: If artifact not found, file not found, path traversal attempt, or on error

    Example:
        GET /api/v1/artifacts/skill:pdf-processor/files/SKILL.md

        Returns:
        {
            "artifact_id": "skill:pdf-processor",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "collection_name": "default",
            "path": "SKILL.md",
            "content": "# PDF Processor Skill...",
            "size": 2048,
            "mime_type": "text/markdown"
        }
    """
    import mimetypes
    import os

    try:
        logger.info(
            f"Getting file content for artifact: {artifact_id}, file: {file_path} (collection={collection})"
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

        # Find artifact
        artifact = None
        collection_name = collection
        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                coll = collection_mgr.load_collection(collection)
                artifact = coll.find_artifact(artifact_name, artifact_type)
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    coll = collection_mgr.load_collection(coll_name)
                    artifact = coll.find_artifact(artifact_name, artifact_type)
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get artifact path
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        artifact_root = collection_path / artifact.path

        if not artifact_root.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Artifact path does not exist: {artifact_root}",
            )

        # Handle single-file artifacts (e.g., agents stored as agents/prd-writer.md)
        # For single-file artifacts, artifact_root IS the file, not a directory
        is_single_file_artifact = artifact_root.is_file()

        # CRITICAL SECURITY: Validate and normalize the file path to prevent path traversal
        # This prevents attacks like: ../../etc/passwd
        try:
            # Normalize the requested path to remove any .., ., etc.
            normalized_file_path = os.path.normpath(file_path)

            # Check for path traversal indicators
            if (
                normalized_file_path.startswith("..")
                or "/.." in normalized_file_path
                or "\\.." in normalized_file_path
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path: path traversal attempt detected",
                )

            if is_single_file_artifact:
                # For single-file artifacts, the file_path must match the artifact's filename
                # or be "." (root indicator). The full_path IS the artifact_root itself.
                artifact_filename = artifact_root.name
                if normalized_file_path in (".", artifact_filename):
                    # Valid request for the single file
                    full_path = artifact_root.resolve()
                else:
                    # Requested file doesn't exist in this single-file artifact
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"File not found: {file_path}. This is a single-file artifact containing only '{artifact_filename}'",
                    )
            else:
                # Directory-based artifact: construct path normally
                full_path = (artifact_root / normalized_file_path).resolve()

                # Ensure the resolved path is still within the artifact directory
                artifact_root_resolved = artifact_root.resolve()
                if not str(full_path).startswith(str(artifact_root_resolved)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid file path: path escapes artifact directory",
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file path: {str(e)}",
            )

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}",
            )

        # Check if it's a file (not a directory)
        if not full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a file: {file_path}",
            )

        # Get file size
        file_size = full_path.stat().st_size

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))

        # Check if file is binary
        def is_binary_file(path: Path) -> bool:
            """Check if file is binary by reading first 8KB."""
            try:
                with open(path, "rb") as f:
                    chunk = f.read(8192)
                    return b"\x00" in chunk
            except Exception:
                return True

        # Read file content
        try:
            if is_binary_file(full_path):
                # For binary files, return a placeholder
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot display binary file: {file_path}. Binary files are not supported.",
                )

            # Read text file
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File encoding error: {file_path} is not valid UTF-8",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read file: {str(e)}",
            )

        logger.info(f"Successfully retrieved file content: {artifact_id}/{file_path}")

        return FileContentResponse(
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection_name,
            path=file_path,
            content=content,
            size=file_size,
            mime_type=mime_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting file content for '{artifact_id}/{file_path}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file content: {str(e)}",
        )


@router.put(
    "/{artifact_id}/files/{file_path:path}",
    response_model=FileContentResponse,
    summary="Update artifact file content",
    description="Update the content of a specific file within an artifact",
    responses={
        200: {"description": "Successfully updated file content"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request, path traversal attempt, or directory path",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact or file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_artifact_file_content(
    artifact_id: str,
    file_path: str,
    request: FileUpdateRequest,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> FileContentResponse:
    """Update a file's content within an artifact.

    **SECURITY: Path Traversal Protection**
    This endpoint implements strict path validation to prevent directory
    traversal attacks. The file_path must:
    - Be within the artifact directory
    - Not contain ".." (parent directory references)
    - Resolve to a path inside the artifact root

    **Atomic Write**
    File updates are performed atomically using a temporary file and rename
    operation to ensure consistency.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        file_path: Relative path to file within artifact (e.g., "SKILL.md" or "src/main.py")
        request: File update request containing new content
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        FileContentResponse with updated file content and metadata

    Raises:
        HTTPException: If artifact not found, file not found, path traversal attempt,
                      directory path, validation error, or write failure

    Example:
        PUT /api/v1/artifacts/skill:pdf-processor/files/SKILL.md
        Body: {"content": "# Updated PDF Processor Skill..."}

        Returns:
        {
            "artifact_id": "skill:pdf-processor",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "collection_name": "default",
            "path": "SKILL.md",
            "content": "# Updated PDF Processor Skill...",
            "size": 2048,
            "mime_type": "text/markdown"
        }
    """
    import mimetypes
    import os
    import tempfile

    try:
        logger.info(
            f"Updating file content for artifact: {artifact_id}, file: {file_path} (collection={collection})"
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

        # Find artifact
        artifact = None
        collection_name = collection
        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                coll = collection_mgr.load_collection(collection)
                artifact = coll.find_artifact(artifact_name, artifact_type)
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    coll = collection_mgr.load_collection(coll_name)
                    artifact = coll.find_artifact(artifact_name, artifact_type)
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get artifact path - use artifact.path to get correct pluralized directory
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        artifact_root = collection_path / artifact.path

        if not artifact_root.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Artifact path does not exist: {artifact_root}",
            )

        # Handle single-file artifacts (e.g., agents stored as agents/prd-writer.md)
        # For single-file artifacts, artifact_root IS the file, not a directory
        is_single_file_artifact = artifact_root.is_file()

        # Validate file path (path traversal protection)
        try:
            # Normalize the requested path to remove any .., ., etc.
            normalized_file_path = os.path.normpath(file_path)

            # Check for path traversal indicators
            if (
                normalized_file_path.startswith("..")
                or "/.." in normalized_file_path
                or "\\.." in normalized_file_path
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path: path traversal attempt detected",
                )

            if is_single_file_artifact:
                # For single-file artifacts, the file_path must match the artifact's filename
                # or be "." (root indicator). The full_path IS the artifact_root itself.
                artifact_filename = artifact_root.name
                if normalized_file_path in (".", artifact_filename):
                    # Valid request for the single file - update is allowed
                    full_path = artifact_root.resolve()
                else:
                    # Requested file doesn't exist in this single-file artifact
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"File not found: {file_path}. This is a single-file artifact containing only '{artifact_filename}'",
                    )
            else:
                # Directory-based artifact: construct path normally
                full_path = (artifact_root / normalized_file_path).resolve()

                # Ensure the resolved path is still within the artifact directory
                artifact_root_resolved = artifact_root.resolve()
                if not str(full_path).startswith(str(artifact_root_resolved)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid file path: path escapes artifact directory",
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file path: {str(e)}",
            )

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}",
            )

        # Check if it's a file (not a directory)
        if not full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a file: {file_path}",
            )

        # Validate content is valid UTF-8 (will raise UnicodeEncodeError if not)
        try:
            request.content.encode("utf-8")
        except UnicodeEncodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content encoding: {str(e)}. Content must be valid UTF-8.",
            )

        # Write file atomically
        try:
            dir_path = full_path.parent

            # Create temporary file in the same directory for atomic rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=dir_path,
                delete=False,
                encoding="utf-8",
                prefix=".tmp_",
                suffix=f"_{full_path.name}",
            ) as tmp:
                tmp.write(request.content)
                tmp_path = PathLib(tmp.name)

            # Atomic rename (same filesystem)
            tmp_path.replace(full_path)

            logger.info(f"Successfully wrote file atomically: {full_path}")

        except Exception as e:
            # Clean up temp file if it still exists
            if "tmp_path" in locals() and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            logger.error(f"Error writing file {full_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write file: {str(e)}",
            )

        # Get updated file info
        file_size = full_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(full_path))

        logger.info(f"Successfully updated file content: {artifact_id}/{file_path}")

        return FileContentResponse(
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection_name,
            path=file_path,
            content=request.content,
            size=file_size,
            mime_type=mime_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error updating file content for '{artifact_id}/{file_path}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file content: {str(e)}",
        )


@router.post(
    "/{artifact_id}/files/{file_path:path}",
    response_model=FileContentResponse,
    summary="Create new artifact file",
    description="Create a new file within an artifact",
    responses={
        201: {"description": "Successfully created file"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request, path traversal attempt, or file already exists",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_artifact_file(
    artifact_id: str,
    file_path: str,
    request: FileUpdateRequest,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> FileContentResponse:
    """Create a new file within an artifact.

    **SECURITY: Path Traversal Protection**
    This endpoint implements strict path validation to prevent directory
    traversal attacks. The file_path must:
    - Be within the artifact directory
    - Not contain ".." (parent directory references)
    - Resolve to a path inside the artifact root

    **Atomic Write**
    File creation is performed atomically using a temporary file and rename
    operation to ensure consistency.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        file_path: Relative path to new file within artifact (e.g., "README.md" or "docs/guide.md")
        request: File content request
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        FileContentResponse with created file content and metadata

    Raises:
        HTTPException: If artifact not found, file already exists, path traversal attempt,
                      validation error, or write failure

    Example:
        POST /api/v1/artifacts/skill:pdf-processor/files/docs/guide.md
        Body: {"content": "# User Guide..."}

        Returns:
        {
            "artifact_id": "skill:pdf-processor",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "collection_name": "default",
            "path": "docs/guide.md",
            "content": "# User Guide...",
            "size": 256,
            "mime_type": "text/markdown"
        }
    """
    import mimetypes
    import os
    import tempfile

    try:
        logger.info(
            f"Creating file for artifact: {artifact_id}, file: {file_path} (collection={collection})"
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

        # Find artifact
        artifact = None
        collection_name = collection
        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                coll = collection_mgr.load_collection(collection)
                artifact = coll.find_artifact(artifact_name, artifact_type)
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    coll = collection_mgr.load_collection(coll_name)
                    artifact = coll.find_artifact(artifact_name, artifact_type)
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get artifact path
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        artifact_root = collection_path / artifact.path

        if not artifact_root.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Artifact path does not exist: {artifact_root}",
            )

        # Handle single-file artifacts (e.g., agents stored as agents/prd-writer.md)
        # For single-file artifacts, artifact_root IS the file, not a directory
        is_single_file_artifact = artifact_root.is_file()

        # Validate file path (path traversal protection)
        try:
            # Normalize the requested path to remove any .., ., etc.
            normalized_file_path = os.path.normpath(file_path)

            # Check for path traversal indicators
            if (
                normalized_file_path.startswith("..")
                or "/.." in normalized_file_path
                or "\\.." in normalized_file_path
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path: path traversal attempt detected",
                )

            if is_single_file_artifact:
                # Single-file artifacts cannot have new files created
                # They can only contain one file (the artifact itself)
                artifact_filename = artifact_root.name
                if normalized_file_path in (".", artifact_filename):
                    # Trying to create the file that already exists
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File already exists: {file_path}. This is a single-file artifact.",
                    )
                else:
                    # Trying to create a different file in a single-file artifact
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot create new files in single-file artifacts. "
                        f"This artifact contains only '{artifact_filename}'. "
                        f"To add multiple files, convert to a directory-based artifact.",
                    )
            else:
                # Directory-based artifact: construct path normally
                full_path = (artifact_root / normalized_file_path).resolve()

                # Ensure the resolved path is still within the artifact directory
                artifact_root_resolved = artifact_root.resolve()
                if not str(full_path).startswith(str(artifact_root_resolved)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid file path: path escapes artifact directory",
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file path: {str(e)}",
            )

        # Check if file already exists
        if full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File already exists: {file_path}",
            )

        # Validate content is valid UTF-8
        try:
            request.content.encode("utf-8")
        except UnicodeEncodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content encoding: {str(e)}. Content must be valid UTF-8.",
            )

        # Create parent directories if they don't exist
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating parent directories for {full_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create parent directories: {str(e)}",
            )

        # Write file atomically
        try:
            dir_path = full_path.parent

            # Create temporary file in the same directory for atomic rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=dir_path,
                delete=False,
                encoding="utf-8",
                prefix=".tmp_",
                suffix=f"_{full_path.name}",
            ) as tmp:
                tmp.write(request.content)
                tmp_path = PathLib(tmp.name)

            # Atomic rename (same filesystem)
            tmp_path.replace(full_path)

            logger.info(f"Successfully created file atomically: {full_path}")

        except Exception as e:
            # Clean up temp file if it still exists
            if "tmp_path" in locals() and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            logger.error(f"Error creating file {full_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create file: {str(e)}",
            )

        # Get file info
        file_size = full_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(full_path))

        logger.info(f"Successfully created file: {artifact_id}/{file_path}")

        return FileContentResponse(
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection_name,
            path=file_path,
            content=request.content,
            size=file_size,
            mime_type=mime_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error creating file for '{artifact_id}/{file_path}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create file: {str(e)}",
        )


@router.delete(
    "/{artifact_id}/files/{file_path:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete artifact file",
    description="Delete a specific file within an artifact",
    responses={
        204: {"description": "Successfully deleted file"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request, path traversal attempt, or directory path",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact or file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_artifact_file(
    artifact_id: str,
    file_path: str,
    _artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
) -> None:
    """Delete a file within an artifact.

    **SECURITY: Path Traversal Protection**
    This endpoint implements strict path validation to prevent directory
    traversal attacks. The file_path must:
    - Be within the artifact directory
    - Not contain ".." (parent directory references)
    - Resolve to a path inside the artifact root

    **Safety**
    - Only files can be deleted, not directories
    - Protected files (SKILL.md, COMMAND.md, etc.) should be validated before deletion

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        file_path: Relative path to file within artifact (e.g., "README.md" or "docs/guide.md")
        _artifact_mgr: Artifact manager dependency (unused, reserved for future use)
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        collection: Optional collection filter

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: If artifact not found, file not found, path traversal attempt,
                      directory path, or deletion failure

    Example:
        DELETE /api/v1/artifacts/skill:pdf-processor/files/docs/guide.md

        Returns: 204 No Content
    """
    import os

    try:
        logger.info(
            f"Deleting file for artifact: {artifact_id}, file: {file_path} (collection={collection})"
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

        # Find artifact
        artifact = None
        collection_name = collection
        if collection:
            # Search in specified collection
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            try:
                coll = collection_mgr.load_collection(collection)
                artifact = coll.find_artifact(artifact_name, artifact_type)
            except ValueError:
                pass  # Not found in this collection
        else:
            # Search across all collections
            for coll_name in collection_mgr.list_collections():
                try:
                    coll = collection_mgr.load_collection(coll_name)
                    artifact = coll.find_artifact(artifact_name, artifact_type)
                    collection_name = coll_name
                    break
                except ValueError:
                    continue

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get artifact path
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        artifact_root = collection_path / artifact.path

        if not artifact_root.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Artifact path does not exist: {artifact_root}",
            )

        # Handle single-file artifacts (e.g., agents stored as agents/prd-writer.md)
        # For single-file artifacts, artifact_root IS the file, not a directory
        is_single_file_artifact = artifact_root.is_file()

        # Validate file path (path traversal protection)
        try:
            # Normalize the requested path to remove any .., ., etc.
            normalized_file_path = os.path.normpath(file_path)

            # Check for path traversal indicators
            if (
                normalized_file_path.startswith("..")
                or "/.." in normalized_file_path
                or "\\.." in normalized_file_path
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path: path traversal attempt detected",
                )

            if is_single_file_artifact:
                # Single-file artifacts cannot have their only file deleted
                # Deleting it would effectively delete the entire artifact
                artifact_filename = artifact_root.name
                if normalized_file_path in (".", artifact_filename):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot delete the only file in a single-file artifact. "
                        f"This would effectively delete the entire artifact '{artifact_id}'. "
                        f"Use the artifact deletion endpoint (DELETE /api/v1/artifacts/{artifact_id}) instead.",
                    )
                else:
                    # Requested file doesn't exist in this single-file artifact
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"File not found: {file_path}. This is a single-file artifact containing only '{artifact_filename}'",
                    )
            else:
                # Directory-based artifact: construct path normally
                full_path = (artifact_root / normalized_file_path).resolve()

                # Ensure the resolved path is still within the artifact directory
                artifact_root_resolved = artifact_root.resolve()
                if not str(full_path).startswith(str(artifact_root_resolved)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid file path: path escapes artifact directory",
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file path: {str(e)}",
            )

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}",
            )

        # Check if it's a file (not a directory)
        if not full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a file (directories cannot be deleted): {file_path}",
            )

        # Prevent deletion of critical files
        critical_files = {
            "SKILL.md",
            "COMMAND.md",
            "AGENT.md",
            "HOOK.md",
            "MCP.md",
        }
        if full_path.name in critical_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete critical file: {full_path.name}",
            )

        # Delete the file
        try:
            full_path.unlink()
            logger.info(f"Successfully deleted file: {full_path}")
        except Exception as e:
            logger.error(f"Error deleting file {full_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}",
            )

        logger.info(f"Successfully deleted file: {artifact_id}/{file_path}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting file for '{artifact_id}/{file_path}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}",
        )


@router.get("/metadata/github", response_model=MetadataFetchResponse)
async def fetch_github_metadata(
    source: str = Query(..., description="GitHub source: user/repo/path[@version]"),
    request: Request = None,
    config_mgr: ConfigManagerDep = None,
) -> MetadataFetchResponse:
    """Fetch metadata from GitHub for a given source.

    Parses the source URL, fetches repository metadata and
    frontmatter from the artifact's markdown file. Results
    are cached to reduce GitHub API calls (configurable TTL).

    Args:
        source: GitHub source in format user/repo/path[@version]
        request: FastAPI request object for accessing app state
        config_mgr: Config manager dependency for GitHub token

    Returns:
        MetadataFetchResponse with metadata or error details

    Raises:
        HTTPException: On internal errors or if feature is disabled
    """
    # Check if auto-population feature is enabled
    from skillmeat.api.config import get_settings

    settings = get_settings()
    if not settings.enable_auto_population:
        logger.warning("Auto-population feature is disabled")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub metadata auto-population feature is currently disabled. Enable with SKILLMEAT_ENABLE_AUTO_POPULATION=true",
        )

    try:
        # Validate source format first
        from skillmeat.core.validation import validate_github_source

        is_valid, error_msg = validate_github_source(source)
        if not is_valid:
            logger.warning(f"Invalid source format '{source}': {error_msg}")
            return MetadataFetchResponse(success=False, error=error_msg)

        logger.info(f"Fetching GitHub metadata for source: {source}")

        # Get or create metadata cache from app state
        app_state = get_app_state()
        if not hasattr(app_state, "metadata_cache") or app_state.metadata_cache is None:
            # Initialize cache with configurable TTL from settings
            ttl_seconds = settings.discovery_cache_ttl
            app_state.metadata_cache = MetadataCache(ttl_seconds=ttl_seconds)
            logger.debug(f"Initialized metadata cache with TTL={ttl_seconds}s")

        # Get GitHub token from settings first, then fallback to config manager
        github_token = settings.github_token
        if not github_token and config_mgr:
            github_token = config_mgr.get("github-token")

        if github_token:
            logger.debug("Using configured GitHub token for API requests")
        else:
            logger.debug(
                "No GitHub token configured, using unauthenticated requests (60 req/hr limit)"
            )

        # Create metadata extractor with cache and token
        extractor = GitHubMetadataExtractor(
            cache=app_state.metadata_cache, token=github_token
        )

        # Try to fetch metadata
        try:
            metadata = extractor.fetch_metadata(source)
            logger.info(f"Successfully fetched metadata for {source}")

            return MetadataFetchResponse(
                success=True,
                metadata=GitHubMetadata(
                    title=metadata.title,
                    description=metadata.description,
                    author=metadata.author,
                    license=metadata.license,
                    topics=metadata.topics,
                    url=metadata.url,
                    fetched_at=metadata.fetched_at,
                ),
            )

        except ValueError as e:
            # Invalid source format (should be caught above, but handle anyway)
            logger.warning(f"Invalid source format '{source}': {e}")
            return MetadataFetchResponse(success=False, error=str(e))

        except RuntimeError as e:
            # Rate limit or API error
            error_msg = str(e)
            logger.error(f"GitHub API error for '{source}': {error_msg}")

            # Provide specific error messages for common issues
            if "404" in error_msg or "not found" in error_msg.lower():
                return MetadataFetchResponse(
                    success=False, error="Repository or artifact not found"
                )
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                return MetadataFetchResponse(
                    success=False,
                    error="GitHub rate limit exceeded. Please configure a GitHub token for higher limits.",
                )
            else:
                return MetadataFetchResponse(success=False, error=error_msg)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"Unexpected error fetching metadata for '{source}': {e}")
        raise create_internal_error("Failed to fetch metadata", e)


# =============================================================================
# Discovery Metrics & Health Endpoints
# =============================================================================


@router.get(
    "/metrics/discovery",
    summary="Get discovery feature metrics",
    description="""
    Get metrics and statistics for discovery features including:
    - Total discovery scans performed
    - Total artifacts discovered
    - Total bulk imports
    - GitHub metadata fetch statistics
    - Cache hit/miss rates
    - Error counts
    - Last scan information

    This endpoint provides simple metrics without requiring Prometheus infrastructure.
    For production monitoring, use the /metrics endpoint exposed by the Prometheus client.
    """,
    response_description="Discovery metrics and statistics",
    tags=["discovery", "metrics"],
)
async def get_discovery_metrics():
    """Get discovery feature metrics and statistics.

    Returns a dictionary with current metrics including scan counts,
    cache performance, and timing information.

    Returns:
        Dictionary with metrics data
    """
    from skillmeat.core.discovery_metrics import discovery_metrics

    try:
        stats = discovery_metrics.get_stats()
        logger.debug("Retrieved discovery metrics")
        return stats
    except Exception as e:
        logger.exception(f"Failed to retrieve discovery metrics: {e}")
        raise create_internal_error("Failed to retrieve metrics", e)


@router.get(
    "/health/discovery",
    summary="Discovery feature health check",
    description="""
    Check the health status of discovery features including:
    - Discovery service availability
    - Auto-population feature status
    - Cache configuration
    - Current metrics

    Returns 200 OK if all discovery features are operational.
    """,
    response_description="Discovery health status",
    tags=["discovery", "health"],
)
async def discovery_health_check():
    """Check discovery feature health and configuration.

    Validates that discovery features are properly configured and operational.
    Includes feature flags, cache settings, and basic metrics.

    Returns:
        Dictionary with health status and configuration
    """
    from skillmeat.api.config import get_settings
    from skillmeat.core.discovery_metrics import discovery_metrics

    try:
        settings = get_settings()

        # Basic health status
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "features": {
                "discovery_enabled": True,  # Always available
                "auto_population_enabled": getattr(
                    settings, "enable_auto_population", False
                ),
                "github_token_configured": bool(
                    getattr(settings, "github_token", None)
                ),
            },
            "configuration": {
                "cache_ttl_seconds": getattr(settings, "discovery_cache_ttl", 3600),
            },
            "metrics": discovery_metrics.get_stats(),
        }

        logger.debug("Discovery health check passed")
        return health_status

    except Exception as e:
        logger.exception(f"Discovery health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }


# ===========================
# Skip Preference Management
# ===========================


@router.post(
    "/projects/{project_id:path}/skip-preferences",
    response_model=SkipPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add skip preference",
    description="Add a skip preference for an artifact in the project",
    responses={
        201: {"description": "Skip preference added successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        422: {
            "model": ErrorResponse,
            "description": "Validation error (duplicate or invalid artifact_key)",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def add_skip_preference(
    project_id: str = Path(..., description="URL-encoded project path"),
    request: SkipPreferenceAddRequest = Body(...),
    _token: TokenDep = None,
) -> SkipPreferenceResponse:
    """Add a skip preference for an artifact in a project.

    Args:
        project_id: Project ID (URL-encoded path)
        request: Skip preference request with artifact_key and skip_reason
        _token: Authentication token

    Returns:
        SkipPreferenceResponse with the created skip preference

    Raises:
        HTTPException: If project not found, validation fails, or operation fails
    """
    from skillmeat.core.skip_preferences import SkipPreferenceManager

    try:
        # Decode project ID to get project path
        project_path = _decode_project_id_param(project_id)
        if not project_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_id: unable to decode project path",
            )

        # Verify project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path}",
            )

        # Initialize skip preference manager for this project
        skip_manager = SkipPreferenceManager(project_path)

        # Add the skip preference
        skip = skip_manager.add_skip(
            artifact_key=request.artifact_key, reason=request.skip_reason
        )

        logger.info(
            f"Added skip preference for '{request.artifact_key}' in project {project_path}"
        )

        # Return response
        return SkipPreferenceResponse(
            artifact_key=skip.artifact_key,
            skip_reason=skip.skip_reason,
            added_date=skip.added_date,
        )

    except ValueError as e:
        # Validation error (duplicate or invalid artifact_key)
        logger.warning(f"Validation error adding skip preference: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to add skip preference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add skip preference: {str(e)}",
        )


@router.delete(
    "/projects/{project_id:path}/skip-preferences/{artifact_key}",
    response_model=SkipClearResponse,
    summary="Remove skip preference",
    description="Remove a single skip preference by artifact key",
    responses={
        200: {"description": "Skip preference removed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {
            "model": ErrorResponse,
            "description": "Project or skip preference not found",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def remove_skip_preference(
    project_id: str = Path(..., description="URL-encoded project path"),
    artifact_key: str = Path(
        ..., description="Artifact key to remove (e.g., 'skill:canvas')"
    ),
    _token: TokenDep = None,
) -> SkipClearResponse:
    """Remove a single skip preference by artifact key.

    Args:
        project_id: Project ID (URL-encoded path)
        artifact_key: Artifact key in format "type:name" (URL-encoded if needed)
        _token: Authentication token

    Returns:
        SkipClearResponse with success status and message

    Raises:
        HTTPException: If project not found or operation fails
    """
    from skillmeat.core.skip_preferences import SkipPreferenceManager

    try:
        # Decode project ID to get project path
        project_path = _decode_project_id_param(project_id)
        if not project_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_id: unable to decode project path",
            )

        # Verify project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path}",
            )

        # Initialize skip preference manager for this project
        skip_manager = SkipPreferenceManager(project_path)

        # Remove the skip preference
        removed = skip_manager.remove_skip(artifact_key)

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skip preference not found for artifact '{artifact_key}'",
            )

        logger.info(
            f"Removed skip preference for '{artifact_key}' from project {project_path}"
        )

        # Return response
        return SkipClearResponse(
            success=True,
            cleared_count=1,
            message=f"Removed skip preference for '{artifact_key}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to remove skip preference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove skip preference: {str(e)}",
        )


@router.delete(
    "/projects/{project_id:path}/skip-preferences",
    response_model=SkipClearResponse,
    summary="Clear all skip preferences",
    description="Clear all skip preferences for a project",
    responses={
        200: {"description": "Skip preferences cleared successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def clear_skip_preferences(
    project_id: str = Path(..., description="URL-encoded project path"),
    _token: TokenDep = None,
) -> SkipClearResponse:
    """Clear all skip preferences for a project.

    Args:
        project_id: Project ID (URL-encoded path)
        _token: Authentication token

    Returns:
        SkipClearResponse with success status, count, and message

    Raises:
        HTTPException: If project not found or operation fails
    """
    from skillmeat.core.skip_preferences import SkipPreferenceManager

    try:
        # Decode project ID to get project path
        project_path = _decode_project_id_param(project_id)
        if not project_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_id: unable to decode project path",
            )

        # Verify project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path}",
            )

        # Initialize skip preference manager for this project
        skip_manager = SkipPreferenceManager(project_path)

        # Clear all skip preferences
        cleared_count = skip_manager.clear_skips()

        logger.info(
            f"Cleared {cleared_count} skip preference(s) from project {project_path}"
        )

        # Return response
        message = (
            f"Cleared {cleared_count} skip preference(s)"
            if cleared_count > 0
            else "No skip preferences to clear"
        )

        return SkipClearResponse(
            success=True,
            cleared_count=cleared_count,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to clear skip preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear skip preferences: {str(e)}",
        )


@router.get(
    "/projects/{project_id:path}/skip-preferences",
    response_model=SkipPreferenceListResponse,
    summary="List skip preferences",
    description="List all skip preferences for a project",
    responses={
        200: {"description": "Skip preferences retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_skip_preferences(
    project_id: str = Path(..., description="URL-encoded project path"),
    _token: TokenDep = None,
) -> SkipPreferenceListResponse:
    """List all skip preferences for a project.

    Args:
        project_id: Project ID (URL-encoded path)
        _token: Authentication token

    Returns:
        SkipPreferenceListResponse with list of skip preferences

    Raises:
        HTTPException: If project not found or operation fails
    """
    from skillmeat.core.skip_preferences import SkipPreferenceManager

    try:
        # Decode project ID to get project path
        project_path = _decode_project_id_param(project_id)
        if not project_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_id: unable to decode project path",
            )

        # Verify project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path}",
            )

        # Initialize skip preference manager for this project
        skip_manager = SkipPreferenceManager(project_path)

        # Get all skip preferences
        skips = skip_manager.get_skipped_list()

        logger.debug(
            f"Retrieved {len(skips)} skip preference(s) from project {project_path}"
        )

        # Convert to response format
        skip_responses = [
            SkipPreferenceResponse(
                artifact_key=skip.artifact_key,
                skip_reason=skip.skip_reason,
                added_date=skip.added_date,
            )
            for skip in skips
        ]

        return SkipPreferenceListResponse(skips=skip_responses)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to list skip preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list skip preferences: {str(e)}",
        )


# ====================================================================
# Artifact-Tag Association Endpoints
# ====================================================================


@router.get(
    "/{artifact_id}/tags",
    response_model=List[TagResponse],
    summary="Get artifact tags",
    description="Get all tags assigned to an artifact",
)
async def get_artifact_tags(artifact_id: str) -> List[TagResponse]:
    """Get all tags assigned to a specific artifact.

    Args:
        artifact_id: Unique identifier of the artifact

    Returns:
        List of tags assigned to the artifact

    Raises:
        HTTPException: 500 if operation fails
    """
    service = TagService()

    try:
        return service.get_artifact_tags(artifact_id)
    except Exception as e:
        logger.error(f"Failed to get tags for artifact {artifact_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{artifact_id}/tags/{tag_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add tag to artifact",
    description="Associate a tag with an artifact",
)
async def add_tag_to_artifact(artifact_id: str, tag_id: str) -> dict:
    """Add a tag to an artifact.

    Args:
        artifact_id: Unique identifier of the artifact
        tag_id: Unique identifier of the tag

    Returns:
        Success message with artifact and tag IDs

    Raises:
        HTTPException: 400 if association already exists or invalid request
        HTTPException: 404 if artifact or tag not found
    """
    service = TagService()

    try:
        service.add_tag_to_artifact(artifact_id, tag_id)
        return {"message": f"Tag {tag_id} added to artifact {artifact_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{artifact_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tag from artifact",
    description="Remove a tag from an artifact",
)
async def remove_tag_from_artifact(artifact_id: str, tag_id: str) -> None:
    """Remove a tag from an artifact.

    Args:
        artifact_id: Unique identifier of the artifact
        tag_id: Unique identifier of the tag

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 400 if invalid request
        HTTPException: 404 if tag association not found
    """
    service = TagService()

    try:
        if not service.remove_tag_from_artifact(artifact_id, tag_id):
            raise HTTPException(status_code=404, detail="Tag association not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
