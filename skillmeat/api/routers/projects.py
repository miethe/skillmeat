"""Project management API endpoints.

Provides REST API for browsing and managing projects with deployed artifacts.
"""

import base64
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from skillmeat.api.dependencies import get_app_state, get_collection_manager, verify_api_key
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.artifacts import (
    DeploymentModificationStatus,
    ModificationCheckResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.drift import (
    DriftDetectionResponse,
    DriftSummaryResponse,
)
from skillmeat.api.schemas.projects import (
    CacheInfo,
    ContextEntityInfo,
    ContextMapResponse,
    DeployedArtifact,
    ModifiedArtifactsResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDeleteResponse,
    ProjectDeploymentRemovalResponse,
    ProjectDetail,
    ProjectListResponse,
    ProjectSummary,
    ProjectUpdateRequest,
)
from skillmeat.api.project_registry import ProjectRegistry, get_project_registry
from skillmeat.cache.manager import CacheManager
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.storage.project import ProjectMetadataStorage
from skillmeat.utils.filesystem import compute_content_hash

logger = logging.getLogger(__name__)


# Type alias for registry dependency
RegistryDep = ProjectRegistry

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


# =============================================================================
# Dependency Injection
# =============================================================================


def get_cache_manager() -> Optional[CacheManager]:
    """Get CacheManager dependency.

    Returns:
        CacheManager instance or None if not available

    Note:
        This is an optional dependency that gracefully returns None
        if the cache cannot be initialized. Endpoints should handle
        None by falling back to ProjectRegistry.
    """
    try:
        # Try to get app state without raising exception
        from skillmeat.api.dependencies import app_state

        # Initialize cache manager if not exists
        if not hasattr(app_state, "cache_manager") or app_state.cache_manager is None:
            # Initialize with default settings (6 hours TTL)
            cache_manager = CacheManager(ttl_minutes=360)
            try:
                cache_manager.initialize_cache()
                app_state.cache_manager = cache_manager
                logger.info("Initialized CacheManager for projects API")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize cache manager: {e}. "
                    "Will fall back to ProjectRegistry."
                )
                return None

        return app_state.cache_manager
    except Exception as e:
        logger.warning(
            f"Cache manager not available: {e}. Will fall back to ProjectRegistry."
        )
        return None


# Type alias for cache manager dependency (optional)
CacheManagerDep = Annotated[Optional[CacheManager], Depends(get_cache_manager)]


def encode_project_id(path: str) -> str:
    """Encode a project path to base64 for use as ID.

    Args:
        path: Absolute project path

    Returns:
        Base64 encoded project ID
    """
    return base64.b64encode(path.encode()).decode()


def decode_project_id(project_id: str) -> str:
    """Decode a base64 project ID to path.

    Args:
        project_id: Base64 encoded project ID

    Returns:
        Decoded project path

    Raises:
        HTTPException: If project ID is invalid
    """
    try:
        return base64.b64decode(project_id.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project ID format: {str(e)}",
        )


def discover_projects(search_paths: Optional[List[Path]] = None) -> List[Path]:
    """Discover projects with .claude/.skillmeat-deployed.toml files.

    This function scans configured search paths for projects that have
    deployment tracking files, indicating they contain deployed artifacts.

    Args:
        search_paths: Optional list of paths to search (defaults to common locations)

    Returns:
        List of project paths with deployments
    """
    if search_paths is None:
        # Default search locations
        # TODO: Make this configurable via settings
        home = Path.home()
        search_paths = [
            home / "projects",
            home / "dev",
            home / "workspace",
            home / "src",
            Path.cwd(),  # Current working directory
        ]

    discovered = []
    MAX_DEPTH = 3  # Limit search depth to prevent performance issues

    for search_path in search_paths:
        if not search_path.exists() or not search_path.is_dir():
            continue

        # Validate search path to prevent directory traversal
        try:
            search_path = search_path.resolve()
        except (RuntimeError, OSError) as e:
            logger.warning(f"Invalid search path {search_path}: {e}")
            continue

        # Search for .skillmeat-deployed.toml files with depth limit
        try:
            for deployment_file in search_path.rglob(
                ".claude/.skillmeat-deployed.toml"
            ):
                # Get project root (parent of .claude)
                project_path = deployment_file.parent.parent

                # Validate path is within search_path (security check)
                try:
                    project_path = project_path.resolve()
                    project_path.relative_to(search_path)
                except (ValueError, RuntimeError, OSError):
                    logger.warning(f"Skipping invalid project path: {project_path}")
                    continue

                # Check depth limit
                depth = len(project_path.relative_to(search_path).parts)
                if depth > MAX_DEPTH:
                    continue

                if project_path not in discovered:
                    discovered.append(project_path)
        except (PermissionError, OSError) as e:
            logger.warning(f"Error scanning {search_path}: {e}")
            continue

    return discovered


def build_project_summary(project_path: Path) -> ProjectSummary:
    """Build a ProjectSummary from a project path.

    Args:
        project_path: Absolute path to project directory

    Returns:
        ProjectSummary object
    """
    deployments = DeploymentTracker.read_deployments(project_path)

    # Find most recent deployment
    last_deployment = None
    if deployments:
        last_deployment = max(d.deployed_at for d in deployments)

    # Try to get project name from metadata, fallback to directory name
    metadata = ProjectMetadataStorage.read_metadata(project_path)
    project_name = metadata.name if metadata else project_path.name

    return ProjectSummary(
        id=encode_project_id(str(project_path)),
        path=str(project_path),
        name=project_name,
        deployment_count=len(deployments),
        last_deployment=last_deployment,
    )


def build_project_detail(project_path: Path, db_session: Optional[Session] = None) -> ProjectDetail:
    """Build a ProjectDetail from a project path.

    Args:
        project_path: Absolute path to project directory
        db_session: Optional database session for collection lookups

    Returns:
        ProjectDetail object
    """
    from skillmeat.api.services import CollectionService
    from skillmeat.cache.models import get_session

    deployments = DeploymentTracker.read_deployments(project_path)

    # Fetch collection memberships for all artifacts (batch query)
    collections_map = {}
    if deployments:
        # Construct artifact IDs: {type}:{name}
        artifact_ids = [f"{d.artifact_type}:{d.artifact_name}" for d in deployments]

        # Use provided session or create new one
        session = db_session or get_session()
        try:
            collection_service = CollectionService(session)
            collections_map = collection_service.get_collection_membership_batch(artifact_ids)
        finally:
            # Only close session if we created it
            if db_session is None:
                session.close()

    # Convert to API schema with collection memberships
    deployed_artifacts = [
        DeployedArtifact(
            artifact_name=d.artifact_name,
            artifact_type=d.artifact_type,
            from_collection=d.from_collection,
            deployed_at=d.deployed_at,
            artifact_path=str(d.artifact_path),
            version=None,  # Version not currently stored in deployment
            collection_sha=d.collection_sha,
            local_modifications=d.local_modifications,
            collections=collections_map.get(f"{d.artifact_type}:{d.artifact_name}", []),
        )
        for d in deployments
    ]

    # Calculate statistics
    by_type = defaultdict(int)
    by_collection = defaultdict(int)
    modified_count = 0

    for d in deployments:
        by_type[d.artifact_type] += 1
        by_collection[d.from_collection] += 1
        if d.local_modifications:
            modified_count += 1

    stats = {
        "by_type": dict(by_type),
        "by_collection": dict(by_collection),
        "modified_count": modified_count,
    }

    # Find most recent deployment
    last_deployment = None
    if deployments:
        last_deployment = max(d.deployed_at for d in deployments)

    # Try to get project name from metadata, fallback to directory name
    metadata = ProjectMetadataStorage.read_metadata(project_path)
    project_name = metadata.name if metadata else project_path.name

    return ProjectDetail(
        id=encode_project_id(str(project_path)),
        path=str(project_path),
        name=project_name,
        deployment_count=len(deployments),
        last_deployment=last_deployment,
        deployments=deployed_artifacts,
        stats=stats,
    )


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Discover and list all projects with deployed artifacts",
    responses={
        200: {"description": "Successfully retrieved projects"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_projects(
    response: Response,
    token: TokenDep,
    cache_manager: CacheManagerDep,
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
    force_refresh: bool = Query(
        default=False,
        alias="refresh",
        description="Force cache refresh (bypass cached results)",
    ),
) -> ProjectListResponse:
    """List all projects with deployed artifacts.

    This endpoint uses a persistent SQLite cache for fast responses (<100ms).
    The cache is checked first, with fallback to ProjectRegistry if needed.
    Cache can be forced to refresh with force_refresh=true query parameter.

    Args:
        response: FastAPI Response object for headers
        token: Authentication token
        cache_manager: CacheManager dependency
        limit: Number of items per page
        after: Cursor for next page
        force_refresh: Force cache refresh

    Returns:
        Paginated list of projects with cache metadata

    Raises:
        HTTPException: On error
    """
    start_time = time.monotonic()
    cache_hit = False
    cache_last_fetched = None

    try:
        logger.info(
            f"Listing projects (limit={limit}, after={after}, force_refresh={force_refresh})"
        )

        all_projects = []

        # Try to get from persistent cache first (unless force_refresh or cache unavailable)
        if not force_refresh and cache_manager is not None:
            try:
                cached_projects = cache_manager.get_projects(include_stale=False)

                if cached_projects:
                    # We have cached data - use it
                    cache_hit = True
                    logger.info(
                        f"Cache HIT: Got {len(cached_projects)} projects from persistent cache"
                    )

                    # Convert cache entries to ProjectSummary
                    for cached_project in cached_projects:
                        try:
                            # Check if this project is stale
                            is_stale = cache_manager.is_cache_stale(cached_project.id)
                            cache_last_fetched = cached_project.last_fetched

                            # Read deployment metadata from disk to keep counts/dates accurate
                            summary_base = build_project_summary(
                                Path(cached_project.path)
                            )

                            summary = ProjectSummary(
                                id=summary_base.id,
                                path=summary_base.path,
                                name=summary_base.name,
                                deployment_count=summary_base.deployment_count,
                                last_deployment=summary_base.last_deployment,
                                cache_info=CacheInfo(
                                    cache_hit=True,
                                    last_fetched=cached_project.last_fetched,
                                    is_stale=is_stale,
                                ),
                            )
                            all_projects.append(summary)
                        except Exception as e:
                            logger.error(
                                f"Error processing cached project {cached_project.id}: {e}"
                            )
                            continue
                else:
                    logger.info("Cache MISS: No projects in persistent cache")
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve from persistent cache: {e}. Falling back to registry."
                )
        elif cache_manager is None:
            logger.info("CacheManager not available, using ProjectRegistry")

        # If no cache hit or force refresh, fall back to ProjectRegistry
        if not cache_hit or force_refresh:
            logger.info(
                f"Cache MISS or force refresh - using ProjectRegistry "
                f"(force={force_refresh})"
            )

            registry = await get_project_registry()
            cache_entries = await registry.get_projects(force_refresh=force_refresh)
            logger.info(f"Got {len(cache_entries)} projects from ProjectRegistry")

            # Convert registry entries to ProjectSummary
            for entry in cache_entries:
                try:
                    summary = ProjectSummary(
                        id=encode_project_id(str(entry.path)),
                        path=str(entry.path),
                        name=entry.name,
                        deployment_count=entry.deployment_count,
                        last_deployment=entry.last_deployment,
                        cache_info=None,  # No cache info for fresh data
                    )
                    all_projects.append(summary)
                except Exception as e:
                    logger.error(f"Error processing project {entry.path}: {e}")
                    continue

            # Populate persistent cache in the background (async)
            # This ensures future requests will hit the cache
            if cache_manager is not None:
                try:
                    projects_data = [
                        {
                            "id": encode_project_id(str(entry.path)),
                            "name": entry.name,
                            "path": str(entry.path),
                            "description": None,
                            "artifacts": [],  # TODO: Add artifact info
                        }
                        for entry in cache_entries
                    ]
                    cache_manager.populate_projects(projects_data)
                    logger.info(
                        f"Populated persistent cache with {len(projects_data)} projects"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to populate persistent cache: {e}", exc_info=True
                    )

        # Sort by last deployment (most recent first)
        all_projects.sort(
            key=lambda p: p.last_deployment or datetime.min,
            reverse=True,
        )

        # Apply pagination
        start_idx = 0
        if after:
            # Decode cursor to get project path
            cursor_path = decode_project_id(after)
            try:
                cursor_idx = next(
                    i for i, p in enumerate(all_projects) if p.path == cursor_path
                )
                start_idx = cursor_idx + 1
            except StopIteration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: project not found",
                )

        end_idx = start_idx + limit
        page_projects = all_projects[start_idx:end_idx]

        # Build pagination info
        has_next = end_idx < len(all_projects)
        has_previous = start_idx > 0

        start_cursor = page_projects[0].id if page_projects else None
        end_cursor = page_projects[-1].id if page_projects else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_projects),
        )

        # Add cache headers
        response.headers["X-Cache-Hit"] = "hit" if cache_hit else "miss"
        if cache_last_fetched:
            response.headers["X-Cache-Last-Fetched"] = cache_last_fetched.isoformat()

        # Log performance metrics
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            f"Retrieved {len(page_projects)} projects "
            f"(cache_hit={cache_hit}, time={elapsed_ms:.2f}ms)"
        )

        return ProjectListResponse(items=page_projects, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        )


@router.post(
    "",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new project",
    description="Create a new project by initializing the directory structure and metadata",
    responses={
        201: {"description": "Project created successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or project already exists",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_project(
    request: ProjectCreateRequest,
    token: TokenDep,
    cache_manager: CacheManagerDep,
) -> ProjectCreateResponse:
    """Create a new project.

    Initializes a new project by:
    1. Creating the project directory if it doesn't exist
    2. Creating the .claude subdirectory
    3. Storing project metadata
    4. Adding project to persistent cache

    Args:
        request: Project creation request with name, path, and optional description
        token: Authentication token
        cache_manager: CacheManager dependency for persistent cache updates

    Returns:
        Created project information

    Raises:
        HTTPException: If project already exists or on error

    Example:
        POST /api/v1/projects
        {
            "name": "my-project",
            "path": "/Users/john/projects/my-project",
            "description": "My awesome project"
        }

        Returns:
        {
            "id": "L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA==",
            "path": "/Users/john/projects/my-project",
            "name": "my-project",
            "description": "My awesome project",
            "created_at": "2025-11-24T12:00:00Z"
        }
    """
    try:
        logger.info(f"Creating project: {request.name} at {request.path}")

        # Convert path to Path object
        project_path = Path(request.path).resolve()

        # Check if project metadata already exists
        if ProjectMetadataStorage.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project already exists at path: {request.path}",
            )

        # Create project directory if it doesn't exist
        try:
            project_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created project directory: {project_path}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create project directory: {str(e)}",
            )

        # Create .claude subdirectory
        claude_dir = project_path / ".claude"
        try:
            claude_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created .claude directory: {claude_dir}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create .claude directory: {str(e)}",
            )

        # Create project metadata
        metadata = ProjectMetadataStorage.create_metadata(
            project_path=project_path,
            name=request.name,
            description=request.description,
        )

        # Initialize empty deployment tracking file so project is discoverable
        from skillmeat.storage.deployment import DeploymentTracker

        DeploymentTracker.write_deployments(project_path, [])

        logger.info(f"Project created successfully: {request.name}")

        # Invalidate in-memory cache so new project appears in list
        registry = await get_project_registry()
        await registry.refresh_entry(project_path)

        # Add project to persistent SQLite cache (upsert preserves other projects)
        if cache_manager is not None:
            try:
                new_project_data: dict[str, object] = {
                    "id": encode_project_id(str(project_path)),
                    "name": request.name,
                    "path": str(project_path),
                    "description": request.description,
                    "artifacts": [],
                }
                cache_manager.upsert_project(new_project_data)
                logger.info(f"Added project to persistent cache: {request.name}")
            except Exception as e:
                # Log error but don't fail - cache will be populated on next list
                logger.error(
                    f"Failed to add project to persistent cache: {e}",
                    exc_info=True,
                )

        return ProjectCreateResponse(
            id=encode_project_id(str(project_path)),
            path=str(project_path),
            name=metadata.name,
            description=metadata.description,
            created_at=metadata.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Get project details",
    description="Retrieve detailed information about a specific project including all deployments",
    responses={
        200: {"description": "Successfully retrieved project"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_project(
    project_id: str,
    token: TokenDep,
    cache_manager: CacheManagerDep,
    response: Response,
) -> ProjectDetail:
    """Get details for a specific project.

    Returns complete information about a project including all deployed
    artifacts, versions, and statistics. Checks cache first for fast response.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token
        cache_manager: CacheManager dependency
        response: FastAPI Response for headers

    Returns:
        Project details with full deployment list

    Raises:
        HTTPException: If project not found or on error
    """
    start_time = time.monotonic()
    cache_hit = False

    try:
        logger.info(f"Getting project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Try to get from cache first (if available)
        if cache_manager is not None:
            try:
                cached_project = cache_manager.get_project(project_id)
                if cached_project and not cache_manager.is_cache_stale(project_id):
                    cache_hit = True
                    logger.info(f"Cache HIT for project: {project_id}")

                    # Set cache headers
                    response.headers["X-Cache-Hit"] = "hit"
                    if cached_project.last_fetched:
                        response.headers["X-Cache-Last-Fetched"] = (
                            cached_project.last_fetched.isoformat()
                        )
            except Exception as e:
                logger.warning(f"Failed to check cache for project {project_id}: {e}")

        # Check if project exists on filesystem
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Build project detail from filesystem (always read fresh for detail view)
        project_detail = build_project_detail(project_path)

        # Set cache miss header if not hit
        if not cache_hit:
            response.headers["X-Cache-Hit"] = "miss"

        # Log performance
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            f"Retrieved project '{project_detail.name}' with "
            f"{project_detail.deployment_count} deployments "
            f"(cache_hit={cache_hit}, time={elapsed_ms:.2f}ms)"
        )

        return project_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project '{project_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}",
        )


@router.put(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Update project metadata",
    description="Update project name and/or description",
    responses={
        200: {"description": "Project updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    token: TokenDep,
) -> ProjectDetail:
    """Update project metadata.

    Updates the project's name and/or description. Only provided fields
    are updated; omitted fields remain unchanged.

    Args:
        project_id: Base64-encoded project path
        request: Project update request with optional name and description
        token: Authentication token

    Returns:
        Updated project details

    Raises:
        HTTPException: If project not found or on error

    Example:
        PUT /api/v1/projects/L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA==
        {
            "name": "renamed-project",
            "description": "Updated description"
        }

        Returns: ProjectDetail with updated metadata
    """
    try:
        logger.info(f"Updating project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Check if project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if metadata exists
        if not ProjectMetadataStorage.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project metadata not found for: {project_path.name}",
            )

        # Validate that at least one field is being updated
        if request.name is None and request.description is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field (name or description) must be provided",
            )

        # Update metadata
        updated_metadata = ProjectMetadataStorage.update_metadata(
            project_path=project_path,
            name=request.name,
            description=request.description,
        )

        if updated_metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to update project metadata",
            )

        logger.info(f"Project updated successfully: {updated_metadata.name}")

        # Refresh cache entry
        registry = await get_project_registry()
        await registry.refresh_entry(project_path)

        # Build and return updated project detail
        project_detail = build_project_detail(project_path)
        return project_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project '{project_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.delete(
    "/{project_id}",
    response_model=ProjectDeleteResponse,
    summary="Delete project",
    description="Remove project from tracking and optionally delete files from disk",
    responses={
        200: {"description": "Project deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_project(
    project_id: str,
    token: TokenDep,
    delete_files: bool = Query(
        default=False,
        description="If true, delete project files from disk (WARNING: destructive operation)",
    ),
) -> ProjectDeleteResponse:
    """Delete a project.

    Removes project metadata from tracking. By default, this only removes
    the tracking metadata and leaves the project files intact. Set
    delete_files=true to also delete the project directory from disk.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token
        delete_files: Whether to delete project files from disk (default: False)

    Returns:
        Deletion status and message

    Raises:
        HTTPException: If project not found or on error

    Example:
        DELETE /api/v1/projects/L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA==?delete_files=false

        Returns:
        {
            "success": true,
            "message": "Project removed from tracking successfully",
            "deleted_files": false
        }
    """
    try:
        logger.info(f"Deleting project: {project_id} (delete_files={delete_files})")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Check if project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if metadata exists
        if not ProjectMetadataStorage.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project metadata not found for: {project_path.name}",
            )

        # Delete metadata file
        metadata_deleted = ProjectMetadataStorage.delete_metadata(project_path)

        message = "Project removed from tracking successfully"
        files_deleted = False

        # Optionally delete project files
        if delete_files:
            try:
                import shutil

                shutil.rmtree(project_path)
                message = "Project and all files deleted successfully"
                files_deleted = True
                logger.warning(f"Deleted project directory: {project_path}")
            except Exception as e:
                logger.error(f"Failed to delete project files: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete project files: {str(e)}",
                )

        logger.info(f"Project deleted successfully: {project_path.name}")

        # Invalidate cache entry
        registry = await get_project_registry()
        await registry.invalidate(project_path)

        return ProjectDeleteResponse(
            success=True,
            message=message,
            deleted_files=files_deleted,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project '{project_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        )


@router.delete(
    "/{project_id}/deployments/{artifact_name}",
    response_model=ProjectDeploymentRemovalResponse,
    summary="Remove deployment from project",
    description="Remove a specific artifact deployment from a project",
    responses={
        200: {"description": "Deployment removed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project or deployment not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def remove_project_deployment(
    project_id: str,
    artifact_name: str,
    token: TokenDep,
    artifact_type: str = Query(
        description="Type of the artifact to remove",
        examples=["skill"],
    ),
    remove_files: bool = Query(
        default=True,
        description="Whether to remove files from filesystem (default: True)",
    ),
) -> ProjectDeploymentRemovalResponse:
    """Remove a deployed artifact from a specific project.

    This endpoint removes an artifact deployment from a specific project,
    including:
    - Removing from SkillMeat system tracking
    - Optionally removing files from local filesystem at project path

    The operation only affects the specific project deployment and leaves:
    - The collection artifact intact
    - Other project deployments of the same artifact intact

    Args:
        project_id: Base64-encoded project path
        artifact_name: Name of the artifact to remove
        request: Deployment removal request with artifact details and options
        token: Authentication token

    Returns:
        ProjectDeploymentRemovalResponse with removal status

    Raises:
        HTTPException: If project not found, deployment not found, or on error

    Example:
        DELETE /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/deployments/pdf-processor?artifact_type=skill&remove_files=true

        Returns:
        {
            "success": true,
            "message": "Artifact 'pdf-processor' removed from project successfully",
            "artifact_name": "pdf-processor",
            "artifact_type": "skill",
            "project_path": "/Users/me/project1",
            "files_removed": true
        }
    """
    try:
        logger.info(
            f"Removing deployment: {artifact_name} "
            f"({artifact_type}) from project {project_id}"
        )

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Validate artifact type
        try:
            from skillmeat.core.artifact import ArtifactType
            artifact_type_enum = ArtifactType(artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact type: {artifact_type}",
            )

        # Check if deployment exists
        deployment = DeploymentTracker.get_deployment(
            project_path, artifact_name, artifact_type
        )

        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment '{artifact_name}' ({artifact_type}) not found in project",
            )

        # Track the artifact info before removal
        artifact_path = project_path / ".claude" / deployment.artifact_path
        files_existed = artifact_path.exists()

        # Perform the removal - handle files separately based on remove_files option
        files_removed = False
        try:
            # Remove files from filesystem if requested and they exist
            if remove_files and files_existed:
                from skillmeat.utils.filesystem import FilesystemManager
                fs_mgr = FilesystemManager()
                fs_mgr.remove_artifact(artifact_path)
                files_removed = True
                logger.info(
                    f"Removed files: {artifact_path} "
                    f"(artifact: {artifact_name}, type: {artifact_type})"
                )

            # Always remove deployment record from tracking
            DeploymentTracker.remove_deployment(
                project_path, artifact_name, artifact_type
            )
            logger.info(
                f"Removed deployment record: {artifact_name} "
                f"({artifact_type}) from {project_path}"
            )

            # Track remove event for analytics
            try:
                from skillmeat.core.analytics import EventTracker

                with EventTracker() as tracker:
                    tracker.track_remove(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type,
                        collection_name=deployment.from_collection,
                        reason="user_action",
                        from_project=True,
                    )
            except Exception as e:
                # Never fail undeploy due to analytics
                logger.warning(f"Failed to record remove analytics: {e}")

            # files_removed already set based on actual operation

            # Update project cache
            registry = await get_project_registry()
            await registry.refresh_entry(project_path)

            response = ProjectDeploymentRemovalResponse(
                success=True,
                message=f"Artifact '{artifact_name}' removed from project successfully",
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                project_path=str(project_path),
                files_removed=files_removed,
            )

            logger.info(
                f"Successfully removed deployment: {artifact_name} "
                f"({artifact_type}) from {project_path}"
            )
            return response

        except ValueError as e:
            # Deployment not found or other validation error
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(
            f"Error removing deployment '{artifact_name}' from project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove deployment: {str(e)}",
        )


@router.post(
    "/{project_id}/check-modifications",
    response_model=ModificationCheckResponse,
    summary="Check for artifact modifications",
    description="Scan all deployments in a project and detect local modifications by comparing content hashes",
    responses={
        200: {"description": "Successfully checked for modifications"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def check_project_modifications(
    project_id: str,
    token: TokenDep,
) -> ModificationCheckResponse:
    """Check for modifications in all deployed artifacts.

    Uses drift detection to properly identify change origins (local_modification,
    sync, or deployment) and track modification timestamps.

    This operation updates the deployment metadata with modification
    timestamps when changes are first detected.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token

    Returns:
        Modification check results with status and change origin for each deployment

    Raises:
        HTTPException: If project not found or on error

    Example:
        POST /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/check-modifications

        Returns:
        {
            "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
            "checked_at": "2025-11-20T16:00:00Z",
            "modifications_detected": 2,
            "deployments": [
                {
                    "artifact_name": "pdf-processor",
                    "artifact_type": "skill",
                    "deployed_sha": "abc123...",
                    "current_sha": "def456...",
                    "is_modified": true,
                    "modification_detected_at": "2025-11-20T15:45:00Z",
                    "change_origin": "local_modification"
                }
            ]
        }
    """
    try:
        logger.info(f"Checking modifications for project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Use sync manager to check drift - this provides proper change_origin detection
        from skillmeat.core.sync import SyncManager

        sync_mgr = SyncManager(
            collection_path=Path.home() / ".skillmeat" / "collection"
        )

        try:
            drift_results = sync_mgr.check_drift(project_path=project_path)
        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check drift: {str(e)}",
            )

        # Convert drift results to modification statuses
        modification_statuses: List[DeploymentModificationStatus] = []
        modifications_count = 0
        checked_at = datetime.now(timezone.utc)

        for drift in drift_results:
            # Skip artifacts that were added or removed (not relevant for modification check)
            if drift.drift_type in ("added", "removed"):
                continue

            # Determine if artifact is modified
            is_modified = drift.drift_type in ("modified", "conflict")

            if is_modified:
                modifications_count += 1

            # Parse modification timestamp if present
            modification_detected_at = None
            if drift.modification_detected_at:
                try:
                    modification_detected_at = datetime.fromisoformat(
                        drift.modification_detected_at.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            modification_statuses.append(
                DeploymentModificationStatus(
                    artifact_name=drift.artifact_name,
                    artifact_type=drift.artifact_type,
                    deployed_sha=drift.baseline_hash or drift.collection_sha or "",
                    current_sha=drift.current_hash or drift.project_sha or "",
                    is_modified=is_modified,
                    modification_detected_at=modification_detected_at,
                    change_origin=drift.change_origin,  # From DriftDetectionResult
                    baseline_hash=drift.baseline_hash,
                )
            )

        logger.info(
            f"Modification check complete: {modifications_count} of {len(modification_statuses)} artifacts modified"
        )

        return ModificationCheckResponse(
            project_id=project_id,
            checked_at=checked_at,
            modifications_detected=modifications_count,
            deployments=modification_statuses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error checking modifications for project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check modifications: {str(e)}",
        )


@router.get(
    "/{project_id}/modified-artifacts",
    response_model=ModifiedArtifactsResponse,
    summary="Get modified artifacts",
    description="List all artifacts in a project that have been modified since deployment",
    responses={
        200: {"description": "Successfully retrieved modified artifacts"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_modified_artifacts(
    project_id: str,
    token: TokenDep,
) -> ModifiedArtifactsResponse:
    """Get list of all modified artifacts in a project.

    Uses drift detection to properly identify change origins and
    filter for modified artifacts only.

    Note: This performs a live drift check. Results are not cached between calls.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token

    Returns:
        List of modified artifacts with change origin and hashes

    Raises:
        HTTPException: If project not found or on error

    Example:
        GET /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/modified-artifacts

        Returns:
        {
            "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
            "modified_artifacts": [
                {
                    "artifact_name": "pdf-processor",
                    "artifact_type": "skill",
                    "deployed_sha": "abc123...",
                    "current_sha": "def456...",
                    "modification_detected_at": "2025-11-20T15:45:00Z",
                    "change_origin": "local_modification"
                }
            ],
            "total_count": 2,
            "last_checked": "2025-11-20T16:00:00Z"
        }
    """
    try:
        logger.info(f"Getting modified artifacts for project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Use sync manager to check drift - provides proper change_origin
        from skillmeat.core.sync import SyncManager

        sync_mgr = SyncManager(
            collection_path=Path.home() / ".skillmeat" / "collection"
        )

        try:
            drift_results = sync_mgr.check_drift(project_path=project_path)
        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check drift: {str(e)}",
            )

        # Filter for modified artifacts only
        from skillmeat.api.schemas.projects import ModifiedArtifactInfo

        modified_artifacts: List[ModifiedArtifactInfo] = []
        checked_at = datetime.now(timezone.utc)

        for drift in drift_results:
            # Only include artifacts that are modified or in conflict
            if drift.drift_type not in ("modified", "conflict"):
                continue

            # Parse modification timestamp if present
            modification_detected_at = None
            if drift.modification_detected_at:
                try:
                    modification_detected_at = datetime.fromisoformat(
                        drift.modification_detected_at.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            modified_artifacts.append(
                ModifiedArtifactInfo(
                    artifact_name=drift.artifact_name,
                    artifact_type=drift.artifact_type,
                    deployed_sha=drift.baseline_hash or drift.collection_sha or "",
                    current_sha=drift.current_hash or drift.project_sha or "",
                    modification_detected_at=modification_detected_at,
                    change_origin=drift.change_origin,  # From DriftDetectionResult
                    baseline_hash=drift.baseline_hash,
                )
            )

        logger.info(
            f"Found {len(modified_artifacts)} modified artifacts in project '{project_path.name}'"
        )

        return ModifiedArtifactsResponse(
            project_id=project_id,
            modified_artifacts=modified_artifacts,
            total_count=len(modified_artifacts),
            last_checked=checked_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting modified artifacts for project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get modified artifacts: {str(e)}",
        )


@router.get(
    "/{project_id}/context-map",
    response_model=ContextMapResponse,
    summary="Discover context entities in project",
    description=(
        "Scan a project's .claude/ directory to discover context entities "
        "(specs, rules, context files) with token estimates for progressive disclosure"
    ),
    responses={
        200: {"description": "Successfully discovered context entities"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_project_context_map(
    project_id: str,
    token: TokenDep,
) -> ContextMapResponse:
    """Discover context entities in a project's .claude/ directory.

    Scans the project for context entities and categorizes them by auto-loading
    behavior for progressive disclosure patterns:

    - **Auto-loaded**: Specs and rules that load based on path patterns
    - **On-demand**: Context files that load only when explicitly requested

    Token estimates are calculated as: word_count * 1.3

    Args:
        project_id: Base64-encoded project path
        token: Authentication token

    Returns:
        Context map with categorized entities and token estimates

    Raises:
        HTTPException: If project not found or on error

    Example:
        GET /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/context-map

        Returns:
        {
            "auto_loaded": [
                {
                    "type": "spec_file",
                    "name": "doc-policy-spec",
                    "path": ".claude/specs/doc-policy-spec.md",
                    "tokens": 800,
                    "auto_load": true
                }
            ],
            "on_demand": [
                {
                    "type": "context_file",
                    "name": "api-endpoint-mapping",
                    "path": ".claude/context/api-endpoint-mapping.md",
                    "tokens": 3000,
                    "auto_load": false
                }
            ],
            "total_auto_load_tokens": 800
        }
    """
    try:
        logger.info(f"Discovering context entities for project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Initialize response containers
        auto_loaded: List[ContextEntityInfo] = []
        on_demand: List[ContextEntityInfo] = []
        total_auto_load_tokens = 0

        # Check if .claude directory exists
        claude_dir = project_path / ".claude"
        if not claude_dir.exists():
            logger.info(f"No .claude directory found for project: {project_path.name}")
            return ContextMapResponse(
                auto_loaded=[],
                on_demand=[],
                total_auto_load_tokens=0,
            )

        def estimate_tokens(content: str) -> int:
            """Estimate token count from content.

            Args:
                content: File content to estimate

            Returns:
                Estimated token count
            """
            word_count = len(content.split())
            return int(word_count * 1.3)

        def extract_name_from_path(file_path: Path) -> str:
            """Extract entity name from file path.

            Args:
                file_path: Path to the file

            Returns:
                Name derived from file path (without extension)
            """
            return file_path.stem

        # Scan .claude/specs/*.md (auto-loaded)
        specs_dir = claude_dir / "specs"
        if specs_dir.exists() and specs_dir.is_dir():
            for spec_file in specs_dir.glob("*.md"):
                try:
                    content = spec_file.read_text(encoding="utf-8")
                    tokens = estimate_tokens(content)
                    relative_path = spec_file.relative_to(project_path)

                    entity = ContextEntityInfo(
                        type="spec_file",
                        name=extract_name_from_path(spec_file),
                        path=str(relative_path),
                        tokens=tokens,
                        auto_load=True,
                    )
                    auto_loaded.append(entity)
                    total_auto_load_tokens += tokens
                except Exception as e:
                    logger.warning(f"Failed to read spec file {spec_file}: {e}")
                    continue

        # Scan .claude/rules/**/*.md (auto-loaded)
        rules_dir = claude_dir / "rules"
        if rules_dir.exists() and rules_dir.is_dir():
            for rule_file in rules_dir.rglob("*.md"):
                try:
                    content = rule_file.read_text(encoding="utf-8")
                    tokens = estimate_tokens(content)
                    relative_path = rule_file.relative_to(project_path)

                    # Create name from path (e.g., web/api-client -> web-api-client)
                    rule_path_parts = rule_file.relative_to(rules_dir).parts
                    if len(rule_path_parts) > 1:
                        # Include parent directory in name
                        name = "-".join(
                            [rule_path_parts[-2], extract_name_from_path(rule_file)]
                        )
                    else:
                        name = extract_name_from_path(rule_file)

                    entity = ContextEntityInfo(
                        type="rule_file",
                        name=name,
                        path=str(relative_path),
                        tokens=tokens,
                        auto_load=True,
                    )
                    auto_loaded.append(entity)
                    total_auto_load_tokens += tokens
                except Exception as e:
                    logger.warning(f"Failed to read rule file {rule_file}: {e}")
                    continue

        # Scan .claude/context/*.md (on-demand)
        context_dir = claude_dir / "context"
        if context_dir.exists() and context_dir.is_dir():
            for context_file in context_dir.glob("*.md"):
                try:
                    content = context_file.read_text(encoding="utf-8")
                    tokens = estimate_tokens(content)
                    relative_path = context_file.relative_to(project_path)

                    entity = ContextEntityInfo(
                        type="context_file",
                        name=extract_name_from_path(context_file),
                        path=str(relative_path),
                        tokens=tokens,
                        auto_load=False,
                    )
                    on_demand.append(entity)
                except Exception as e:
                    logger.warning(f"Failed to read context file {context_file}: {e}")
                    continue

        logger.info(
            f"Discovered {len(auto_loaded)} auto-loaded and {len(on_demand)} on-demand "
            f"context entities for project '{project_path.name}' "
            f"(total auto-load tokens: {total_auto_load_tokens})"
        )

        return ContextMapResponse(
            auto_loaded=auto_loaded,
            on_demand=on_demand,
            total_auto_load_tokens=total_auto_load_tokens,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error discovering context entities for project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover context entities: {str(e)}",
        )


# =============================================================================
# Drift Detection Endpoints
# =============================================================================


def calculate_drift_summary(
    project_path: str,
    collection_name: str,
    drift_results: List,
) -> DriftSummaryResponse:
    """Calculate drift summary counts from drift detection results.

    Args:
        project_path: Path to the project directory
        collection_name: Name of the collection being compared
        drift_results: List of DriftDetectionResult objects

    Returns:
        DriftSummaryResponse with calculated summary counts

    Note:
        This helper function implements TASK-4.3 summary count calculation:
        - upstream_changes: Count of "outdated", "added", "removed" drift
        - local_changes: Count of "modified" drift
        - conflicts: Count of "conflict" drift
        - total: Total artifacts with drift
    """
    from skillmeat.models import DriftDetectionResult

    # Initialize counters
    upstream_changes = 0
    local_changes = 0
    conflicts = 0
    modified_count = 0
    outdated_count = 0
    conflict_count = 0
    added_count = 0
    removed_count = 0
    version_mismatch_count = 0

    # Count by drift type
    for drift in drift_results:
        drift_type = drift.drift_type

        # Update summary counts (TASK-4.3)
        if drift_type in ("outdated", "added", "removed"):
            upstream_changes += 1
        elif drift_type == "modified":
            local_changes += 1
        elif drift_type == "conflict":
            conflicts += 1

        # Update individual type counts
        if drift_type == "modified":
            modified_count += 1
        elif drift_type == "outdated":
            outdated_count += 1
        elif drift_type == "conflict":
            conflict_count += 1
        elif drift_type == "added":
            added_count += 1
        elif drift_type == "removed":
            removed_count += 1
        elif drift_type == "version_mismatch":
            version_mismatch_count += 1

    # Convert DriftDetectionResult to DriftDetectionResponse
    drift_details = [
        DriftDetectionResponse(
            artifact_name=d.artifact_name,
            artifact_type=d.artifact_type,
            drift_type=d.drift_type,
            collection_sha=d.collection_sha,
            project_sha=d.project_sha,
            collection_version=d.collection_version,
            project_version=d.project_version,
            last_deployed=d.last_deployed,
            recommendation=d.recommendation,
            change_origin=d.change_origin,
            baseline_hash=d.baseline_hash,
            current_hash=d.current_hash,
            modification_detected_at=d.modification_detected_at,
        )
        for d in drift_results
    ]

    return DriftSummaryResponse(
        project_path=project_path,
        collection_name=collection_name,
        total_artifacts=len(drift_results),
        drifted_count=len(drift_results),
        modified_count=modified_count,
        outdated_count=outdated_count,
        conflict_count=conflict_count,
        added_count=added_count,
        removed_count=removed_count,
        version_mismatch_count=version_mismatch_count,
        upstream_changes=upstream_changes,
        local_changes=local_changes,
        conflicts=conflicts,
        total=len(drift_results),
        drift_details=drift_details,
        checked_at=datetime.now(timezone.utc),
    )


@router.get(
    "/{project_id}/drift/summary",
    response_model=DriftSummaryResponse,
    summary="Get drift detection summary",
    description="Detect drift between project and collection with summary counts",
    responses={
        200: {"description": "Successfully detected drift"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_project_drift_summary(
    project_id: str,
    token: TokenDep,
    collection_name: Optional[str] = Query(
        default=None,
        description="Collection name to compare against (defaults to deployed collection)",
    ),
) -> DriftSummaryResponse:
    """Get drift detection summary for a project.

    Detects drift between deployed artifacts and collection state, returning
    summary counts for:
    - upstream_changes: Changes from collection (outdated, added, removed)
    - local_changes: Local modifications in project
    - conflicts: Both local and upstream changes
    - total: Total artifacts with drift

    This endpoint implements TASK-4.3 drift summary counts.

    Args:
        project_id: Base64-encoded project path
        token: Authentication token
        collection_name: Optional collection name override

    Returns:
        Drift summary with counts and detailed drift information

    Raises:
        HTTPException: If project not found or on error

    Example:
        GET /api/v1/projects/L1VzZXJzL21lL3Byb2plY3Qx/drift/summary

        Returns:
        {
            "project_path": "/Users/me/project1",
            "collection_name": "default",
            "upstream_changes": 2,
            "local_changes": 1,
            "conflicts": 0,
            "total": 3,
            "drift_details": [...]
        }
    """
    try:
        logger.info(f"Getting drift summary for project: {project_id}")

        # Decode project ID to path
        project_path_str = decode_project_id(project_id)
        project_path = Path(project_path_str)

        # Validate project exists
        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found at path: {project_path_str}",
            )

        # Check if deployment file exists
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)
        if not deployment_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deployments found for project: {project_path.name}",
            )

        # Get SyncManager from app state
        from skillmeat.api.dependencies import app_state

        if not hasattr(app_state, "sync_manager") or app_state.sync_manager is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SyncManager not available",
            )

        sync_manager = app_state.sync_manager

        # Detect drift
        drift_results = sync_manager.check_drift(
            project_path=project_path,
            collection_name=collection_name,
        )

        # Calculate summary
        summary = calculate_drift_summary(
            project_path=str(project_path),
            collection_name=collection_name or "default",
            drift_results=drift_results,
        )

        logger.info(
            f"Drift summary: {summary.upstream_changes} upstream, "
            f"{summary.local_changes} local, {summary.conflicts} conflicts"
        )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting drift summary for project '{project_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get drift summary: {str(e)}",
        )


# =============================================================================
# Cache Management Endpoints
# =============================================================================


@router.post(
    "/cache/clear",
    summary="Clear project cache",
    description="Clear the persistent SQLite cache and force full project rediscovery",
    responses={
        200: {"description": "Cache cleared successfully"},
        500: {"description": "Cache manager not available"},
    },
)
async def clear_project_cache(
    token: TokenDep,
    cache_manager: CacheManagerDep,
) -> dict:
    """Clear persistent project cache and force rediscovery.

    This clears the SQLite cache and triggers a full filesystem scan
    to rediscover all projects. Use when cache is out of sync with disk.

    Args:
        token: Authentication token
        cache_manager: CacheManager dependency

    Returns:
        Cache clear status with project count after rediscovery
    """
    if cache_manager is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache manager not available",
        )

    try:
        # Clear SQLite project cache
        cleared = cache_manager.clear_cache()
        if not cleared:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear cache",
            )

        # Force ProjectRegistry refresh to rediscover projects
        registry = await get_project_registry()
        discovered = await registry.get_projects(force_refresh=True)

        # Repopulate cache with fresh data
        projects_data = [
            {
                "id": encode_project_id(str(entry.path)),
                "name": entry.name,
                "path": str(entry.path),
                "description": None,
                "artifacts": [],
            }
            for entry in discovered
        ]
        cache_manager.populate_projects(projects_data)

        logger.info(
            f"Cleared project cache and rediscovered {len(discovered)} projects"
        )

        return {
            "success": True,
            "message": f"Cache cleared and {len(discovered)} projects rediscovered",
            "projects_found": len(discovered),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to clear project cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


@router.post(
    "/cache/refresh",
    summary="Refresh project cache",
    description="Force a full refresh of the project discovery cache",
    responses={
        200: {"description": "Cache refreshed successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def refresh_cache(token: TokenDep) -> dict:
    """Force refresh the project discovery cache.

    Triggers a full filesystem scan to update the cached project list.
    This is useful after making changes outside the API or if the cache
    seems stale.

    Args:
        token: Authentication token

    Returns:
        Cache status after refresh
    """
    try:
        logger.info("Forcing project cache refresh")
        registry = await get_project_registry()
        await registry.get_projects(force_refresh=True)
        stats = registry.get_cache_stats()
        logger.info(f"Cache refreshed: {stats['entries']} projects")
        return {
            "success": True,
            "message": "Cache refreshed successfully",
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh cache: {str(e)}",
        )


@router.get(
    "/cache/stats",
    summary="Get cache statistics",
    description="Get statistics about the project discovery cache",
    responses={
        200: {"description": "Cache statistics"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_cache_stats(token: TokenDep) -> dict:
    """Get cache statistics for monitoring.

    Returns information about the cache state including number of entries,
    age, and validity status.

    Args:
        token: Authentication token

    Returns:
        Cache statistics
    """
    registry = await get_project_registry()
    return registry.get_cache_stats()
