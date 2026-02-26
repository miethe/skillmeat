"""Artifact management API endpoints.

Provides REST API for managing artifacts within collections.
"""

import base64
import difflib
import hashlib
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path as PathLib
from typing import Annotated, Dict, Iterator, List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    CollectionManagerDep,
    ConfigManagerDep,
    SettingsDep,
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
    ArtifactTagsUpdate,
    ArtifactUpdateRequest,
    ArtifactUpstreamDiffResponse,
    ArtifactUpstreamInfo,
    ArtifactUpstreamResponse,
    ArtifactVersionInfo,
    ConflictInfo,
    ConsolidationActionRequest,
    ConsolidationActionResponse,
    ConsolidationClustersResponse,
    CreateLinkedArtifactRequest,
    DeploymentStatistics,
    FileDiff,
    FileContentResponse,
    FileListResponse,
    FileNode,
    FileUpdateRequest,
    LinkedArtifactReferenceSchema,
    MergeDeployDetails,
    MergeFileAction,
    ProjectDeploymentInfo,
    SimilarArtifactDTO,
    SimilarArtifactsResponse,
    SimilarityBreakdownDTO,
    SimilarityClusterDTO,
    VersionGraphNodeResponse,
    VersionGraphResponse,
)
from skillmeat.api.schemas.associations import AssociationItemDTO, AssociationsDTO
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
from skillmeat.api.utils.upstream_cache import get_upstream_cache
from skillmeat.core.artifact import ArtifactType, LinkedArtifactReference
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
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash
from sqlalchemy import func
from skillmeat.api.services import (
    CollectionService,
    delete_artifact_cache,
    refresh_single_artifact_cache,
)
from skillmeat.api.services.artifact_cache_service import (
    add_deployment_to_cache,
    parse_deployments,
)
from skillmeat.api.schemas.deployments import DeploymentSummary
from skillmeat.cache.composite_repository import CompositeMembershipRepository
from skillmeat.cache.models import (
    Artifact,
    Collection,
    CollectionArtifact,
    CompositeArtifact,
    MarketplaceCatalogEntry,
    get_session,
)
from skillmeat.cache.repositories import MarketplaceCatalogRepository
from skillmeat.observability.timing import PerfTimer

logger = logging.getLogger(__name__)

# Exclusion patterns for diff operations - skip non-content directories
DIFF_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
}


def iter_artifact_files(
    base_path: PathLib, exclude_dirs: Optional[set[str]] = None
) -> Iterator[PathLib]:
    """Iterate artifact files, excluding specified directories.

    Filters out directories like node_modules, .git, __pycache__, etc. that would
    cause significant performance degradation during diff operations.

    Args:
        base_path: Root path to iterate
        exclude_dirs: Set of directory names to exclude (defaults to DIFF_EXCLUDE_DIRS)
    """
    exclusions = exclude_dirs or DIFF_EXCLUDE_DIRS
    for f in base_path.rglob("*"):
        if f.is_file():
            # Skip if any parent directory is in exclusion list
            if not any(part in exclusions for part in f.relative_to(base_path).parts):
                yield f


def _normalize_artifact_path(path_str: str) -> str:
    """Normalize artifact path by removing duplicate extensions.

    Detects and fixes double extensions like .md.md, .txt.txt, etc.

    Args:
        path_str: Artifact path from manifest

    Returns:
        Normalized path with duplicate extensions removed
    """
    from pathlib import Path

    path = Path(path_str)
    stem = path.stem
    suffix = path.suffix

    # Check if the filename has duplicate extension (e.g., "file.md.md")
    # path.stem would be "file.md" and suffix would be ".md"
    # So we check if stem ends with suffix (without the dot)
    if suffix:
        # Remove the leading dot from suffix for comparison
        suffix_no_dot = suffix[1:]
        # Check if stem ends with the same extension
        if stem.endswith(f".{suffix_no_dot}"):
            # Build normalized path: parent / stem (which already has one extension)
            # stem already includes the extension once, so we don't add suffix again
            normalized = str(Path(path.parent) / stem)
            logger.warning(
                f"Normalized artifact path with duplicate extension: {path_str} -> {normalized}"
            )
            return normalized

    return path_str


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


def _get_possible_artifact_paths(artifact_type: ArtifactType, name: str) -> List[str]:
    """Get possible project paths for an artifact without deployment record.

    When an artifact exists in a project but has no deployment record (e.g.,
    manually deployed or deployed before tracking was implemented), this
    function returns candidate paths based on artifact type conventions.

    Args:
        artifact_type: The type of artifact (skill, command, agent, etc.)
        name: The artifact name

    Returns:
        List of possible relative paths within .claude/ directory, ordered by
        likelihood. The first matching path should be used.
    """
    type_val = artifact_type.value
    paths: List[str] = []

    if type_val == "skill":
        paths = [f"skills/{name}"]
    elif type_val == "command":
        paths = [f"commands/{name}"]
    elif type_val == "agent":
        # Agents can be single files or directories
        paths = [
            f"agents/{name}.md",
            f"agents/{name}",
            f"agents/pm/{name}.md",
            f"agents/dev/{name}.md",
        ]
    elif type_val == "hook":
        paths = [f"hooks/{name}"]
    elif type_val == "mcp":
        paths = [f"mcp/{name}"]

    return paths


# Common file extensions that may be incorrectly included in artifact IDs
_ARTIFACT_ID_EXTENSIONS = (".md", ".txt", ".json", ".yaml", ".yml")


def parse_artifact_id(artifact_id: str) -> tuple[str, str]:
    """Parse artifact_id into (type, name), normalizing the name.

    Handles cases where the frontend sends artifact IDs with file extensions
    (e.g., 'agent:prd-writer.md' instead of 'agent:prd-writer').

    Args:
        artifact_id: The artifact identifier in 'type:name' format

    Returns:
        Tuple of (artifact_type_str, artifact_name) with normalized name

    Raises:
        ValueError: If artifact_id is not in 'type:name' format
    """
    if ":" not in artifact_id:
        raise ValueError("Invalid artifact ID format. Expected 'type:name'")

    artifact_type_str, artifact_name = artifact_id.split(":", 1)

    # Strip common file extensions that may be incorrectly included
    original_name = artifact_name
    for ext in _ARTIFACT_ID_EXTENSIONS:
        if artifact_name.endswith(ext):
            artifact_name = artifact_name[: -len(ext)]
            logger.warning(
                f"Stripped extension from artifact ID: '{original_name}' -> '{artifact_name}'"
            )
            break

    return artifact_type_str, artifact_name


router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


def get_db_session():
    """Dependency that provides a database session.

    Yields:
        Session: SQLAlchemy database session
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_db_session)]


def resolve_collection_name(
    collection_param: str,
    collection_mgr,
    db_session=None,
) -> Optional[str]:
    """Resolve a collection parameter to a collection name.

    Accepts either a collection name or UUID. If a UUID is provided,
    looks up the name from the database.

    Args:
        collection_param: Collection name or UUID string
        collection_mgr: CollectionManager instance
        db_session: Optional SQLAlchemy session. If None, creates one internally.

    Returns:
        The collection name if found, None if not resolvable.
    """
    # Fast path: check as a name first
    collection_names = collection_mgr.list_collections()
    if collection_param in collection_names:
        return collection_param

    # Try as a UUID - look up in DB
    owns_session = db_session is None
    if owns_session:
        db_session = get_session()
    try:
        collection_record = (
            db_session.query(Collection)
            .filter(Collection.id == collection_param)
            .first()
        )
        if collection_record:
            # Case-insensitive match: compare lowercase versions
            collection_names_lower = {name.lower(): name for name in collection_names}
            db_name_lower = collection_record.name.lower()

            if db_name_lower in collection_names_lower:
                # Return the filesystem name (preserves original case)
                filesystem_name = collection_names_lower[db_name_lower]
                logger.warning(
                    "Resolved collection UUID '%s' to name '%s' (DB: '%s', filesystem: '%s'). "
                    "Frontend should send collection name instead of UUID.",
                    collection_param,
                    filesystem_name,
                    collection_record.name,
                    filesystem_name,
                )
                return filesystem_name
    finally:
        if owns_session:
            db_session.close()

    return None


def _find_artifact_in_collections(
    artifact_name: str,
    artifact_type: ArtifactType,
    collection_mgr,
    preferred_collection: Optional[str] = None,
    db_session=None,
) -> tuple:
    """Find an artifact across collections, with optional preferred collection hint.

    When a preferred collection is specified (name or UUID), searches there first.
    If the artifact is not found in the preferred collection (e.g., stale DB
    association), falls back to searching all collections.

    This prevents 404 errors caused by the frontend sending a collection UUID
    from a stale DB association while the artifact actually lives in a different
    collection on the filesystem.

    Args:
        artifact_name: Normalized artifact name (extension already stripped)
        artifact_type: Artifact type enum
        collection_mgr: CollectionManager instance
        preferred_collection: Optional collection name or UUID to search first
        db_session: Optional SQLAlchemy session for UUID resolution

    Returns:
        Tuple of (artifact, collection_name) where collection_name is the
        filesystem collection name. Returns (None, None) if not found anywhere.
    """
    # If a preferred collection is specified, try it first
    if preferred_collection:
        resolved = resolve_collection_name(
            preferred_collection, collection_mgr, db_session=db_session
        )
        if resolved:
            try:
                coll = collection_mgr.load_collection(resolved)
                artifact = coll.find_artifact(artifact_name, artifact_type)
                if artifact:
                    return artifact, resolved
            except ValueError:
                pass  # Collection load or ambiguous name error
            # Artifact not found in preferred collection - fall through to search all
            logger.warning(
                "Artifact '%s:%s' not found in preferred collection '%s' "
                "(resolved from '%s'). Falling back to searching all collections.",
                artifact_type.value,
                artifact_name,
                resolved,
                preferred_collection,
            )

    # Search across all collections
    for coll_name in collection_mgr.list_collections():
        try:
            coll = collection_mgr.load_collection(coll_name)
            artifact = coll.find_artifact(artifact_name, artifact_type)
            if artifact:
                return artifact, coll_name
        except ValueError:
            continue

    return None, None


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
        Uses DeploymentStatsCache for performance optimization.
    """
    from skillmeat.api.routers.projects import discover_projects
    from skillmeat.cache.deployment_stats_cache import get_deployment_stats_cache

    cache = get_deployment_stats_cache()

    # Fast path: full cache hit
    cached = cache.get_stats(artifact_name, artifact_type.value)
    if cached is not None:
        return cached

    # Medium path: reuse cached project discovery
    project_paths = cache.get_discovered_projects()
    if project_paths is None:
        project_paths = discover_projects()
        cache.set_discovered_projects(project_paths)

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

    result = DeploymentStatistics(
        total_deployments=total_deployments,
        modified_deployments=modified_deployments,
        projects=projects_info,
    )
    cache.set_stats(artifact_name, artifact_type.value, result)
    return result


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
    collections_data: Optional[List[ArtifactCollectionInfo]] = None,
    db_source: Optional[str] = None,
    deployments: Optional[List[DeploymentSummary]] = None,
    db_uuid: Optional[str] = None,
) -> ArtifactResponse:
    """Convert Artifact model to API response schema.

    Args:
        artifact: Artifact instance
        drift_status: Optional drift status ("none", "modified", "deleted", "added")
        has_local_modifications: Optional flag indicating local modifications
        collections_data: Optional list of ArtifactCollectionInfo from CollectionService
        db_source: Optional source from DB cache (overrides filesystem source)
        db_uuid: Optional UUID from DB cache (used when artifact.uuid is None)

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
            dependencies=artifact.metadata.dependencies,
            tools=(
                [tool.value for tool in artifact.metadata.tools]
                if artifact.metadata.tools
                else []
            ),
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

    # Convert collections from passed data (from CollectionService)
    collections_response = collections_data or []

    # Resolve UUID: prefer artifact.uuid, then db_uuid, then generate deterministic fallback
    artifact_uuid = artifact.uuid or db_uuid
    if not artifact_uuid:
        # Deterministic fallback based on type:name (should rarely happen)
        fallback_input = f"{artifact.type.value}:{artifact.name}"
        artifact_uuid = hashlib.md5(fallback_input.encode()).hexdigest()

    return ArtifactResponse(
        id=f"{artifact.type.value}:{artifact.name}",
        uuid=artifact_uuid,
        name=artifact.name,
        type=artifact.type.value,
        source=db_source or (artifact.upstream if artifact.upstream else "local"),
        origin=artifact.origin,
        origin_source=artifact.origin_source,
        version=version,
        aliases=[],  # TODO: Add alias support when implemented
        tags=artifact.tags or [],
        target_platforms=artifact.target_platforms,
        metadata=metadata_response,
        upstream=upstream_response,
        collections=collections_response,
        deployments=deployments,
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
    session: Session = Depends(get_session),
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
                target_platforms=(
                    [platform.value for platform in a.target_platforms]
                    if a.target_platforms is not None
                    else None
                ),
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

                            # Also record deployments in DB cache for UI visibility
                            for artifact_payload, import_result in zip(
                                request.artifacts, results
                            ):
                                if import_result.status != ImportStatus.SUCCESS:
                                    continue

                                artifact_name = artifact_payload.name or (
                                    PathLib(artifact_payload.path).stem
                                    if artifact_payload.path
                                    else None
                                )
                                if not artifact_name:
                                    continue

                                artifact_id = (
                                    f"{artifact_payload.artifact_type}:{artifact_name}"
                                )

                                try:
                                    add_deployment_to_cache(
                                        session=session,
                                        artifact_id=artifact_id,
                                        project_path=str(project_path),
                                        project_name=project_path.name,
                                        deployed_at=datetime.now(timezone.utc),
                                        content_hash=(
                                            compute_content_hash(
                                                PathLib(artifact_payload.path)
                                            )
                                            if artifact_payload.path
                                            else None
                                        ),
                                        local_modifications=False,
                                        collection_id=collection_name,
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to record deployment in cache for {artifact_id}: {e}"
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

        # Determine collection - use default if not specified
        collection_name = request.collection
        if not collection_name:
            # Use the default collection
            collection_name = "default"
            # Verify default collection exists (should always exist after server startup)
            collections = collection_mgr.list_collections()
            if "default" not in collections:
                # Fall back to first available if default doesn't exist (shouldn't happen)
                if collections:
                    collection_name = collections[0]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No collections found. Create a collection first.",
                    )
        else:
            # Verify collection exists (resolve UUID if needed)
            resolved = resolve_collection_name(collection_name, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection_name}' not found",
                )
            collection_name = resolved

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
                    target_platforms=request.target_platforms,
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
                    target_platforms=request.target_platforms,
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

        # Refresh DB cache after successful create (non-blocking)
        artifact_id = f"{artifact.type.value}:{artifact.name}"
        try:
            db_session = get_session()
            try:
                refresh_single_artifact_cache(
                    db_session, artifact_mgr, artifact_id, collection_name
                )
            finally:
                db_session.close()
        except Exception as cache_err:
            logger.warning(f"Cache refresh failed for {artifact_id}: {cache_err}")

        return ArtifactCreateResponse(
            success=True,
            artifact_id=artifact_id,
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
        description="Filter by artifact type (skill, command, agent). Supports comma-separated values (e.g., skill,command,agent).",
    ),
    collection: Optional[str] = Query(
        default=None,
        description="Filter by collection name",
    ),
    tags: Optional[str] = Query(
        default=None,
        description="Filter by tags (comma-separated)",
    ),
    tools: Optional[str] = Query(
        default=None,
        description="Filter by tools (comma-separated). Returns artifacts that use any of the specified tools.",
    ),
    check_drift: bool = Query(
        default=False,
        description="Check for local modifications and drift status (may impact performance)",
    ),
    project_path: Optional[str] = Query(
        default=None,
        description="Project path for drift detection (required if check_drift=true)",
    ),
    has_unlinked: Optional[bool] = Query(
        default=None,
        description="Filter for artifacts with unlinked references (true) or without (false)",
    ),
    import_id: Optional[str] = Query(
        default=None,
        description="Filter by marketplace import batch ID",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search artifacts by name or description (case-insensitive substring match)",
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
        artifact_type: Optional type filter (comma-separated for multiple types)
        collection: Optional collection filter
        tags: Optional tag filter (comma-separated)
        tools: Optional tools filter (comma-separated)
        check_drift: Whether to check for drift and local modifications
        project_path: Project path for drift detection
        has_unlinked: Filter for artifacts with/without unlinked references
        import_id: Filter by marketplace import batch ID
        search: Optional search string (case-insensitive match on name/description)

    Returns:
        Paginated list of artifacts

    Raises:
        HTTPException: On error
    """
    try:
        # Start timing for performance monitoring
        start_time = time.perf_counter()

        logger.info(
            f"Listing artifacts (limit={limit}, after={after}, "
            f"type={artifact_type}, collection={collection}, tags={tags}, tools={tools}, "
            f"import_id={import_id}, search={search})"
        )

        # Parse filters
        type_filter = None
        if artifact_type:
            raw_types = [t.strip() for t in artifact_type.split(",") if t.strip()]
            parsed_types = []
            for raw in raw_types:
                try:
                    parsed_types.append(ArtifactType(raw))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid artifact type: {raw}",
                    )
            type_filter = parsed_types if len(parsed_types) > 1 else parsed_types[0]

        tag_filter = None
        if tags:
            tag_filter = [t.strip() for t in tags.split(",") if t.strip()]

        # Get artifacts from specified collection or all collections
        if collection:
            # Check if collection exists (resolve UUID if needed)
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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

        # Filter by tools if specified
        if tools:
            tools_filter = [t.strip().lower() for t in tools.split(",") if t.strip()]
            if tools_filter:
                filtered_artifacts = []
                for artifact in artifacts:
                    if artifact.metadata and artifact.metadata.tools:
                        # Get tool values as lowercase strings for comparison
                        artifact_tools = [
                            (t.value.lower() if hasattr(t, "value") else str(t).lower())
                            for t in artifact.metadata.tools
                        ]
                        # Check if any of the specified tools match
                        if any(tool in artifact_tools for tool in tools_filter):
                            filtered_artifacts.append(artifact)
                artifacts = filtered_artifacts

        # Filter by unlinked references if specified
        if has_unlinked is not None:
            filtered_artifacts = []
            for artifact in artifacts:
                if artifact.metadata and artifact.metadata.unlinked_references:
                    # Has unlinked references (non-empty array)
                    if has_unlinked and len(artifact.metadata.unlinked_references) > 0:
                        filtered_artifacts.append(artifact)
                else:
                    # No unlinked references (empty or None)
                    if not has_unlinked:
                        filtered_artifacts.append(artifact)
            artifacts = filtered_artifacts

        # Filter by import_id if specified
        # import_id is stored on MarketplaceCatalogEntry (not filesystem artifacts),
        # so we query the DB to get artifact names/types from that import batch.
        if import_id:
            try:
                db_session = get_session()
                # Query catalog entries that were imported in this batch
                entries = (
                    db_session.query(
                        MarketplaceCatalogEntry.artifact_type,
                        MarketplaceCatalogEntry.name,
                    )
                    .filter(MarketplaceCatalogEntry.import_id == import_id)
                    .all()
                )
                # Build artifact IDs in "type:name" format
                matching_ids: set[str] = {
                    f"{entry.artifact_type}:{entry.name}" for entry in entries
                }
                db_session.close()
            except Exception as e:
                logger.warning(f"Failed to query import_id from DB: {e}")
                matching_ids = set()
            artifacts = [
                a for a in artifacts if f"{a.type.value}:{a.name}" in matching_ids
            ]

        # Search filter (case-insensitive substring match on name and description)
        if search:
            search_lower = search.lower()
            artifacts = [
                a for a in artifacts
                if search_lower in a.name.lower()
                or (a.metadata.description and search_lower in a.metadata.description.lower())
            ]

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

        # Query database for collection memberships and source metadata
        artifact_ids = [f"{a.type.value}:{a.name}" for a in page_artifacts]
        collections_map: Dict[str, List[ArtifactCollectionInfo]] = {}
        source_lookup: Dict[str, str] = {}
        deployments_lookup: Dict[str, List[DeploymentSummary]] = {}

        if artifact_ids:
            try:
                db_session = get_session()
                collection_service = CollectionService(db_session)
                collections_map = collection_service.get_collection_membership_batch(
                    artifact_ids
                )
                # Query DB source and deployments for artifacts.
                # CollectionArtifact uses artifact_uuid FK; join through Artifact
                # to resolve type:name identifiers (Artifact.id) for the lookup keys.
                db_rows = (
                    db_session.query(
                        Artifact.id,
                        CollectionArtifact.source,
                        CollectionArtifact.deployments_json,
                    )
                    .join(
                        CollectionArtifact,
                        CollectionArtifact.artifact_uuid == Artifact.uuid,
                    )
                    .filter(Artifact.id.in_(artifact_ids))
                    .all()
                )
                for row in db_rows:
                    if row.source is not None:
                        source_lookup[row.id] = row.source
                    parsed = parse_deployments(row.deployments_json)
                    if parsed:
                        deployments_lookup[row.id] = parsed
                db_session.close()
            except Exception as e:
                logger.warning(f"Failed to query collection memberships: {e}")

        # Build uuid lookup from DB cache
        uuid_lookup: dict = {}
        try:
            db_session = get_session()
            db_artifacts = (
                db_session.query(Artifact.type, Artifact.name, Artifact.uuid)
                .filter(
                    Artifact.type.in_([a.type.value for a in page_artifacts]),
                )
                .all()
            )
            for db_art in db_artifacts:
                uuid_lookup[f"{db_art.type}:{db_art.name}"] = db_art.uuid
            db_session.close()
        except Exception as e:
            logger.warning(f"Failed to query uuids from DB: {e}")

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
                    db_source=source_lookup.get(artifact_key),
                    deployments=deployments_lookup.get(artifact_key),
                    db_uuid=uuid_lookup.get(artifact_key),
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

        # Log query performance
        elapsed = time.perf_counter() - start_time
        logger.debug(
            "Artifact list query completed",
            extra={
                "elapsed_ms": round(elapsed * 1000, 2),
                "artifact_count": len(items),
            },
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
    db_session: DbSessionDep,
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
        db_session: Database session dependency
        token: Authentication token
        collection: Optional collection filter
        include_deployments: Whether to include deployment statistics

    Returns:
        Artifact details with optional deployment statistics and collections

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Search for artifact
        artifact = None
        if collection:
            # Search in specified collection (resolve UUID if needed)
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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

        # Fetch collection memberships using CollectionService
        collection_service = CollectionService(db_session)
        collections_data = collection_service.get_collection_membership_single(
            artifact_id
        )

        # Get UUID from DB cache (filesystem artifacts may have uuid=None)
        db_artifact = (
            db_session.query(Artifact)
            .filter(
                Artifact.type == artifact_type.value,
                Artifact.name == artifact_name,
            )
            .first()
        )
        db_uuid = db_artifact.uuid if db_artifact else None

        # Build base response with collections
        response = artifact_to_response(
            artifact, collections_data=collections_data, db_uuid=db_uuid
        )

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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

        # Fetch update information — primary network cost for this endpoint
        with PerfTimer(
            "router.check_artifact_upstream.fetch",
            artifact_id=artifact_id,
            collection=collection_name,
        ):
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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
            # Search in specified collection (resolve UUID if needed)
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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
                artifact.tags = metadata_updates.tags
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

            # Refresh DB cache after successful update (non-blocking)
            try:
                db_session = get_session()
                try:
                    refresh_single_artifact_cache(
                        db_session, artifact_mgr, artifact_id, collection_name
                    )
                finally:
                    db_session.close()
            except Exception as cache_err:
                logger.warning(f"Cache refresh failed for {artifact_id}: {cache_err}")

            # Invalidate upstream fetch cache — cached diff results are now stale
            try:
                get_upstream_cache().invalidate_artifact(artifact_id)
            except Exception:
                pass  # Cache invalidation failure is non-critical
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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
            # Search in specified collection (resolve UUID if needed)
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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
                    from skillmeat.core.services import TagService

                    session = get_session()
                    try:
                        row = (
                            session.query(Artifact.uuid)
                            .filter(Artifact.id == artifact_id)
                            .first()
                        )
                    finally:
                        session.close()

                    if row:
                        TagService().sync_artifact_tags(row[0], pending_tag_sync)
                    else:
                        logger.warning(
                            f"No artifact row found for {artifact_id}, skipping tag sync"
                        )
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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
            # Check specified collection (resolve UUID if needed)
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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

        # Reset any linked marketplace catalog entry status to allow re-import
        # This enables re-importing artifacts that were previously imported then deleted
        try:
            catalog_repo = MarketplaceCatalogRepository()
            catalog_entry = catalog_repo.find_by_artifact_name_and_type(
                name=artifact_name,
                artifact_type=artifact_type_str,
            )
            if catalog_entry:
                reset_result = catalog_repo.reset_import_status(
                    entry_id=catalog_entry.id,
                    source_id=catalog_entry.source_id,
                )
                if reset_result:
                    logger.info(
                        f"Reset catalog entry status for deleted artifact: "
                        f"{artifact_id} (entry_id: {catalog_entry.id})"
                    )
        except Exception as catalog_error:
            # Don't fail deletion if catalog reset fails - just log it
            logger.warning(
                f"Failed to reset catalog entry for deleted artifact {artifact_id}: "
                f"{catalog_error}"
            )

        # Delete DB cache entry after successful artifact deletion (non-blocking)
        try:
            db_session = get_session()
            try:
                delete_artifact_cache(db_session, artifact_id, collection_name)
            finally:
                db_session.close()
        except Exception as cache_err:
            logger.warning(f"Cache deletion failed for {artifact_id}: {cache_err}")

        # Invalidate upstream fetch cache — artifact no longer exists
        try:
            get_upstream_cache().invalidate_artifact(artifact_id)
        except Exception:
            pass  # Cache invalidation failure is non-critical

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
    description=(
        "Deploy artifact from collection to project's .claude/ directory. "
        "Supports 'overwrite' (default) and 'merge' strategies."
    ),
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
    settings: SettingsDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        None, description="Collection name (uses default if not specified)"
    ),
) -> ArtifactDeployResponse:
    """Deploy artifact from collection to project.

    Copies the artifact to the project's .claude/ directory and tracks
    the deployment in .skillmeat-deployed.toml.

    Supports two strategies:
    - 'overwrite' (default): Replace existing deployment entirely.
    - 'merge': File-level merge. New files are copied, project-only files
      are preserved, identical files are skipped, and conflicts (files
      modified on both sides) are reported without overwriting.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        request: Deployment request with project_path, overwrite flag, and strategy
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        Deployment result with optional merge_details when strategy='merge'

    Raises:
        HTTPException: If artifact not found or on error
    """
    try:
        logger.info(
            f"Deploying artifact: {artifact_id} to {request.project_path} "
            f"(collection={collection}, strategy={request.strategy})"
        )

        if request.all_profiles and request.deployment_profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="deployment_profile_id cannot be set when all_profiles=true",
            )

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
            resolved = resolve_collection_name(collection, collection_mgr)
            if not resolved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            collection = resolved
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

        # --- Strategy: merge ---
        if request.strategy == "merge":
            return await _deploy_merge(
                artifact_id=artifact_id,
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                artifact=artifact,
                collection_name=collection_name,
                collection_mgr=collection_mgr,
                artifact_mgr=artifact_mgr,
                project_path=project_path,
                settings=settings,
            )

        # --- Strategy: overwrite (default, existing behavior) ---
        # Create deployment manager
        from skillmeat.core.deployment import (
            DeploymentManager as RuntimeDeploymentManager,
        )

        deployment_mgr = RuntimeDeploymentManager(collection_mgr=collection_mgr)

        # Deploy artifact
        try:
            deployments = deployment_mgr.deploy_artifacts(
                artifact_names=[artifact_name],
                collection_name=collection_name,
                project_path=project_path,
                artifact_type=artifact_type,
                overwrite=request.overwrite,
                profile_id=request.deployment_profile_id,
                all_profiles=request.all_profiles,
            )

            if not deployments:
                # Deployment was skipped (likely user declined overwrite prompt)
                return ArtifactDeployResponse(
                    success=False,
                    message=f"Deployment of '{artifact_name}' was skipped",
                    artifact_name=artifact_name,
                    artifact_type=artifact_type.value,
                    error_message="Deployment cancelled or artifact not found",
                    strategy="overwrite",
                )

            deployment = deployments[0]
            deployed_profiles = sorted(
                {item.deployment_profile_id or "claude_code" for item in deployments}
            )

            # Determine deployed path
            deployed_path = (
                project_path
                / (deployment.profile_root_dir or ".claude")
                / deployment.artifact_path
            )
            logger.info(
                f"Artifact '{artifact_name}' deployed successfully to {deployed_path}"
            )

            # Refresh DB cache after successful deploy (non-blocking)
            _refresh_cache_safe(
                artifact_mgr,
                artifact_id,
                collection_name,
                deployment_profile_id=request.deployment_profile_id,
            )

            # Invalidate upstream fetch cache — project version has changed
            try:
                get_upstream_cache().invalidate_artifact(artifact_id)
            except Exception:
                pass  # Cache invalidation failure is non-critical

            return ArtifactDeployResponse(
                success=True,
                message=f"Artifact '{artifact_name}' deployed successfully",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                deployed_path=str(deployed_path),
                strategy="overwrite",
                deployment_profile_id=deployment.deployment_profile_id,
                deployed_profiles=deployed_profiles,
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
                strategy="overwrite",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying artifact '{artifact_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy artifact: {str(e)}",
        )


def _refresh_cache_safe(
    artifact_mgr,
    artifact_id: str,
    collection_name: str,
    deployment_profile_id: Optional[str] = None,
) -> None:
    """Refresh DB cache after deploy, swallowing errors to avoid failing the deploy."""
    try:
        db_session = get_session()
        try:
            refresh_single_artifact_cache(
                db_session,
                artifact_mgr,
                artifact_id,
                collection_name,
                deployment_profile_id=deployment_profile_id,
            )
        finally:
            db_session.close()
    except Exception as cache_err:
        logger.warning(f"Cache refresh failed for {artifact_id}: {cache_err}")


async def _deploy_merge(
    *,
    artifact_id: str,
    artifact_name: str,
    artifact_type: ArtifactType,
    artifact,
    collection_name: str,
    collection_mgr,
    artifact_mgr,
    project_path: PathLib,
    settings: SettingsDep,
) -> ArtifactDeployResponse:
    """Perform a merge deployment: file-level merge between collection and project.

    Files only in collection (source) are copied to project.
    Files only in project (target) are preserved (not deleted).
    Files in both that are identical are skipped.
    Files in both that differ are reported as conflicts (project version kept).

    Args:
        artifact_id: Artifact identifier string
        artifact_name: Artifact name
        artifact_type: Artifact type enum
        artifact: Artifact object from collection
        collection_name: Name of source collection
        collection_mgr: Collection manager instance
        artifact_mgr: Artifact manager instance
        project_path: Path to the target project directory

    Returns:
        ArtifactDeployResponse with merge_details populated
    """
    # Resolve source path (collection artifact directory)
    collection_path = collection_mgr.config.get_collection_path(collection_name)
    source_path = collection_path / artifact.path

    if not source_path.exists():
        logger.error(f"Collection artifact path missing: {source_path}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection artifact path does not exist: {source_path}",
        )

    # Resolve target path (project deployment directory)
    dest_base = project_path / ".claude"
    if artifact_type == ArtifactType.SKILL:
        target_path = dest_base / "skills" / artifact_name
    elif artifact_type == ArtifactType.COMMAND:
        target_path = dest_base / "commands" / f"{artifact_name}.md"
    elif artifact_type == ArtifactType.AGENT:
        target_path = dest_base / "agents" / f"{artifact_name}.md"
    elif artifact_type == ArtifactType.MCP:
        target_path = dest_base / "mcp" / artifact_name
    elif artifact_type == ArtifactType.HOOK:
        target_path = dest_base / "hooks" / f"{artifact_name}.md"
    elif artifact_type == ArtifactType.COMPOSITE:
        target_path = dest_base / "composites" / artifact_name
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported artifact type for merge: {artifact_type.value}",
        )

    # If target does not exist yet, this is a fresh deploy — copy everything
    if not target_path.exists():
        logger.info(
            f"Merge deploy: target does not exist, performing full copy to {target_path}"
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(
                source_path,
                target_path,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".DS_Store", ".git"
                ),
            )
        else:
            shutil.copy2(source_path, target_path)

        # Count files copied
        if target_path.is_dir():
            copied_files = sorted(
                str(f.relative_to(target_path))
                for f in iter_artifact_files(
                    target_path, set(settings.diff_exclude_dirs)
                )
            )
        else:
            copied_files = [target_path.name]

        file_actions = [
            MergeFileAction(file_path=fp, action="copied") for fp in copied_files
        ]

        _refresh_cache_safe(artifact_mgr, artifact_id, collection_name)

        return ArtifactDeployResponse(
            success=True,
            message=(
                f"Artifact '{artifact_name}' deployed successfully "
                f"(merge, fresh copy of {len(copied_files)} file(s))"
            ),
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            deployed_path=str(target_path),
            strategy="merge",
            merge_details=MergeDeployDetails(
                files_copied=len(copied_files),
                files_skipped=0,
                files_preserved=0,
                conflicts=0,
                file_actions=file_actions,
            ),
        )

    # --- Both source and target exist: perform file-level merge ---
    def _file_hash(file_path: PathLib) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    # Collect relative file paths from source and target
    exclude_dirs = set(settings.diff_exclude_dirs)
    if source_path.is_dir():
        source_files = {
            str(f.relative_to(source_path))
            for f in iter_artifact_files(source_path, exclude_dirs)
        }
    else:
        source_files = {source_path.name}

    if target_path.is_dir():
        target_files = {
            str(f.relative_to(target_path))
            for f in iter_artifact_files(target_path, exclude_dirs)
        }
    else:
        target_files = {target_path.name}

    file_actions: List[MergeFileAction] = []
    files_copied = 0
    files_skipped = 0
    files_preserved = 0
    conflicts = 0

    all_files = sorted(source_files | target_files)

    for rel_path in all_files:
        in_source = rel_path in source_files
        in_target = rel_path in target_files

        if in_source and not in_target:
            # File only in collection — copy to project
            src_file = source_path / rel_path if source_path.is_dir() else source_path
            dst_file = target_path / rel_path if target_path.is_dir() else target_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            file_actions.append(MergeFileAction(file_path=rel_path, action="copied"))
            files_copied += 1

        elif not in_source and in_target:
            # File only in project — preserve (do nothing)
            file_actions.append(
                MergeFileAction(
                    file_path=rel_path,
                    action="preserved",
                    detail="File exists only in project; kept as-is",
                )
            )
            files_preserved += 1

        else:
            # File in both — compare hashes
            src_file = source_path / rel_path if source_path.is_dir() else source_path
            dst_file = target_path / rel_path if target_path.is_dir() else target_path

            src_hash = _file_hash(src_file)
            dst_hash = _file_hash(dst_file)

            if src_hash == dst_hash:
                # Identical — skip
                file_actions.append(
                    MergeFileAction(file_path=rel_path, action="skipped")
                )
                files_skipped += 1
            else:
                # Both sides modified — conflict; keep project version
                file_actions.append(
                    MergeFileAction(
                        file_path=rel_path,
                        action="conflict",
                        detail=(
                            f"File modified on both sides "
                            f"(collection={src_hash[:8]}, project={dst_hash[:8]}). "
                            f"Project version kept."
                        ),
                    )
                )
                conflicts += 1

    merge_details = MergeDeployDetails(
        files_copied=files_copied,
        files_skipped=files_skipped,
        files_preserved=files_preserved,
        conflicts=conflicts,
        file_actions=file_actions,
    )

    has_conflicts = conflicts > 0
    if has_conflicts:
        msg = (
            f"Artifact '{artifact_name}' merge deployed with {conflicts} conflict(s). "
            f"{files_copied} file(s) copied, {files_preserved} preserved, "
            f"{files_skipped} skipped."
        )
    else:
        msg = (
            f"Artifact '{artifact_name}' merge deployed successfully. "
            f"{files_copied} file(s) copied, {files_preserved} preserved, "
            f"{files_skipped} skipped."
        )

    logger.info(
        f"Merge deploy complete for '{artifact_name}': "
        f"copied={files_copied}, skipped={files_skipped}, "
        f"preserved={files_preserved}, conflicts={conflicts}"
    )

    _refresh_cache_safe(artifact_mgr, artifact_id, collection_name)

    return ArtifactDeployResponse(
        success=True,
        message=msg,
        artifact_name=artifact_name,
        artifact_type=artifact_type.value,
        deployed_path=str(target_path),
        strategy="merge",
        merge_details=merge_details,
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
    settings: SettingsDep,
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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Handle upstream sync (no project_path provided)
        if not request.project_path:
            return ArtifactSyncResponse(
                success=False,
                message="Upstream sync is not yet implemented for this endpoint",
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                conflicts=None,
                updated_version=None,
                synced_files_count=None,
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
        target_deployment = None
        collection_name = collection

        for deployment in deployments:
            if (
                deployment.artifact_name == artifact_name
                and deployment.artifact_type == artifact_type.value
            ):
                target_deployment = deployment
                break

        # Backward-compatibility: support legacy sync metadata loaders in tests
        if target_deployment is None and hasattr(sync_mgr, "_load_deployment_metadata"):
            legacy_metadata = sync_mgr._load_deployment_metadata(project_path)
            if legacy_metadata:
                if not collection_name:
                    collection_name = getattr(legacy_metadata, "collection", None)
                for deployed in getattr(legacy_metadata, "artifacts", []) or []:
                    if (
                        deployed.name == artifact_name
                        and deployed.artifact_type == artifact_type.value
                    ):
                        target_deployment = deployed
                        break

        if target_deployment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not deployed in project",
            )

        if not collection_name:
            collection_name = getattr(target_deployment, "from_collection", "default")

        # Verify collection exists (resolve UUID if needed)
        resolved = resolve_collection_name(collection_name, collection_mgr)
        if not resolved:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )
        collection_name = resolved

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
                    synced_files_count = sum(
                        1
                        for _ in iter_artifact_files(
                            artifact_path, set(settings.diff_exclude_dirs)
                        )
                    )

            logger.info(
                f"Artifact '{artifact_name}' sync completed: status={sync_result.status}, "
                f"conflicts={len(conflicts_list) if conflicts_list else 0}"
            )

            # Refresh DB cache after successful project sync (non-blocking)
            if success:
                try:
                    db_session = get_session()
                    try:
                        refresh_single_artifact_cache(
                            db_session, artifact_mgr, artifact_id, collection_name
                        )
                    finally:
                        db_session.close()
                except Exception as cache_err:
                    logger.warning(
                        f"Cache refresh failed for {artifact_id}: {cache_err}"
                    )

                # Invalidate upstream fetch cache — collection version has changed
                try:
                    get_upstream_cache().invalidate_artifact(artifact_id)
                except Exception:
                    pass  # Cache invalidation failure is non-critical

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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
    settings: SettingsDep,
    _token: TokenDep,
    project_path: str = Query(
        ...,
        description="Path to project for comparison",
    ),
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
    summary_only: bool = Query(
        default=False,
        description="Return only summary counts and file metadata without unified diffs",
    ),
    include_unified_diff: bool = Query(
        default=True,
        description="Include unified diff content in file results. Set to False for summary view.",
    ),
    file_paths: Optional[str] = Query(
        default=None,
        description="Comma-separated file paths to include unified diffs for. When set, only these files get full diff content; others get status/hash only.",
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

        # Parse optional file-path filter for lazy per-file diff loading
        requested_files = set(file_paths.split(",")) if file_paths else None

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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

        # Handle case when no deployment record exists (manually deployed or legacy)
        if deployment:
            collection_name = collection or deployment.from_collection
            inferred_artifact_path = deployment.artifact_path
        else:
            # No deployment record - try to infer paths
            logger.debug(
                f"No deployment record for {artifact_id}, attempting to infer paths"
            )
            collection_name = collection or "default"

            # Find artifact in project using standard conventions
            possible_paths = _get_possible_artifact_paths(artifact_type, artifact_name)
            inferred_artifact_path = None

            for path in possible_paths:
                full_path = proj_path / ".claude" / path
                if full_path.exists():
                    inferred_artifact_path = path
                    logger.debug(f"Found artifact at inferred path: {path}")
                    break

            if not inferred_artifact_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_id}' not found in project {project_path}",
                )

        # Find artifact in collection (with fallback across all collections)
        artifact, resolved_collection = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection_name,
        )

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in any collection",
            )
        collection_name = resolved_collection

        # Normalize artifact path to handle duplicate extensions
        normalized_artifact_path = _normalize_artifact_path(artifact.path)

        # Get paths
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        collection_artifact_path = collection_path / normalized_artifact_path
        project_artifact_path = proj_path / ".claude" / inferred_artifact_path

        # Handle missing collection artifact (project has files that aren't in collection)
        collection_exists = collection_artifact_path.exists()
        project_exists = project_artifact_path.exists()

        if not collection_exists and not project_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in either collection or project",
            )

        # Log resilience cases
        if not collection_exists:
            logger.warning(
                f"Collection artifact missing but project exists: {artifact_id} "
                f"(collection_path={collection_artifact_path}, project_path={project_artifact_path}). "
                "Returning diff with all project files marked as 'deleted'."
            )
        elif not project_exists:
            logger.warning(
                f"Project artifact missing but collection exists: {artifact_id} "
                f"(collection_path={collection_artifact_path}, project_path={project_artifact_path}). "
                "Returning diff with all collection files marked as 'added'."
            )

        # Collect all files from both locations — timed to measure filesystem enumeration
        with PerfTimer(
            "router.get_artifact_diff.enumerate_files",
            artifact_id=artifact_id,
            project_path=project_path,
        ):
            collection_files = set()
            project_files = set()
            exclude_dirs = set(settings.diff_exclude_dirs)

            if collection_exists:
                if collection_artifact_path.is_dir():
                    collection_files = {
                        str(f.relative_to(collection_artifact_path))
                        for f in iter_artifact_files(
                            collection_artifact_path, exclude_dirs
                        )
                    }
                else:
                    collection_files = {collection_artifact_path.name}

            if project_exists:
                if project_artifact_path.is_dir():
                    project_files = {
                        str(f.relative_to(project_artifact_path))
                        for f in iter_artifact_files(
                            project_artifact_path, exclude_dirs
                        )
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

        # Build file diffs — timed to measure hashing + diff generation cost
        file_diffs: List[FileDiff] = []
        summary = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}

        with PerfTimer(
            "router.get_artifact_diff.compute",
            artifact_id=artifact_id,
            file_count=len(all_files),
        ):
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

                        # Generate unified diff if text file and not summary-only mode
                        unified_diff = None
                        skip_diff = summary_only or not include_unified_diff
                        if (
                            not skip_diff
                            and requested_files is not None
                            and file_rel_path not in requested_files
                        ):
                            skip_diff = True
                        if (
                            not skip_diff
                            and not is_binary_file(coll_file_path)
                            and not is_binary_file(proj_file_path)
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
                    # File only in collection (treat as "added" if comparing from project perspective,
                    # or "deleted" if project artifact doesn't exist at all)
                    # For collection-vs-project diff: files in collection but not project are "added"
                    # (because deploying from collection would add them to project)
                    file_status = "added"
                    summary["added"] += 1

                    if collection_exists:
                        if collection_artifact_path.is_dir():
                            coll_file_path = collection_artifact_path / file_rel_path
                        else:
                            coll_file_path = collection_artifact_path
                        coll_hash = compute_file_hash(coll_file_path)
                    else:
                        coll_hash = None

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
                    # File only in project (treat as "deleted" if comparing from collection perspective)
                    file_status = "deleted"
                    summary["deleted"] += 1

                    if project_exists:
                        if project_artifact_path.is_dir():
                            proj_file_path = project_artifact_path / file_rel_path
                        else:
                            proj_file_path = project_artifact_path
                        proj_hash = compute_file_hash(proj_file_path)
                    else:
                        proj_hash = None

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
    settings: SettingsDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
    summary_only: bool = Query(
        default=False,
        description="Return only summary counts and file metadata without unified diffs",
    ),
    include_unified_diff: bool = Query(
        default=True,
        description="Include unified diff content in file results. Set to False for summary view.",
    ),
    file_paths: Optional[str] = Query(
        default=None,
        description="Comma-separated file paths to include unified diffs for. When set, only these files get full diff content; others get status/hash only.",
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

        # Parse optional file-path filter for lazy per-file diff loading
        requested_files = set(file_paths.split(",")) if file_paths else None

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact (with fallback across collections)
        artifact, collection_name = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection,
        )

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in any collection",
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

        # Fetch latest upstream version — check short-lived cache first to
        # avoid redundant GitHub API calls when the sync modal fires both
        # upstream-diff and source-project-diff for the same artifact.
        _cache_key = f"{artifact_id}:{collection_name or 'default'}"
        _cached_fetch = None
        try:
            _cached_fetch = get_upstream_cache().get(_cache_key)
        except Exception:
            logger.warning(
                f"Upstream cache get failed for {_cache_key}, falling through to fetch"
            )
        if _cached_fetch is not None:
            fetch_result = _cached_fetch
        else:
            logger.info(f"Fetching upstream update for {artifact_id}")
            fetch_result = artifact_mgr.fetch_update(
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                collection_name=collection_name,
            )
            if not fetch_result.error:
                try:
                    get_upstream_cache().put(_cache_key, fetch_result)
                except Exception:
                    logger.warning(f"Upstream cache put failed for {_cache_key}")

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

        # Normalize artifact path to handle duplicate extensions
        normalized_artifact_path = _normalize_artifact_path(artifact.path)

        # Get paths
        collection_path = collection_mgr.config.get_collection_path(collection_name)
        collection_artifact_path = collection_path / normalized_artifact_path
        upstream_artifact_path = fetch_result.fetch_result.artifact_path

        # Handle missing artifacts gracefully
        collection_exists = collection_artifact_path.exists()
        upstream_exists = upstream_artifact_path.exists()

        if not collection_exists and not upstream_exists:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Neither collection nor upstream artifact exists for {artifact_id}",
            )

        # Log resilience cases
        if not collection_exists:
            logger.warning(
                f"Collection artifact missing but upstream exists: {artifact_id} "
                f"(collection_path={collection_artifact_path}). "
                "Returning diff with all upstream files marked as 'added'."
            )
        elif not upstream_exists:
            logger.warning(
                f"Upstream artifact missing but collection exists: {artifact_id} "
                f"(upstream_path={upstream_artifact_path}). "
                "Returning diff with all collection files marked as 'deleted'."
            )

        # Collect all files from both locations
        collection_files = set()
        upstream_files = set()
        exclude_dirs = set(settings.diff_exclude_dirs)

        if collection_exists:
            if collection_artifact_path.is_dir():
                collection_files = {
                    str(f.relative_to(collection_artifact_path))
                    for f in iter_artifact_files(collection_artifact_path, exclude_dirs)
                }
            else:
                collection_files = {collection_artifact_path.name}

        if upstream_exists:
            if upstream_artifact_path.is_dir():
                upstream_files = {
                    str(f.relative_to(upstream_artifact_path))
                    for f in iter_artifact_files(upstream_artifact_path, exclude_dirs)
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

                    # Generate unified diff if text file and not summary-only mode
                    unified_diff = None
                    skip_diff = summary_only or not include_unified_diff
                    if (
                        not skip_diff
                        and requested_files is not None
                        and file_rel_path not in requested_files
                    ):
                        skip_diff = True
                    if (
                        not skip_diff
                        and not is_binary_file(coll_file_path)
                        and not is_binary_file(upstream_file_path)
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

                if collection_exists:
                    if collection_artifact_path.is_dir():
                        coll_file_path = collection_artifact_path / file_rel_path
                    else:
                        coll_file_path = collection_artifact_path
                    coll_hash = compute_file_hash(coll_file_path)
                else:
                    coll_hash = None

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

                if upstream_exists:
                    if upstream_artifact_path.is_dir():
                        upstream_file_path = upstream_artifact_path / file_rel_path
                    else:
                        upstream_file_path = upstream_artifact_path
                    upstream_hash = compute_file_hash(upstream_file_path)
                else:
                    upstream_hash = None

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
    "/{artifact_id}/source-project-diff",
    response_model=ArtifactDiffResponse,
    summary="Get source-to-project diff",
    description="Compare artifact upstream source directly against project deployment",
    responses={
        200: {"description": "Successfully retrieved source-project diff"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or missing project_path",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact_source_project_diff(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    settings: SettingsDep,
    _token: TokenDep,
    project_path: str = Query(
        ...,
        description="Path to project deployment directory",
    ),
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (searches all if not specified)",
    ),
    summary_only: bool = Query(
        default=False,
        description="Return only summary counts and file metadata without unified diffs",
    ),
    include_unified_diff: bool = Query(
        default=True,
        description="Include unified diff content in file results. Set to False for summary view.",
    ),
    file_paths: Optional[str] = Query(
        default=None,
        description="Comma-separated file paths to include unified diffs for. When set, only these files get full diff content; others get status/hash only.",
    ),
) -> ArtifactDiffResponse:
    """Get diff between upstream source and project deployment, skipping collection.

    Fetches the latest upstream version from GitHub and compares it directly
    against the deployed version in a project, bypassing the collection copy.

    Args:
        artifact_id: Artifact identifier (format: "type:name")
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        _token: Authentication token (dependency injection)
        project_path: Path to project directory containing deployed artifact
        collection: Optional collection filter

    Returns:
        ArtifactDiffResponse with file-level diffs and summary

    Raises:
        HTTPException: If artifact not found, project not found, or on error
    """
    try:
        logger.info(
            f"Getting source-project diff for artifact: {artifact_id} "
            f"(project={project_path}, collection={collection})"
        )

        # Parse optional file-path filter for lazy per-file diff loading
        requested_files = set(file_paths.split(",")) if file_paths else None

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
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

        if deployment:
            collection_name = collection or deployment.from_collection
            inferred_artifact_path = deployment.artifact_path
        else:
            logger.debug(
                f"No deployment record for {artifact_id}, attempting to infer paths"
            )
            collection_name = collection or "default"
            possible_paths = _get_possible_artifact_paths(artifact_type, artifact_name)
            inferred_artifact_path = None

            for path in possible_paths:
                full_path = proj_path / ".claude" / path
                if full_path.exists():
                    inferred_artifact_path = path
                    break

            if not inferred_artifact_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_id}' not found in project {project_path}",
                )

        # Find artifact in collection (with fallback across all collections)
        artifact, resolved_collection = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection_name,
        )

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in any collection",
            )
        collection_name = resolved_collection

        # Check upstream support
        if artifact.origin != "github":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Artifact origin '{artifact.origin}' does not support source diff. Only GitHub artifacts are supported.",
            )

        if not artifact.upstream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Artifact does not have upstream tracking configured",
            )

        # Fetch latest upstream version — primary network cost for source-project diff.
        # Check the short-lived cache first to avoid a redundant GitHub API call when
        # the sync modal has already fetched upstream data for this artifact (e.g. via
        # the upstream-diff endpoint moments earlier in the same modal session).
        _cache_key = f"{artifact_id}:{collection_name or 'default'}"
        _cached_fetch = None
        try:
            _cached_fetch = get_upstream_cache().get(_cache_key)
        except Exception:
            logger.warning(
                f"Upstream cache get failed for {_cache_key}, falling through to fetch"
            )
        if _cached_fetch is not None:
            logger.info(
                f"Using cached upstream fetch for source-project diff: {artifact_id}"
            )
            fetch_result = _cached_fetch
        else:
            logger.info(f"Fetching upstream for source-project diff: {artifact_id}")
            with PerfTimer(
                "router.get_artifact_source_project_diff.fetch_upstream",
                artifact_id=artifact_id,
                collection=collection_name,
            ):
                fetch_result = artifact_mgr.fetch_update(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                )
            if not fetch_result.error:
                try:
                    get_upstream_cache().put(_cache_key, fetch_result)
                except Exception:
                    logger.warning(f"Upstream cache put failed for {_cache_key}")

        try:
            if fetch_result.error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch upstream: {fetch_result.error}",
                )

            # Normalize artifact path to handle duplicate extensions
            normalized_artifact_path = _normalize_artifact_path(artifact.path)

            # Determine upstream artifact path
            if fetch_result.has_update and fetch_result.fetch_result:
                upstream_artifact_path = fetch_result.fetch_result.artifact_path
            elif not fetch_result.has_update:
                # No upstream update means collection matches upstream; use collection copy
                collection_path = collection_mgr.config.get_collection_path(
                    collection_name
                )
                upstream_artifact_path = collection_path / normalized_artifact_path
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to resolve upstream artifact path",
                )

            project_artifact_path = proj_path / ".claude" / inferred_artifact_path

            # Handle missing artifacts gracefully
            upstream_exists = upstream_artifact_path.exists()
            project_exists = project_artifact_path.exists()

            if not upstream_exists and not project_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Neither upstream nor project artifact exists for {artifact_id}",
                )

            # Log resilience cases
            if not upstream_exists:
                logger.warning(
                    f"Upstream artifact missing but project exists: {artifact_id} "
                    f"(upstream_path={upstream_artifact_path}, project_path={project_artifact_path}). "
                    "Returning diff with all project files marked as 'deleted'."
                )
            elif not project_exists:
                logger.warning(
                    f"Project artifact missing but upstream exists: {artifact_id} "
                    f"(upstream_path={upstream_artifact_path}, project_path={project_artifact_path}). "
                    "Returning diff with all upstream files marked as 'added'."
                )

            # Collect files from both locations — timed to measure filesystem enumeration
            with PerfTimer(
                "router.get_artifact_source_project_diff.enumerate_files",
                artifact_id=artifact_id,
                project_path=project_path,
            ):
                source_files = set()
                project_files = set()
                exclude_dirs = set(settings.diff_exclude_dirs)

                if upstream_exists:
                    if upstream_artifact_path.is_dir():
                        source_files = {
                            str(f.relative_to(upstream_artifact_path))
                            for f in iter_artifact_files(
                                upstream_artifact_path, exclude_dirs
                            )
                        }
                    else:
                        source_files = {upstream_artifact_path.name}

                if project_exists:
                    if project_artifact_path.is_dir():
                        project_files = {
                            str(f.relative_to(project_artifact_path))
                            for f in iter_artifact_files(
                                project_artifact_path, exclude_dirs
                            )
                        }
                    else:
                        project_files = {project_artifact_path.name}

            all_files = sorted(source_files | project_files)

            def compute_file_hash(file_path: PathLib) -> str:
                hasher = hashlib.sha256()
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        hasher.update(chunk)
                return hasher.hexdigest()

            def is_binary_file(file_path: PathLib) -> bool:
                try:
                    with open(file_path, "rb") as f:
                        chunk = f.read(8192)
                        return b"\x00" in chunk
                except Exception:
                    return True

            file_diffs: List[FileDiff] = []
            summary = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}

            # Diff computation — timed to measure hashing + diff generation cost
            with PerfTimer(
                "router.get_artifact_source_project_diff.compute",
                artifact_id=artifact_id,
                file_count=len(all_files),
            ):
                for file_rel_path in all_files:
                    in_source = file_rel_path in source_files
                    in_project = file_rel_path in project_files

                    if in_source and in_project:
                        src_file = (
                            upstream_artifact_path / file_rel_path
                            if upstream_artifact_path.is_dir()
                            else upstream_artifact_path
                        )
                        proj_file = (
                            project_artifact_path / file_rel_path
                            if project_artifact_path.is_dir()
                            else project_artifact_path
                        )

                        src_hash = compute_file_hash(src_file)
                        proj_hash = compute_file_hash(proj_file)

                        if src_hash == proj_hash:
                            file_status = "unchanged"
                            unified_diff = None
                            summary["unchanged"] += 1
                        else:
                            file_status = "modified"
                            summary["modified"] += 1
                            unified_diff = None
                            skip_diff = summary_only or not include_unified_diff
                            if (
                                not skip_diff
                                and requested_files is not None
                                and file_rel_path not in requested_files
                            ):
                                skip_diff = True
                            if (
                                not skip_diff
                                and not is_binary_file(src_file)
                                and not is_binary_file(proj_file)
                            ):
                                try:
                                    with open(src_file, "r", encoding="utf-8") as f:
                                        src_lines = f.readlines()
                                    with open(proj_file, "r", encoding="utf-8") as f:
                                        proj_lines = f.readlines()
                                    diff_lines = difflib.unified_diff(
                                        src_lines,
                                        proj_lines,
                                        fromfile=f"source/{file_rel_path}",
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
                                collection_hash=src_hash,
                                project_hash=proj_hash,
                                unified_diff=unified_diff,
                            )
                        )

                    elif in_source and not in_project:
                        # File only in source (would be added when deploying)
                        file_status = "added"
                        summary["added"] += 1
                        if upstream_exists:
                            src_file = (
                                upstream_artifact_path / file_rel_path
                                if upstream_artifact_path.is_dir()
                                else upstream_artifact_path
                            )
                            src_hash = compute_file_hash(src_file)
                        else:
                            src_hash = None
                        file_diffs.append(
                            FileDiff(
                                file_path=file_rel_path,
                                status=file_status,
                                collection_hash=src_hash,
                                project_hash=None,
                                unified_diff=None,
                            )
                        )

                    elif not in_source and in_project:
                        # File only in project (would be deleted when syncing from source)
                        file_status = "deleted"
                        summary["deleted"] += 1
                        if project_exists:
                            proj_file = (
                                project_artifact_path / file_rel_path
                                if project_artifact_path.is_dir()
                                else project_artifact_path
                            )
                            proj_hash = compute_file_hash(proj_file)
                        else:
                            proj_hash = None
                        file_diffs.append(
                            FileDiff(
                                file_path=file_rel_path,
                                status=file_status,
                                collection_hash=None,
                                project_hash=proj_hash,
                                unified_diff=None,
                            )
                        )

            has_changes = (
                summary["added"] > 0
                or summary["modified"] > 0
                or summary["deleted"] > 0
            )

            logger.info(
                f"Source-project diff computed for {artifact_id}: {len(file_diffs)} files, "
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
        finally:
            # Clean up temp workspace if one was created
            try:
                if fetch_result.temp_workspace and fetch_result.temp_workspace.exists():
                    shutil.rmtree(fetch_result.temp_workspace, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temp workspace: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting source-project diff for '{artifact_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get source-project diff: {str(e)}",
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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact (with fallback across collections)
        artifact, collection_name = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection,
        )

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact (with fallback across collections)
        artifact, collection_name = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection,
        )

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact (with fallback across collections)
        artifact, collection_name = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection,
        )

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

        # Refresh DB cache after successful file update (non-blocking)
        try:
            db_session = get_session()
            try:
                refresh_single_artifact_cache(
                    db_session, _artifact_mgr, artifact_id, collection_name
                )
                logger.debug(f"Refreshed cache after file update: {artifact_id}")
            finally:
                db_session.close()
        except Exception as cache_err:
            logger.warning(
                f"Cache refresh failed after file update for {artifact_id}: {cache_err}"
            )

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact (with fallback across collections)
        artifact, collection_name = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection,
        )

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

        # Refresh DB cache after successful file create (non-blocking)
        try:
            db_session = get_session()
            try:
                refresh_single_artifact_cache(
                    db_session, _artifact_mgr, artifact_id, collection_name
                )
                logger.debug(f"Refreshed cache after file create: {artifact_id}")
            finally:
                db_session.close()
        except Exception as cache_err:
            logger.warning(
                f"Cache refresh failed after file create for {artifact_id}: {cache_err}"
            )

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
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Find artifact (with fallback across collections)
        artifact, collection_name = _find_artifact_in_collections(
            artifact_name,
            artifact_type,
            collection_mgr,
            preferred_collection=collection,
        )

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

        # Refresh DB cache after successful file delete (non-blocking)
        try:
            db_session = get_session()
            try:
                refresh_single_artifact_cache(
                    db_session, _artifact_mgr, artifact_id, collection_name
                )
                logger.debug(f"Refreshed cache after file delete: {artifact_id}")
            finally:
                db_session.close()
        except Exception as cache_err:
            logger.warning(
                f"Cache refresh failed after file delete for {artifact_id}: {cache_err}"
            )

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
        artifact_id: Unique identifier of the artifact (type:name format)

    Returns:
        List of tags assigned to the artifact

    Raises:
        HTTPException: 404 if artifact not found
        HTTPException: 500 if operation fails
    """
    from skillmeat.core.services import TagService

    service = TagService()

    try:
        # Resolve type:name artifact_id → artifacts.uuid (ADR-007 stable identity)
        db_session = get_session()
        try:
            db_art = db_session.query(Artifact).filter_by(id=artifact_id).first()
        finally:
            db_session.close()

        if not db_art:
            raise HTTPException(
                status_code=404, detail=f"Artifact '{artifact_id}' not found"
            )

        return service.get_artifact_tags(db_art.uuid)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tags for artifact {artifact_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{artifact_id}/tags",
    response_model=ArtifactResponse,
    summary="Update artifact tags",
    description="""
    Update all tags for an artifact.

    Accepts a list of tag names which will be normalized (lowercase, spaces to
    underscores, trimmed). For each tag:
    - If it exists in the tags table, the existing tag is used
    - If it doesn't exist, a new tag is created with the normalized name as slug

    This operation replaces all existing tags with the provided list.
    """,
    responses={
        200: {"description": "Successfully updated artifact tags"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_artifact_tags(
    artifact_id: str,
    request: ArtifactTagsUpdate,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> ArtifactResponse:
    """Update all tags for an artifact.

    This endpoint replaces the artifact's current tags with the provided list.
    Tags are normalized (lowercase, spaces to underscores) by the schema validator.

    Args:
        artifact_id: Unique identifier of the artifact (format: type:name)
        request: Request body containing list of tag names
        collection_mgr: Collection manager dependency
        token: API token for authentication
        collection: Optional collection name

    Returns:
        Updated artifact with new tags

    Raises:
        HTTPException 400: If request data is invalid
        HTTPException 404: If artifact not found
        HTTPException 500: If operation fails
    """
    try:
        logger.info(f"Updating tags for artifact {artifact_id}: {request.tags}")

        # Parse artifact ID (format: type:name)
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Resolve collection
        collection_name = collection or collection_mgr.get_active_collection_name()

        # Load collection
        try:
            coll = collection_mgr.load_collection(collection_name)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Find artifact
        try:
            artifact = coll.find_artifact(artifact_name, artifact_type)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),  # Ambiguous artifact name
            )

        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in collection",
            )

        # Update tags (request.tags is already normalized by the validator)
        artifact.tags = request.tags

        # Save collection back to disk
        collection_mgr.save_collection(coll)

        # Refresh CollectionArtifact cache to keep tags in sync
        try:
            db_session = get_session()
            # Resolve type:name artifact_id → artifacts.uuid for the FK lookup
            db_art = db_session.query(Artifact).filter_by(id=artifact_id).first()
            if db_art:
                cas = (
                    db_session.query(CollectionArtifact)
                    .filter_by(artifact_uuid=db_art.uuid)
                    .all()
                )
                for ca in cas:
                    ca.tags_json = json.dumps(request.tags) if request.tags else None
                db_session.commit()
            db_session.close()
        except Exception as cache_err:
            logger.warning(
                f"Failed to update CollectionArtifact tags cache: {cache_err}"
            )

        logger.info(
            f"Successfully updated tags for artifact {artifact_id}: {artifact.tags}"
        )

        # Return updated artifact response
        return artifact_to_response(artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update tags for artifact {artifact_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update artifact tags: {str(e)}",
        )


@router.post(
    "/{artifact_id}/tags/{tag_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add tag to artifact",
    description="Associate a tag with an artifact",
)
async def add_tag_to_artifact(
    artifact_id: str,
    tag_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
) -> dict[str, str]:
    """Add a tag to an artifact.

    Args:
        artifact_id: Unique identifier of the artifact
        tag_id: Unique identifier of the tag
        collection_mgr: Collection manager dependency
        token: API token for authentication

    Returns:
        Success message with artifact and tag IDs

    Raises:
        HTTPException: 400 if association already exists or invalid request
        HTTPException: 404 if artifact or tag not found
    """
    from skillmeat.core.services import TagService

    service = TagService()

    # Resolve type:name artifact_id → artifacts.uuid (ADR-007 stable identity)
    db_session = get_session()
    try:
        db_art = db_session.query(Artifact).filter_by(id=artifact_id).first()
    finally:
        db_session.close()

    if not db_art:
        raise HTTPException(
            status_code=404, detail=f"Artifact '{artifact_id}' not found"
        )

    artifact_uuid = db_art.uuid

    try:
        service.add_tag_to_artifact(artifact_uuid, tag_id)

        # Write-through: sync tags to CollectionArtifact.tags_json and filesystem
        updated_tags = [t.name for t in service.get_artifact_tags(artifact_uuid)]

        # Update CollectionArtifact.tags_json in DB cache
        try:
            db_session = get_session()
            cas = (
                db_session.query(CollectionArtifact)
                .filter_by(artifact_uuid=artifact_uuid)
                .all()
            )
            for ca in cas:
                ca.tags_json = json.dumps(updated_tags) if updated_tags else None
            db_session.commit()
            db_session.close()
        except Exception as cache_err:
            logger.warning(
                f"Failed to update CollectionArtifact tags cache: {cache_err}"
            )

        # Update filesystem artifact
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
            collection_name = collection_mgr.get_active_collection_name()
            coll = collection_mgr.load_collection(collection_name)
            artifact = coll.find_artifact(artifact_name, artifact_type)
            if artifact:
                artifact.tags = updated_tags
                collection_mgr.save_collection(coll)
                logger.info(
                    f"Updated filesystem tags for {artifact_id}: {updated_tags}"
                )
        except Exception as fs_err:
            logger.warning(f"Failed to update filesystem artifact tags: {fs_err}")

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
async def remove_tag_from_artifact(
    artifact_id: str,
    tag_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
) -> None:
    """Remove a tag from an artifact.

    Args:
        artifact_id: Unique identifier of the artifact
        tag_id: Unique identifier of the tag
        collection_mgr: Collection manager dependency
        token: API token for authentication

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 400 if invalid request
        HTTPException: 404 if tag association not found
    """
    from skillmeat.core.services import TagService

    service = TagService()

    # Resolve type:name artifact_id → artifacts.uuid (ADR-007 stable identity)
    db_session = get_session()
    try:
        db_art = db_session.query(Artifact).filter_by(id=artifact_id).first()
    finally:
        db_session.close()

    if not db_art:
        raise HTTPException(
            status_code=404, detail=f"Artifact '{artifact_id}' not found"
        )

    artifact_uuid = db_art.uuid

    try:
        if not service.remove_tag_from_artifact(artifact_uuid, tag_id):
            raise HTTPException(status_code=404, detail="Tag association not found")

        # Write-through: sync tags to CollectionArtifact.tags_json and filesystem
        updated_tags = [t.name for t in service.get_artifact_tags(artifact_uuid)]

        # Update CollectionArtifact.tags_json in DB cache
        try:
            db_session = get_session()
            cas = (
                db_session.query(CollectionArtifact)
                .filter_by(artifact_uuid=artifact_uuid)
                .all()
            )
            for ca in cas:
                ca.tags_json = json.dumps(updated_tags) if updated_tags else None
            db_session.commit()
            db_session.close()
        except Exception as cache_err:
            logger.warning(
                f"Failed to update CollectionArtifact tags cache: {cache_err}"
            )

        # Update filesystem artifact
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
            collection_name = collection_mgr.get_active_collection_name()
            coll = collection_mgr.load_collection(collection_name)
            artifact = coll.find_artifact(artifact_name, artifact_type)
            if artifact:
                artifact.tags = updated_tags
                collection_mgr.save_collection(coll)
                logger.info(
                    f"Updated filesystem tags for {artifact_id}: {updated_tags}"
                )
        except Exception as fs_err:
            logger.warning(f"Failed to update filesystem artifact tags: {fs_err}")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Linked Artifacts Endpoints
# =============================================================================


@router.post(
    "/{artifact_id}/linked-artifacts",
    response_model=LinkedArtifactReferenceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create artifact link",
    description="Create a link from this artifact to another artifact.",
    responses={
        201: {"description": "Successfully created artifact link"},
        400: {"model": ErrorResponse, "description": "Invalid request or self-linking"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        409: {"model": ErrorResponse, "description": "Link already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_linked_artifact(
    artifact_id: str,
    request: CreateLinkedArtifactRequest,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> LinkedArtifactReferenceSchema:
    """Create a link from one artifact to another.

    Validates:
    - Both artifacts exist
    - Not linking to self
    - Link doesn't already exist

    Args:
        artifact_id: Source artifact identifier (format: type:name)
        request: Request body with target artifact ID and link type
        collection_mgr: Collection manager dependency
        token: API token for authentication
        collection: Optional collection name

    Returns:
        Created linked artifact reference

    Raises:
        HTTPException 400: If self-linking or invalid request
        HTTPException 404: If source or target artifact not found
        HTTPException 409: If link already exists
        HTTPException 500: If operation fails
    """
    try:
        logger.info(
            f"Creating link from {artifact_id} to {request.target_artifact_id} "
            f"with type '{request.link_type}'"
        )

        # Parse source artifact ID
        try:
            source_type_str, source_name = parse_artifact_id(artifact_id)
            source_type = ArtifactType(source_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Parse target artifact ID
        try:
            target_type_str, target_name = parse_artifact_id(request.target_artifact_id)
            target_type = ArtifactType(target_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target artifact ID format. Expected 'type:name'",
            )

        # Prevent self-linking
        if artifact_id == request.target_artifact_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot link artifact to itself",
            )

        # Resolve collection
        collection_name = collection or collection_mgr.get_active_collection_name()

        # Load collection
        try:
            coll = collection_mgr.load_collection(collection_name)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Find source artifact
        source_artifact = coll.find_artifact(source_name, source_type)
        if source_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source artifact '{artifact_id}' not found",
            )

        # Find target artifact
        target_artifact = coll.find_artifact(target_name, target_type)
        if target_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target artifact '{request.target_artifact_id}' not found",
            )

        # Ensure source artifact has metadata
        if source_artifact.metadata is None:
            from skillmeat.core.artifact import ArtifactMetadata

            source_artifact.metadata = ArtifactMetadata()

        # Resolve linked_artifacts if needed
        source_artifact.metadata.resolve_linked_artifacts()

        # Check if link already exists
        existing_links = source_artifact.metadata.linked_artifacts or []
        for existing_link in existing_links:
            existing_id = (
                existing_link.artifact_id
                if hasattr(existing_link, "artifact_id")
                else existing_link.get("artifact_id")
            )
            if existing_id == request.target_artifact_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Link to '{request.target_artifact_id}' already exists",
                )

        # Create new link
        new_link = LinkedArtifactReference(
            artifact_id=request.target_artifact_id,
            artifact_name=target_artifact.name,
            artifact_type=target_artifact.type,
            source_name=(
                target_artifact.upstream if target_artifact.upstream else "local"
            ),
            link_type=request.link_type,
            created_at=datetime.now(timezone.utc),
        )

        # Add to source artifact's linked_artifacts
        source_artifact.metadata.linked_artifacts.append(new_link)

        # Clear matching unlinked reference if present
        # Check if target was in unlinked_references and remove it
        unlinked = source_artifact.metadata.unlinked_references or []
        target_name_lower = target_artifact.name.lower()

        # Check for variations of the name (exact match and plural handling)
        updated_unlinked = [
            ref
            for ref in unlinked
            if ref.lower() != target_name_lower
            and ref.lower().rstrip("s") != target_name_lower.rstrip("s")
        ]

        if len(updated_unlinked) != len(unlinked):
            source_artifact.metadata.unlinked_references = updated_unlinked
            logger.info(
                f"Cleared unlinked reference for {target_artifact.name} from {source_artifact.name}"
            )

        # Save collection back to disk
        collection_mgr.save_collection(coll)

        logger.info(
            f"Successfully created link from {artifact_id} to {request.target_artifact_id}"
        )

        # Return the created link as response
        return LinkedArtifactReferenceSchema(
            artifact_id=new_link.artifact_id,
            artifact_name=new_link.artifact_name,
            artifact_type=(
                new_link.artifact_type.value
                if hasattr(new_link.artifact_type, "value")
                else str(new_link.artifact_type)
            ),
            source_name=new_link.source_name,
            link_type=new_link.link_type,
            created_at=new_link.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to create link from {artifact_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create artifact link: {str(e)}",
        )


@router.delete(
    "/{artifact_id}/linked-artifacts/{target_artifact_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete artifact link",
    description="Remove a link from this artifact to another.",
    responses={
        204: {"description": "Successfully deleted artifact link"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact or link not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_linked_artifact(
    artifact_id: str,
    target_artifact_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> None:
    """Delete a link from one artifact to another.

    Args:
        artifact_id: Source artifact identifier (format: type:name)
        target_artifact_id: Target artifact identifier (format: type:name)
        collection_mgr: Collection manager dependency
        token: API token for authentication
        collection: Optional collection name

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 404: If artifact or link not found
        HTTPException 500: If operation fails
    """
    try:
        logger.info(f"Deleting link from {artifact_id} to {target_artifact_id}")

        # Parse source artifact ID
        try:
            source_type_str, source_name = parse_artifact_id(artifact_id)
            source_type = ArtifactType(source_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Resolve collection
        collection_name = collection or collection_mgr.get_active_collection_name()

        # Load collection
        try:
            coll = collection_mgr.load_collection(collection_name)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Find source artifact
        source_artifact = coll.find_artifact(source_name, source_type)
        if source_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Check if artifact has linked_artifacts
        if source_artifact.metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Link to '{target_artifact_id}' not found",
            )

        # Resolve linked_artifacts if needed
        source_artifact.metadata.resolve_linked_artifacts()

        # Get current links
        current_links = source_artifact.metadata.linked_artifacts or []
        original_count = len(current_links)

        # Filter out the target link
        new_links = []
        for link in current_links:
            link_id = (
                link.artifact_id
                if hasattr(link, "artifact_id")
                else link.get("artifact_id")
            )
            if link_id != target_artifact_id:
                new_links.append(link)

        # Check if link was found
        if len(new_links) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Link to '{target_artifact_id}' not found",
            )

        # Update linked_artifacts
        source_artifact.metadata.linked_artifacts = new_links

        # Save collection back to disk
        collection_mgr.save_collection(coll)

        logger.info(
            f"Successfully deleted link from {artifact_id} to {target_artifact_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to delete link from {artifact_id} to {target_artifact_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete artifact link: {str(e)}",
        )


@router.get(
    "/{artifact_id}/linked-artifacts",
    response_model=List[LinkedArtifactReferenceSchema],
    summary="List artifact links",
    description="Get all artifacts linked from this artifact.",
    responses={
        200: {"description": "Successfully retrieved artifact links"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_linked_artifacts(
    artifact_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    link_type: Optional[str] = Query(
        default=None,
        description="Filter by link type (requires, enables, related)",
        pattern="^(requires|enables|related)$",
    ),
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> List[LinkedArtifactReferenceSchema]:
    """List all artifacts linked from this artifact.

    Args:
        artifact_id: Artifact identifier (format: type:name)
        collection_mgr: Collection manager dependency
        token: API token for authentication
        link_type: Optional filter by link type
        collection: Optional collection name

    Returns:
        List of linked artifact references

    Raises:
        HTTPException 404: If artifact not found
        HTTPException 500: If operation fails
    """
    try:
        logger.info(
            f"Listing linked artifacts for {artifact_id} (link_type={link_type})"
        )

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Resolve collection
        collection_name = collection or collection_mgr.get_active_collection_name()

        # Load collection
        try:
            coll = collection_mgr.load_collection(collection_name)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Find artifact
        artifact = coll.find_artifact(artifact_name, artifact_type)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get linked artifacts
        links = []
        if artifact.metadata and artifact.metadata.linked_artifacts:
            # Resolve linked_artifacts if needed
            artifact.metadata.resolve_linked_artifacts()

            for link in artifact.metadata.linked_artifacts:
                # Get link type - handle both object and dict
                current_link_type = (
                    link.link_type
                    if hasattr(link, "link_type")
                    else link.get("link_type", "requires")
                )

                # Filter by link_type if specified
                if link_type and current_link_type != link_type:
                    continue

                # Convert to response schema
                if hasattr(link, "artifact_id"):
                    # It's a LinkedArtifactReference object
                    links.append(
                        LinkedArtifactReferenceSchema(
                            artifact_id=link.artifact_id,
                            artifact_name=link.artifact_name,
                            artifact_type=(
                                link.artifact_type.value
                                if hasattr(link.artifact_type, "value")
                                else str(link.artifact_type)
                            ),
                            source_name=link.source_name,
                            link_type=link.link_type,
                            created_at=link.created_at,
                        )
                    )
                else:
                    # It's a dict
                    links.append(
                        LinkedArtifactReferenceSchema(
                            artifact_id=link.get("artifact_id"),
                            artifact_name=link.get("artifact_name", ""),
                            artifact_type=link.get("artifact_type", "skill"),
                            source_name=link.get("source_name"),
                            link_type=link.get("link_type", "requires"),
                            created_at=link.get("created_at"),
                        )
                    )

        return links

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list linked artifacts for {artifact_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list linked artifacts: {str(e)}",
        )


@router.get(
    "/{artifact_id}/unlinked-references",
    response_model=Dict[str, List[str]],
    summary="Get unlinked references",
    description="Get references that couldn't be auto-linked.",
    responses={
        200: {"description": "Successfully retrieved unlinked references"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_unlinked_references(
    artifact_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> Dict[str, List[str]]:
    """Get list of unlinked artifact references.

    These are references that were found in the artifact's content or frontmatter
    but couldn't be automatically linked to existing artifacts in the collection.

    Args:
        artifact_id: Artifact identifier (format: type:name)
        collection_mgr: Collection manager dependency
        token: API token for authentication
        collection: Optional collection name

    Returns:
        Dictionary with 'unlinked_references' key containing list of reference strings

    Raises:
        HTTPException 404: If artifact not found
        HTTPException 500: If operation fails
    """
    try:
        logger.info(f"Getting unlinked references for {artifact_id}")

        # Parse artifact ID
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        # Resolve collection
        collection_name = collection or collection_mgr.get_active_collection_name()

        # Load collection
        try:
            coll = collection_mgr.load_collection(collection_name)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Find artifact
        artifact = coll.find_artifact(artifact_name, artifact_type)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        # Get unlinked references
        unlinked = []
        if artifact.metadata and artifact.metadata.unlinked_references:
            unlinked = artifact.metadata.unlinked_references

        return {"unlinked_references": unlinked}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get unlinked references for {artifact_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unlinked references: {str(e)}",
        )


@router.get(
    "/{artifact_id}/sync-diff",
    summary="Get per-member version comparison rows for a skill",
    description=(
        "Return a flat list of VersionComparisonRow objects for the given skill artifact "
        "and its composite members.  The first element is always the parent skill row "
        "(is_member=False); subsequent elements are member rows (is_member=True).  "
        "Returns a single-element list for skills without embedded members.  "
        "Requires collection and project_id query parameters."
    ),
    responses={
        200: {"description": "Successfully retrieved sync diff rows"},
        400: {"model": ErrorResponse, "description": "Invalid artifact ID or missing params"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_skill_sync_diff(
    artifact_id: str,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses active collection if omitted)",
    ),
    project_id: Optional[str] = Query(
        default=None,
        description="Project identifier for deployed_version lookup",
    ),
):
    """Return hierarchical version comparison rows for a skill and its members.

    Uses ``compute_skill_sync_diff()`` from the sync diff service to build one
    row per artifact (parent + members) with ``source_version``,
    ``collection_version``, and ``deployed_version`` fields.

    Args:
        artifact_id: Artifact identifier in ``type:name`` format.
        collection_mgr: Collection manager dependency.
        _token: Authentication token dependency.
        collection: Collection name; defaults to active collection.
        project_id: Project identifier for deployed_version resolution.

    Returns:
        JSON list of VersionComparisonRow-shaped dicts.

    Raises:
        HTTPException 400: Invalid artifact_id or missing required params.
        HTTPException 404: Artifact not found.
        HTTPException 500: Unexpected database or service error.
    """
    from skillmeat.core.services.sync_diff_service import compute_skill_sync_diff  # noqa: PLC0415

    try:
        # Validate artifact ID
        try:
            parse_artifact_id(artifact_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        collection_name = collection or collection_mgr.get_active_collection_name()
        if not collection_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active collection found. Pass the 'collection' query parameter.",
            )

        # Resolve a db_path by looking up the collection path
        try:
            collection_path = collection_mgr.config.get_collection_path(collection_name)
            db_path = str(collection_path / "cache.db")
        except Exception:
            db_path = None

        effective_project_id = project_id or ""

        rows = compute_skill_sync_diff(
            artifact_id=artifact_id,
            collection_id=collection_name,
            project_id=effective_project_id,
            db_path=db_path or "",
            _session=get_session() if not db_path else None,
        )

        return [
            {
                "artifact_id": r.artifact_id,
                "artifact_name": r.artifact_name,
                "artifact_type": r.artifact_type,
                "source_version": r.source_version,
                "collection_version": r.collection_version,
                "deployed_version": r.deployed_version,
                "is_member": r.is_member,
                "parent_artifact_id": r.parent_artifact_id,
            }
            for r in rows
        ]

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Failed to compute sync diff for '%s': %s", artifact_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute sync diff: {str(e)}",
        )


@router.get(
    "/{artifact_id}/associations",
    response_model=AssociationsDTO,
    summary="Get artifact associations",
    description=(
        "Return the composite-artifact associations for a given artifact. "
        "``parents`` lists composites that contain this artifact as a child; "
        "``children`` lists the child artifacts when this artifact is itself a composite."
    ),
    responses={
        200: {"description": "Successfully retrieved associations"},
        400: {"model": ErrorResponse, "description": "Invalid artifact ID format"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact_associations(
    artifact_id: str,
    collection_mgr: CollectionManagerDep,
    _token: TokenDep,
    include_parents: bool = Query(
        default=True,
        description="Include composites that contain this artifact as a child",
    ),
    include_children: bool = Query(
        default=True,
        description="Include child artifacts of this composite",
    ),
    relationship_type: Optional[str] = Query(
        default=None,
        description="Filter by relationship type (e.g. 'contains')",
    ),
    collection: Optional[str] = Query(
        default=None,
        description="Collection name or UUID (uses active collection if omitted)",
    ),
) -> AssociationsDTO:
    """Return composite-membership associations for an artifact.

    Queries the ``composite_memberships`` cache table to return:

    - ``parents``: Composite artifacts (plugins, stacks, suites) that list
      this artifact as a member.
    - ``children``: Artifacts that belong to this composite (only populated
      when ``artifact_id`` itself is a composite).

    Both lists may be empty — an empty response is **not** a 404.  A 404 is
    only returned when the ``artifact_id`` cannot be resolved to any known
    artifact in the active collection.

    Args:
        artifact_id: Artifact identifier in ``type:name`` format
            (e.g. ``"skill:canvas"`` or ``"composite:my-plugin"``).
        collection_mgr: Collection manager dependency.
        _token: Authentication token (dependency injection).
        include_parents: When ``False``, ``parents`` is always ``[]``.
        include_children: When ``False``, ``children`` is always ``[]``.
        relationship_type: Optional filter applied to both parent and child
            lists after retrieval.
        collection: Collection name or UUID; defaults to the active collection.

    Returns:
        AssociationsDTO with ``parents`` and ``children`` lists.

    Raises:
        HTTPException 400: Invalid ``artifact_id`` format.
        HTTPException 404: Artifact not found in the resolved collection.
        HTTPException 500: Unexpected database or service error.

    Example:
        GET /api/v1/artifacts/composite:my-plugin/associations

        Returns::

            {
                "artifact_id": "composite:my-plugin",
                "parents": [],
                "children": [
                    {
                        "artifact_id": "skill:canvas",
                        "artifact_name": "canvas",
                        "artifact_type": "skill",
                        "relationship_type": "contains",
                        "pinned_version_hash": null,
                        "created_at": "2025-01-01T00:00:00"
                    }
                ]
            }
    """
    try:
        logger.info(
            "Getting associations for artifact: %s (collection=%s, "
            "include_parents=%s, include_children=%s, relationship_type=%s)",
            artifact_id,
            collection,
            include_parents,
            include_children,
            relationship_type,
        )

        # Validate artifact ID format
        try:
            artifact_type_str, artifact_name = parse_artifact_id(artifact_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact ID format. Expected 'type:name'",
            )

        try:
            artifact_type_enum = ArtifactType(artifact_type_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown artifact type: '{artifact_type_str}'",
            )

        # Resolve collection name/UUID and find artifact on filesystem.
        # Uses the shared fallback helper so UUIDs and stale collection hints
        # don't incorrectly return 404.
        preferred_collection = collection or collection_mgr.get_active_collection_name()
        artifact_obj, resolved_collection_name = _find_artifact_in_collections(
            artifact_name=artifact_name,
            artifact_type=artifact_type_enum,
            collection_mgr=collection_mgr,
            preferred_collection=preferred_collection,
        )
        if artifact_obj is None or resolved_collection_name is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )
        if collection and preferred_collection != resolved_collection_name:
            logger.warning(
                "Associations collection fallback: requested '%s', resolved '%s' "
                "for artifact '%s'",
                preferred_collection,
                resolved_collection_name,
                artifact_id,
            )

        # Resolve the collection_id used in the DB (the collection UUID / name key)
        # The composite_memberships table stores collection_id as the Collection.id
        # We look it up via the DB session so we use the canonical value.
        db_session = get_session()
        collection_id: Optional[str] = None
        try:
            col_row = (
                db_session.query(Collection)
                .filter(Collection.name == resolved_collection_name)
                .first()
            )
            if col_row is None and collection is not None:
                # Backward-compatible fallback when callers provide UUIDs or
                # human-friendly collection names.
                col_row = (
                    db_session.query(Collection)
                    .filter(
                        (Collection.id == collection) | (Collection.name == collection)
                    )
                    .first()
                )
            if col_row is not None:
                collection_id = col_row.id
        finally:
            db_session.close()

        # Fall back to resolved filesystem name when DB row is unavailable.
        if collection_id is None:
            collection_id = resolved_collection_name

        # Query associations via the repository
        repo = CompositeMembershipRepository()
        raw = repo.get_associations(artifact_id, collection_id)

        def _build_parent_dto(record: dict) -> AssociationItemDTO:
            """Convert a parent membership record dict to AssociationItemDTO."""
            parent_id: str = record.get("composite_id", "")
            if ":" in parent_id:
                p_type, p_name = parent_id.split(":", 1)
            else:
                p_type, p_name = "composite", parent_id
            return AssociationItemDTO(
                artifact_id=parent_id,
                artifact_name=p_name,
                artifact_type=p_type,
                relationship_type=record.get("relationship_type", "contains"),
                pinned_version_hash=record.get("pinned_version_hash"),
                created_at=record.get("created_at"),
            )

        def _build_child_dto(record: dict) -> AssociationItemDTO:
            """Convert a child membership record dict to AssociationItemDTO."""
            child_info = record.get("child_artifact") or {}
            child_id: str = child_info.get("id", record.get("child_artifact_uuid", ""))
            if ":" in child_id:
                c_type, c_name = child_id.split(":", 1)
            else:
                # UUID fallback — use type from child_artifact dict if available
                c_type = child_info.get("type", "unknown")
                c_name = child_info.get("name", child_id)
            return AssociationItemDTO(
                artifact_id=child_id,
                artifact_name=c_name,
                artifact_type=c_type,
                relationship_type=record.get("relationship_type", "contains"),
                pinned_version_hash=record.get("pinned_version_hash"),
                created_at=record.get("created_at"),
            )

        parents: List[AssociationItemDTO] = []
        if include_parents:
            parents = [_build_parent_dto(r) for r in raw.get("parents", [])]
            if relationship_type is not None:
                parents = [
                    p for p in parents if p.relationship_type == relationship_type
                ]

        children: List[AssociationItemDTO] = []
        if include_children:
            children = [_build_child_dto(r) for r in raw.get("children", [])]

            # For skills: look up the companion CompositeArtifact whose
            # metadata_json encodes this skill's UUID as the originating
            # artifact (written by create_skill_composite()).  This surfaces
            # embedded member artifacts (commands, agents, etc.) that live
            # inside the skill directory.
            if artifact_type_str == "skill" and not children:
                skill_uuid_session = get_session()
                try:
                    skill_art = (
                        skill_uuid_session.query(Artifact)
                        .filter(Artifact.id == artifact_id)
                        .first()
                    )
                    if skill_art is not None:
                        skill_members = repo.get_skill_composite_children(
                            skill_artifact_uuid=str(skill_art.uuid),
                            collection_id=collection_id,
                        )
                        children = [_build_child_dto(r) for r in skill_members]
                        if skill_members:
                            logger.debug(
                                "Associations: found %d embedded member(s) via "
                                "skill composite for '%s'",
                                len(skill_members),
                                artifact_id,
                            )
                finally:
                    skill_uuid_session.close()

            if relationship_type is not None:
                children = [
                    c for c in children if c.relationship_type == relationship_type
                ]

        logger.info(
            "Associations for '%s': %d parent(s), %d child(ren)",
            artifact_id,
            len(parents),
            len(children),
        )

        return AssociationsDTO(
            artifact_id=artifact_id,
            parents=parents,
            children=children,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get associations for '%s': %s", artifact_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get associations: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Consolidation endpoints (fixed paths — registered before /{artifact_id}/*)
# to prevent FastAPI from matching "consolidation" as an artifact_id value.
# ---------------------------------------------------------------------------


@router.get(
    "/consolidation/clusters",
    response_model=ConsolidationClustersResponse,
    summary="List consolidation clusters",
    description=(
        "Returns groups of similar artifacts identified for potential consolidation. "
        "Clusters are formed by union-find grouping of DuplicatePair records whose "
        "similarity_score meets the min_score threshold, then paginated via cursor."
    ),
    responses={
        200: {"description": "Successfully retrieved consolidation clusters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_consolidation_clusters(
    db_session: DbSessionDep,
    token: TokenDep,
    min_score: float = Query(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold (0.0–1.0, default 0.5)",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of clusters to return per page (1–100, default 20)",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Opaque pagination cursor returned by a previous call",
    ),
) -> ConsolidationClustersResponse:
    """Return paginated consolidation clusters for deduplication review.

    Loads non-ignored DuplicatePair records that meet the min_score threshold,
    groups them using union-find clustering, and returns a sorted, paginated
    result.  Use ``next_cursor`` from the response to fetch subsequent pages.

    Args:
        db_session: Injected SQLAlchemy session.
        token:      Authentication token (dependency injection).
        min_score:  Minimum pairwise similarity score (0.0–1.0, default 0.5).
        limit:      Page size (1–100, default 20).
        cursor:     Opaque cursor from a previous page, or ``None`` for the first page.

    Returns:
        ConsolidationClustersResponse with clusters and optional next_cursor.

    Raises:
        HTTPException 500: On unexpected errors.

    Example:
        GET /api/v1/artifacts/consolidation/clusters?min_score=0.7&limit=10
    """
    try:
        logger.info(
            "Getting consolidation clusters (min_score=%.2f, limit=%d, cursor=%r)",
            min_score,
            limit,
            cursor,
        )

        from skillmeat.core.similarity import SimilarityService

        service = SimilarityService(session=db_session)
        result = service.get_consolidation_clusters(
            min_score=min_score,
            limit=limit,
            cursor=cursor,
        )

        clusters: List[SimilarityClusterDTO] = [
            SimilarityClusterDTO(
                artifacts=cluster["artifacts"],
                max_score=cluster["max_score"],
                artifact_type=cluster["artifact_type"],
                pair_count=cluster["pair_count"],
            )
            for cluster in result["clusters"]
        ]

        logger.info(
            "Consolidation clusters: returned %d cluster(s), next_cursor=%r",
            len(clusters),
            result["next_cursor"],
        )

        return ConsolidationClustersResponse(
            clusters=clusters,
            next_cursor=result["next_cursor"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get consolidation clusters: %s",
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get consolidation clusters: {str(e)}",
        )


@router.post(
    "/consolidation/pairs/{pair_id}/ignore",
    summary="Ignore a duplicate pair",
    description=(
        "Marks the specified DuplicatePair as ignored so it is excluded from "
        "consolidation cluster results.  Idempotent: calling this on an already-"
        "ignored pair still returns 200."
    ),
    responses={
        200: {"description": "Pair successfully marked as ignored"},
        404: {"model": ErrorResponse, "description": "Pair not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    status_code=status.HTTP_200_OK,
)
async def ignore_duplicate_pair(
    pair_id: str,
    token: TokenDep,
) -> dict:
    """Mark a DuplicatePair as ignored (consolidation skip action).

    Args:
        pair_id: Primary key (UUID hex string) of the DuplicatePair record.
        token:   Authentication token (dependency injection).

    Returns:
        JSON object ``{"pair_id": "<id>", "ignored": true}``.

    Raises:
        HTTPException 404: If no pair with ``pair_id`` exists.
        HTTPException 500: On unexpected database errors.

    Example:
        POST /api/v1/artifacts/consolidation/pairs/abc123/ignore
    """
    try:
        logger.info("Marking duplicate pair %r as ignored", pair_id)

        from skillmeat.cache.repositories import DuplicatePairRepository

        repo = DuplicatePairRepository()
        found = repo.mark_pair_ignored(pair_id)

        if not found:
            logger.info("Duplicate pair not found: %r", pair_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Duplicate pair '{pair_id}' not found",
            )

        logger.info("Duplicate pair %r marked as ignored", pair_id)
        return {"pair_id": pair_id, "ignored": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to ignore duplicate pair '%s': %s",
            pair_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ignore duplicate pair: {str(e)}",
        )


@router.delete(
    "/consolidation/pairs/{pair_id}/ignore",
    summary="Unignore a duplicate pair",
    description=(
        "Clears the ignored flag on the specified DuplicatePair, making it "
        "visible again in consolidation cluster results.  Idempotent: calling "
        "this on a pair that is already active still returns 200."
    ),
    responses={
        200: {"description": "Pair ignore flag successfully cleared"},
        404: {"model": ErrorResponse, "description": "Pair not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    status_code=status.HTTP_200_OK,
)
async def unignore_duplicate_pair(
    pair_id: str,
    token: TokenDep,
) -> dict:
    """Clear the ignored flag on a DuplicatePair (undo consolidation skip).

    Args:
        pair_id: Primary key (UUID hex string) of the DuplicatePair record.
        token:   Authentication token (dependency injection).

    Returns:
        JSON object ``{"pair_id": "<id>", "ignored": false}``.

    Raises:
        HTTPException 404: If no pair with ``pair_id`` exists.
        HTTPException 500: On unexpected database errors.

    Example:
        DELETE /api/v1/artifacts/consolidation/pairs/abc123/ignore
    """
    try:
        logger.info("Clearing ignored flag on duplicate pair %r", pair_id)

        from skillmeat.cache.repositories import DuplicatePairRepository

        repo = DuplicatePairRepository()
        found = repo.unmark_pair_ignored(pair_id)

        if not found:
            logger.info("Duplicate pair not found: %r", pair_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Duplicate pair '{pair_id}' not found",
            )

        logger.info("Duplicate pair %r ignore flag cleared", pair_id)
        return {"pair_id": pair_id, "ignored": False}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to unignore duplicate pair '%s': %s",
            pair_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unignore duplicate pair: {str(e)}",
        )


@router.get(
    "/{artifact_id}/similar",
    response_model=SimilarArtifactsResponse,
    summary="Find similar artifacts",
    description=(
        "Returns artifacts similar to the specified artifact, ranked by composite "
        "similarity score. The artifact_id must be in 'type:name' format "
        "(e.g. 'skill:canvas-design')."
    ),
    responses={
        200: {"description": "Successfully retrieved similar artifacts"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_similar_artifacts(
    artifact_id: str,
    db_session: DbSessionDep,
    token: TokenDep,
    response: Response,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of similar artifacts to return",
    ),
    min_score: float = Query(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum composite similarity score threshold (0.0–1.0)",
    ),
    source: str = Query(
        default="collection",
        pattern="^(collection|marketplace|all)$",
        description="Search scope: 'collection', 'marketplace', or 'all'",
    ),
) -> SimilarArtifactsResponse:
    """Find artifacts similar to the given artifact.

    Resolves the artifact_id (type:name) to its internal UUID, checks the
    SimilarityCacheManager for pre-computed results (cache hit), and falls
    back to live SimilarityService scoring on a cache miss.  Cached results
    are persisted by compute_and_store() for subsequent requests.

    Response headers:
        X-Cache:     ``HIT`` when results came from the cache, ``MISS``
                     when live computation was performed.
        X-Cache-Age: Seconds since the cached scores were computed.
                     Only present on cache HITs.

    Args:
        artifact_id: Artifact identifier in 'type:name' format.
        db_session:  Injected SQLAlchemy session.
        token:       Authentication token (dependency injection).
        response:    FastAPI Response object used to set custom headers.
        limit:       Maximum results to return (1–50, default 10).
        min_score:   Minimum composite score threshold (0.0–1.0, default 0.1).
        source:      Where to search — 'collection', 'marketplace', or 'all'.

    Returns:
        SimilarArtifactsResponse with items ordered by composite score descending.

    Raises:
        HTTPException 404: If the artifact does not exist in the DB cache.
        HTTPException 500: On unexpected errors.

    Example:
        GET /api/v1/artifacts/skill:canvas-design/similar?limit=5&min_score=0.5&source=collection
    """
    try:
        logger.info(
            "Finding similar artifacts for '%s' (limit=%d, min_score=%.2f, source=%s)",
            artifact_id,
            limit,
            min_score,
            source,
        )

        # 1. Resolve type:name → UUID.  Artifact.id stores the 'type:name' string;
        #    SimilarityService and SimilarityCacheManager expect the hex UUID.
        artifact_row: Optional[Artifact] = (
            db_session.query(Artifact).filter(Artifact.id == artifact_id).first()
        )
        if artifact_row is None:
            logger.info("Artifact not found in DB cache: '%s'", artifact_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )

        artifact_uuid: str = str(artifact_row.uuid)

        # 2. Try the similarity cache first.  Only the collection source is
        #    cached — marketplace and cross-source searches always go live.
        from skillmeat.cache.similarity_cache import SimilarityCacheManager
        from skillmeat.core.similarity import SimilarityService

        cache_mgr = SimilarityCacheManager()
        cached_rows: List[dict] = []
        cache_hit = False

        if source == "collection":
            try:
                cached_rows = cache_mgr.get_similar(
                    artifact_uuid, db_session, limit=limit, min_score=min_score
                )
                if cached_rows:
                    cache_hit = True
                    logger.info(
                        "Cache HIT for '%s': returning %d cached result(s)",
                        artifact_id,
                        len(cached_rows),
                    )
            except Exception as cache_err:  # noqa: BLE001
                logger.warning(
                    "SimilarityCacheManager.get_similar failed for '%s': %s; "
                    "falling back to live computation.",
                    artifact_id,
                    cache_err,
                )

        # 3. Set X-Cache response header.
        response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"

        if cache_hit:
            # 3a. Add X-Cache-Age from the computed_at timestamp of the first row.
            computed_at = cached_rows[0].get("computed_at")
            if computed_at is not None:
                try:
                    from datetime import datetime, timezone

                    now_utc = datetime.now(timezone.utc)
                    # computed_at may be a naive datetime (stored as UTC).
                    if computed_at.tzinfo is None:
                        computed_at = computed_at.replace(tzinfo=timezone.utc)
                    age_seconds = max(0, int((now_utc - computed_at).total_seconds()))
                    response.headers["X-Cache-Age"] = str(age_seconds)
                except Exception:  # noqa: BLE001
                    pass  # Cache-Age is best-effort

            # 3b. Build items from cached dicts — resolve target UUIDs to Artifact rows.
            import json as _json

            items: List[SimilarArtifactDTO] = []
            for cached in cached_rows:
                target_uuid = cached.get("target_artifact_uuid")
                if not target_uuid:
                    continue

                target_row: Optional[Artifact] = (
                    db_session.query(Artifact)
                    .filter(Artifact.uuid == target_uuid)
                    .first()
                )
                if target_row is None:
                    continue

                name: str = getattr(target_row, "name", "") or ""
                artifact_type: str = getattr(target_row, "type", "") or ""
                artifact_source: Optional[str] = getattr(target_row, "source", None)
                description: Optional[str] = getattr(target_row, "description", None)
                tags_list: List[str] = []

                meta = getattr(target_row, "artifact_metadata", None)
                if meta is not None:
                    if not description:
                        description = getattr(meta, "description", None)
                    if not description:
                        meta_dict = (
                            meta.get_metadata_dict()
                            if hasattr(meta, "get_metadata_dict")
                            else None
                        )
                        if meta_dict:
                            description = meta_dict.get("description") or None
                    tags_list = (
                        meta.get_tags_list() if hasattr(meta, "get_tags_list") else []
                    )
                else:
                    raw_tags = getattr(target_row, "tags", None)
                    if isinstance(raw_tags, list):
                        tags_list = [getattr(t, "name", str(t)) for t in raw_tags if t]
                    elif isinstance(raw_tags, str) and raw_tags:
                        tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]

                if not tags_list:
                    orm_tags = getattr(target_row, "tags", None)
                    if isinstance(orm_tags, list) and orm_tags:
                        tags_list = [getattr(t, "name", str(t)) for t in orm_tags if t]

                if not description:
                    from skillmeat.cache.models import CollectionArtifact

                    ca = (
                        db_session.query(CollectionArtifact)
                        .filter(
                            CollectionArtifact.artifact_uuid == str(target_uuid)
                        )
                        .first()
                    )
                    if ca and ca.description:
                        description = ca.description

                # Parse breakdown from cached JSON.
                breakdown_data: dict = {}
                raw_breakdown = cached.get("breakdown_json")
                if raw_breakdown:
                    try:
                        breakdown_data = _json.loads(raw_breakdown)
                    except Exception:  # noqa: BLE001
                        pass

                composite_score = float(cached.get("composite_score", 0.0))
                metadata_score = breakdown_data.get("metadata_score", 0.0)
                text_score_raw = breakdown_data.get("text_score")

                breakdown = SimilarityBreakdownDTO(
                    content_score=breakdown_data.get("content_score", 0.0),
                    structure_score=breakdown_data.get("structure_score", 0.0),
                    metadata_score=metadata_score,
                    keyword_score=breakdown_data.get("keyword_score", 0.0),
                    semantic_score=breakdown_data.get("semantic_score"),
                    text_score=(
                        text_score_raw
                        if text_score_raw is not None
                        else metadata_score
                    ),
                )

                # Cached results don't carry match_type — default to "keyword".
                items.append(
                    SimilarArtifactDTO(
                        artifact_id=getattr(target_row, "id", target_uuid),
                        name=name,
                        artifact_type=artifact_type,
                        source=artifact_source,
                        description=description,
                        tags=tags_list,
                        composite_score=composite_score,
                        match_type="keyword",
                        breakdown=breakdown,
                    )
                )

            logger.info(
                "Similar artifacts for '%s' (cache HIT): returning %d result(s)",
                artifact_id,
                len(items),
            )
            return SimilarArtifactsResponse(
                artifact_id=artifact_id,
                items=items,
                total=len(items),
            )

        # 4. Cache MISS — run live similarity search via SimilarityService.
        service = SimilarityService(session=db_session)
        results = service.find_similar(
            artifact_id=artifact_uuid,
            limit=limit,
            min_score=min_score,
            source=source,
        )

        # 5. Convert SimilarityResult objects to SimilarArtifactDTO.
        items = []
        for result in results:
            row = result.artifact  # Artifact or MarketplaceCatalogEntry ORM row
            name = getattr(row, "name", "") or ""
            artifact_type = getattr(row, "type", "") or getattr(
                row, "artifact_type", ""
            ) or ""
            artifact_source = getattr(row, "source", None)
            description = getattr(row, "description", None)

            # Try artifact_metadata relationship for enriched data (Artifact rows).
            meta = getattr(row, "artifact_metadata", None)
            if meta is not None:
                if not description:
                    description = getattr(meta, "description", None)
                # Also check metadata JSON dict (where descriptions are actually stored).
                if not description:
                    meta_dict = meta.get_metadata_dict() if hasattr(meta, "get_metadata_dict") else None
                    if meta_dict:
                        description = meta_dict.get("description") or None
                tags_list = meta.get_tags_list() if hasattr(meta, "get_tags_list") else []
            else:
                raw_tags = getattr(row, "tags", None)
                if isinstance(raw_tags, list):
                    tags_list = [getattr(t, "name", str(t)) for t in raw_tags if t]
                elif isinstance(raw_tags, str) and raw_tags:
                    tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
                else:
                    tags_list = []

            # Final fallback: if meta CSV tags were empty, try the ORM relationship.
            if not tags_list:
                orm_tags = getattr(row, "tags", None)
                if isinstance(orm_tags, list) and orm_tags:
                    tags_list = [getattr(t, "name", str(t)) for t in orm_tags if t]

            # Final fallback: description lives in collection_artifacts table, not
            # artifacts or artifact_metadata.  Query it by artifact UUID.
            if not description:
                from skillmeat.cache.models import CollectionArtifact

                result_artifact_uuid = getattr(row, "uuid", None)
                if result_artifact_uuid:
                    ca = (
                        db_session.query(CollectionArtifact)
                        .filter(
                            CollectionArtifact.artifact_uuid
                            == str(result_artifact_uuid)
                        )
                        .first()
                    )
                    if ca and ca.description:
                        description = ca.description

            breakdown = SimilarityBreakdownDTO(
                content_score=result.breakdown.content_score,
                structure_score=result.breakdown.structure_score,
                metadata_score=result.breakdown.metadata_score,
                keyword_score=result.breakdown.keyword_score,
                semantic_score=result.breakdown.semantic_score,
                # text_score is populated by the text_similarity module (SSO-1.2+).
                # Fall back to metadata_score as a proxy until that module is active,
                # ensuring the field is non-null for existing scoring runs.
                text_score=(
                    result.breakdown.text_score
                    if result.breakdown.text_score is not None
                    else result.breakdown.metadata_score
                ),
            )

            items.append(
                SimilarArtifactDTO(
                    artifact_id=result.artifact_id,
                    name=name,
                    artifact_type=artifact_type,
                    source=artifact_source,
                    description=description,
                    tags=tags_list,
                    composite_score=result.composite_score,
                    match_type=result.match_type.value,
                    breakdown=breakdown,
                )
            )

        logger.info(
            "Similar artifacts for '%s' (cache MISS): found %d live result(s)",
            artifact_id,
            len(items),
        )

        # 6. Persist live results to the cache for future requests (collection source only).
        if source == "collection":
            try:
                cache_mgr.compute_and_store(artifact_uuid, db_session)
            except Exception as store_err:  # noqa: BLE001
                logger.warning(
                    "SimilarityCacheManager.compute_and_store failed for '%s': %s; "
                    "results will not be cached.",
                    artifact_id,
                    store_err,
                )

        return SimilarArtifactsResponse(
            artifact_id=artifact_id,
            items=items,
            total=len(items),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to find similar artifacts for '%s': %s",
            artifact_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar artifacts: {str(e)}",
        )


def _create_auto_snapshot_for_consolidation(
    cluster_id: str,
    action: str,
) -> str:
    """Create an auto-snapshot before a destructive consolidation action.

    Args:
        cluster_id: Cluster identifier (used in snapshot message).
        action: Action name (``'merge'`` or ``'replace'``).

    Returns:
        Snapshot ID string.

    Raises:
        RuntimeError: If snapshot creation fails for any reason.
    """
    from skillmeat.core.version import VersionManager

    version_mgr = VersionManager()
    snapshot = version_mgr.auto_snapshot(
        message=f"Before consolidation {action}: cluster {cluster_id}",
    )
    return snapshot.id


@router.post(
    "/consolidation/clusters/{cluster_id}/merge",
    response_model=ConsolidationActionResponse,
    summary="Merge consolidation cluster (secondary into primary)",
    description=(
        "Merges all secondary artifacts in the cluster into the primary artifact, "
        "then removes the secondaries from the collection.  An auto-snapshot is "
        "always created before any data is modified.  If the snapshot step fails "
        "the action is aborted and a 500 is returned — the collection is never "
        "modified without a confirmed snapshot."
    ),
    responses={
        200: {"description": "Merge completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Cluster or primary artifact not found"},
        500: {"model": ErrorResponse, "description": "Snapshot failed or internal error"},
    },
    status_code=status.HTTP_200_OK,
)
async def merge_consolidation_cluster(
    cluster_id: str,
    request: ConsolidationActionRequest,
    artifact_mgr: ArtifactManagerDep,
    token: TokenDep,
) -> ConsolidationActionResponse:
    """Merge secondary artifacts into the primary for a consolidation cluster.

    The endpoint:
    1. Creates an auto-snapshot (aborts with HTTP 500 if this fails).
    2. Resolves the cluster members from ``DuplicatePair`` records.
    3. Removes each secondary artifact from the collection.
    4. Marks all pairs in the cluster as resolved (ignored).

    Args:
        cluster_id: Opaque cluster identifier (used in snapshot message).
        request:     Request body with ``primary_artifact_uuid`` and optional
                     ``collection_name``.
        artifact_mgr: Injected ArtifactManager.
        token:        Authentication token (dependency injection).

    Returns:
        ConsolidationActionResponse describing what was done.

    Raises:
        HTTPException 500: If the auto-snapshot fails (action is aborted).
        HTTPException 404: If the primary artifact UUID is not found.
        HTTPException 500: On unexpected errors during the merge.

    Example:
        POST /api/v1/artifacts/consolidation/clusters/abc123/merge
        {"primary_artifact_uuid": "deadbeef...", "collection_name": null}
    """
    # --- Step 1: Auto-snapshot (mandatory gate) ---
    try:
        snapshot_id = _create_auto_snapshot_for_consolidation(cluster_id, "merge")
        logger.info(
            "Auto-snapshot created before merge of cluster %r: snapshot_id=%r",
            cluster_id,
            snapshot_id,
        )
    except Exception as snap_err:
        logger.error(
            "Snapshot failed before merge of cluster %r: %s",
            cluster_id,
            snap_err,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Snapshot failed — action aborted",
        )

    # --- Step 2: Resolve cluster members ---
    try:
        from skillmeat.cache.models import DuplicatePair
        from skillmeat.cache.repositories import DuplicatePairRepository

        primary_uuid = request.primary_artifact_uuid

        with get_session() as session:
            # Validate primary artifact exists
            primary_art = (
                session.query(Artifact)
                .filter(Artifact.uuid == primary_uuid)
                .first()
            )
            if primary_art is None:
                logger.warning(
                    "Merge cluster %r: primary artifact UUID %r not found",
                    cluster_id,
                    primary_uuid,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Primary artifact '{primary_uuid}' not found",
                )

            # Collect all UUIDs in the cluster via DuplicatePair records
            pairs = (
                session.query(DuplicatePair)
                .filter(
                    DuplicatePair.ignored.is_(False),
                    (DuplicatePair.artifact1_uuid == primary_uuid)
                    | (DuplicatePair.artifact2_uuid == primary_uuid),
                )
                .all()
            )

            secondary_uuids: List[str] = []
            for pair in pairs:
                other = (
                    pair.artifact2_uuid
                    if pair.artifact1_uuid == primary_uuid
                    else pair.artifact1_uuid
                )
                if other not in secondary_uuids:
                    secondary_uuids.append(other)

            pair_ids = [pair.id for pair in pairs]

        logger.info(
            "Merge cluster %r: primary=%r, secondaries=%r",
            cluster_id,
            primary_uuid,
            secondary_uuids,
        )

        # --- Step 3: Remove each secondary artifact from the collection ---
        removed_uuids: List[str] = []
        with get_session() as session:
            for sec_uuid in secondary_uuids:
                sec_art = (
                    session.query(Artifact)
                    .filter(Artifact.uuid == sec_uuid)
                    .first()
                )
                if sec_art is None:
                    logger.warning(
                        "Merge cluster %r: secondary artifact UUID %r not found, skipping",
                        cluster_id,
                        sec_uuid,
                    )
                    continue

                try:
                    from skillmeat.core.enums import ArtifactType as CoreArtifactType

                    art_type = CoreArtifactType(sec_art.artifact_type)
                    artifact_mgr.remove(
                        artifact_name=sec_art.name,
                        artifact_type=art_type,
                        collection_name=request.collection_name,
                    )
                    removed_uuids.append(sec_uuid)
                    logger.info(
                        "Merge cluster %r: removed secondary artifact %r (%r)",
                        cluster_id,
                        sec_art.name,
                        sec_uuid,
                    )
                except Exception as rm_err:
                    logger.warning(
                        "Merge cluster %r: could not remove secondary %r: %s",
                        cluster_id,
                        sec_uuid,
                        rm_err,
                    )

        # --- Step 4: Mark pairs as resolved (ignored) ---
        repo = DuplicatePairRepository()
        pairs_resolved = 0
        for pid in pair_ids:
            if repo.mark_pair_ignored(pid):
                pairs_resolved += 1

        logger.info(
            "Merge cluster %r completed: removed=%d, pairs_resolved=%d",
            cluster_id,
            len(removed_uuids),
            pairs_resolved,
        )

        return ConsolidationActionResponse(
            action="merge",
            cluster_id=cluster_id,
            primary_artifact_uuid=primary_uuid,
            removed_artifact_uuids=removed_uuids,
            pairs_resolved=pairs_resolved,
            snapshot_id=snapshot_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Merge cluster %r failed: %s",
            cluster_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge consolidation cluster: {str(e)}",
        )


@router.post(
    "/consolidation/clusters/{cluster_id}/replace",
    response_model=ConsolidationActionResponse,
    summary="Replace consolidation cluster (keep primary, discard secondaries)",
    description=(
        "Keeps the primary artifact unchanged and discards all secondary artifacts "
        "in the cluster.  An auto-snapshot is always created before any data is "
        "modified.  If the snapshot step fails the action is aborted and a 500 is "
        "returned — the collection is never modified without a confirmed snapshot."
    ),
    responses={
        200: {"description": "Replace completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Cluster or primary artifact not found"},
        500: {"model": ErrorResponse, "description": "Snapshot failed or internal error"},
    },
    status_code=status.HTTP_200_OK,
)
async def replace_consolidation_cluster(
    cluster_id: str,
    request: ConsolidationActionRequest,
    artifact_mgr: ArtifactManagerDep,
    token: TokenDep,
) -> ConsolidationActionResponse:
    """Keep the primary artifact and discard all secondaries in the cluster.

    Unlike merge, no content from the secondaries is incorporated — the primary
    is kept exactly as-is while the secondaries are deleted from the collection.

    The endpoint:
    1. Creates an auto-snapshot (aborts with HTTP 500 if this fails).
    2. Resolves the cluster members from ``DuplicatePair`` records.
    3. Removes each secondary artifact from the collection.
    4. Marks all pairs in the cluster as resolved (ignored).

    Args:
        cluster_id: Opaque cluster identifier (used in snapshot message).
        request:     Request body with ``primary_artifact_uuid`` and optional
                     ``collection_name``.
        artifact_mgr: Injected ArtifactManager.
        token:        Authentication token (dependency injection).

    Returns:
        ConsolidationActionResponse describing what was done.

    Raises:
        HTTPException 500: If the auto-snapshot fails (action is aborted).
        HTTPException 404: If the primary artifact UUID is not found.
        HTTPException 500: On unexpected errors during the replace.

    Example:
        POST /api/v1/artifacts/consolidation/clusters/abc123/replace
        {"primary_artifact_uuid": "deadbeef...", "collection_name": null}
    """
    # --- Step 1: Auto-snapshot (mandatory gate) ---
    try:
        snapshot_id = _create_auto_snapshot_for_consolidation(cluster_id, "replace")
        logger.info(
            "Auto-snapshot created before replace of cluster %r: snapshot_id=%r",
            cluster_id,
            snapshot_id,
        )
    except Exception as snap_err:
        logger.error(
            "Snapshot failed before replace of cluster %r: %s",
            cluster_id,
            snap_err,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Snapshot failed — action aborted",
        )

    # --- Step 2: Resolve cluster members ---
    try:
        from skillmeat.cache.models import DuplicatePair
        from skillmeat.cache.repositories import DuplicatePairRepository

        primary_uuid = request.primary_artifact_uuid

        with get_session() as session:
            # Validate primary artifact exists
            primary_art = (
                session.query(Artifact)
                .filter(Artifact.uuid == primary_uuid)
                .first()
            )
            if primary_art is None:
                logger.warning(
                    "Replace cluster %r: primary artifact UUID %r not found",
                    cluster_id,
                    primary_uuid,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Primary artifact '{primary_uuid}' not found",
                )

            # Collect all UUIDs in the cluster via DuplicatePair records
            pairs = (
                session.query(DuplicatePair)
                .filter(
                    DuplicatePair.ignored.is_(False),
                    (DuplicatePair.artifact1_uuid == primary_uuid)
                    | (DuplicatePair.artifact2_uuid == primary_uuid),
                )
                .all()
            )

            secondary_uuids: List[str] = []
            for pair in pairs:
                other = (
                    pair.artifact2_uuid
                    if pair.artifact1_uuid == primary_uuid
                    else pair.artifact1_uuid
                )
                if other not in secondary_uuids:
                    secondary_uuids.append(other)

            pair_ids = [pair.id for pair in pairs]

        logger.info(
            "Replace cluster %r: primary=%r, secondaries=%r",
            cluster_id,
            primary_uuid,
            secondary_uuids,
        )

        # --- Step 3: Remove each secondary artifact from the collection ---
        removed_uuids: List[str] = []
        with get_session() as session:
            for sec_uuid in secondary_uuids:
                sec_art = (
                    session.query(Artifact)
                    .filter(Artifact.uuid == sec_uuid)
                    .first()
                )
                if sec_art is None:
                    logger.warning(
                        "Replace cluster %r: secondary artifact UUID %r not found, skipping",
                        cluster_id,
                        sec_uuid,
                    )
                    continue

                try:
                    from skillmeat.core.enums import ArtifactType as CoreArtifactType

                    art_type = CoreArtifactType(sec_art.artifact_type)
                    artifact_mgr.remove(
                        artifact_name=sec_art.name,
                        artifact_type=art_type,
                        collection_name=request.collection_name,
                    )
                    removed_uuids.append(sec_uuid)
                    logger.info(
                        "Replace cluster %r: removed secondary artifact %r (%r)",
                        cluster_id,
                        sec_art.name,
                        sec_uuid,
                    )
                except Exception as rm_err:
                    logger.warning(
                        "Replace cluster %r: could not remove secondary %r: %s",
                        cluster_id,
                        sec_uuid,
                        rm_err,
                    )

        # --- Step 4: Mark pairs as resolved (ignored) ---
        repo = DuplicatePairRepository()
        pairs_resolved = 0
        for pid in pair_ids:
            if repo.mark_pair_ignored(pid):
                pairs_resolved += 1

        logger.info(
            "Replace cluster %r completed: removed=%d, pairs_resolved=%d",
            cluster_id,
            len(removed_uuids),
            pairs_resolved,
        )

        return ConsolidationActionResponse(
            action="replace",
            cluster_id=cluster_id,
            primary_artifact_uuid=primary_uuid,
            removed_artifact_uuids=removed_uuids,
            pairs_resolved=pairs_resolved,
            snapshot_id=snapshot_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Replace cluster %r failed: %s",
            cluster_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replace consolidation cluster: {str(e)}",
        )
