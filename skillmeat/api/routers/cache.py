"""Cache management API endpoints.

Provides REST API for cache operations including refresh, invalidation,
and status queries.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import get_app_state, verify_api_key
from skillmeat.api.schemas.cache import (
    CacheInvalidateRequest,
    CacheInvalidateResponse,
    CacheRefreshRequest,
    CacheRefreshResponse,
    CacheStatusResponse,
    CachedArtifactResponse,
    CachedArtifactsListResponse,
    CachedProjectResponse,
    CachedProjectsListResponse,
    MarketplaceEntryResponse,
    MarketplaceListResponse,
    RefreshJobStatus,
    SearchResult,
    SearchResultsResponse,
    StaleArtifactResponse,
    StaleArtifactsListResponse,
)
from skillmeat.cache.manager import CacheManager
from skillmeat.cache.refresh import RefreshJob

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cache",
    tags=["cache"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


# =============================================================================
# Dependency Injection
# =============================================================================


def get_cache_manager(
    state: Annotated[object, Depends(get_app_state)],
) -> CacheManager:
    """Get CacheManager dependency.

    Args:
        state: Application state

    Returns:
        CacheManager instance

    Raises:
        HTTPException: If CacheManager not available
    """
    # Initialize cache manager if not exists
    if not hasattr(state, "cache_manager") or state.cache_manager is None:
        # Initialize with default settings
        cache_manager = CacheManager(ttl_minutes=360)  # 6 hours default TTL
        cache_manager.initialize_cache()
        state.cache_manager = cache_manager

    return state.cache_manager


def get_refresh_job(
    cache_manager: Annotated[CacheManager, Depends(get_cache_manager)],
    state: Annotated[object, Depends(get_app_state)],
) -> RefreshJob:
    """Get RefreshJob dependency.

    Args:
        cache_manager: CacheManager instance
        state: Application state

    Returns:
        RefreshJob instance
    """
    # Initialize refresh job if not exists
    if not hasattr(state, "refresh_job") or state.refresh_job is None:
        refresh_job = RefreshJob(
            cache_manager=cache_manager,
            interval_hours=6.0,
            max_concurrent=3,
        )
        state.refresh_job = refresh_job

    return state.refresh_job


# Type aliases for cleaner dependency injection
CacheManagerDep = Annotated[CacheManager, Depends(get_cache_manager)]
RefreshJobDep = Annotated[RefreshJob, Depends(get_refresh_job)]


# =============================================================================
# Cache Refresh Endpoints
# =============================================================================


@router.post(
    "/refresh",
    response_model=CacheRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger cache refresh",
    description=(
        "Manually trigger cache refresh for all projects or a specific project. "
        "By default, only refreshes stale projects (past TTL). "
        "Use force=true to refresh regardless of staleness."
    ),
)
async def refresh_cache(
    request: CacheRefreshRequest,
    refresh_job: RefreshJobDep,
) -> CacheRefreshResponse:
    """Trigger manual cache refresh.

    Args:
        request: Refresh request parameters
        refresh_job: RefreshJob dependency

    Returns:
        Refresh operation result

    Raises:
        HTTPException: On refresh failure
    """
    try:
        logger.info(
            f"Manual refresh triggered (project_id={request.project_id}, "
            f"force={request.force})"
        )

        # Perform refresh
        if request.project_id:
            # Refresh specific project
            result = refresh_job.refresh_project(
                project_id=request.project_id,
                force=request.force,
            )
        else:
            # Refresh all projects
            result = refresh_job.refresh_all(force=request.force)

        # Build response
        message = "Refresh completed successfully"
        if not result.success:
            message = f"Refresh completed with errors: {'; '.join(result.errors)}"

        return CacheRefreshResponse(
            success=result.success,
            projects_refreshed=result.projects_refreshed,
            changes_detected=result.changes_detected,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
            message=message,
        )

    except Exception as e:
        logger.error(f"Cache refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refresh failed: {str(e)}",
        )


# =============================================================================
# Cache Status Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=CacheStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get cache status",
    description=(
        "Get comprehensive cache statistics including project/artifact counts, "
        "staleness information, and refresh job status."
    ),
)
async def get_cache_status(
    cache_manager: CacheManagerDep,
    refresh_job: RefreshJobDep,
) -> CacheStatusResponse:
    """Get cache statistics and status.

    Args:
        cache_manager: CacheManager dependency
        refresh_job: RefreshJob dependency

    Returns:
        Cache status information

    Raises:
        HTTPException: On status retrieval failure
    """
    try:
        # Get cache statistics
        cache_stats = cache_manager.get_cache_status()

        # Get refresh job status
        job_status = refresh_job.get_refresh_status()

        return CacheStatusResponse(
            total_projects=cache_stats["total_projects"],
            total_artifacts=cache_stats["total_artifacts"],
            stale_projects=cache_stats["stale_projects"],
            outdated_artifacts=cache_stats["outdated_artifacts"],
            cache_size_bytes=cache_stats["cache_size_bytes"],
            oldest_entry=cache_stats.get("oldest_entry"),
            newest_entry=cache_stats.get("newest_entry"),
            last_refresh=cache_stats.get("last_refresh"),
            refresh_job_status=RefreshJobStatus(
                is_running=job_status["is_running"],
                next_run_time=job_status.get("next_run_time"),
                last_run_time=job_status.get("last_run_time"),
            ),
        )

    except Exception as e:
        logger.error(f"Failed to get cache status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache status: {str(e)}",
        )


# =============================================================================
# Project Endpoints
# =============================================================================


@router.get(
    "/projects",
    response_model=CachedProjectsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List cached projects",
    description="Get list of cached projects with optional filtering by status.",
)
async def list_cached_projects(
    cache_manager: CacheManagerDep,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status (active, stale, error)",
        examples=["active"],
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of items to skip",
        examples=[0],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum items to return",
        examples=[100],
    ),
) -> CachedProjectsListResponse:
    """List cached projects.

    Args:
        cache_manager: CacheManager dependency
        status_filter: Optional status filter
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        Paginated list of cached projects

    Raises:
        HTTPException: On retrieval failure
    """
    try:
        # Get all projects
        all_projects = cache_manager.get_projects(include_stale=True)

        # Apply status filter if specified
        if status_filter:
            if status_filter == "stale":
                # Get stale project IDs
                stale_ids = {
                    p.id for p in all_projects if cache_manager.is_cache_stale(p.id)
                }
                filtered_projects = [p for p in all_projects if p.id in stale_ids]
            else:
                # Filter by status field
                filtered_projects = [
                    p for p in all_projects if p.status == status_filter
                ]
        else:
            filtered_projects = all_projects

        total = len(filtered_projects)

        # Apply pagination
        paginated_projects = filtered_projects[skip : skip + limit]

        # Convert to response schema
        items = [
            CachedProjectResponse(
                id=p.id,
                name=p.name,
                path=p.path,
                status=p.status,
                last_fetched=p.last_fetched,
                artifact_count=len(p.artifacts),
            )
            for p in paginated_projects
        ]

        return CachedProjectsListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Failed to list cached projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        )


# =============================================================================
# Artifact Endpoints
# =============================================================================


@router.get(
    "/artifacts",
    response_model=CachedArtifactsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List cached artifacts",
    description=(
        "Get list of cached artifacts with optional filtering by project, "
        "type, or outdated status."
    ),
)
async def list_cached_artifacts(
    cache_manager: CacheManagerDep,
    project_id: Optional[str] = Query(
        None,
        description="Filter by project ID",
        examples=["proj-1"],
    ),
    artifact_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by artifact type",
        examples=["skill"],
    ),
    is_outdated: Optional[bool] = Query(
        None,
        description="Filter by outdated status",
        examples=[True],
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of items to skip",
        examples=[0],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum items to return",
        examples=[100],
    ),
) -> CachedArtifactsListResponse:
    """List cached artifacts.

    Args:
        cache_manager: CacheManager dependency
        project_id: Optional project ID filter
        artifact_type: Optional artifact type filter
        is_outdated: Optional outdated status filter
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        Paginated list of cached artifacts

    Raises:
        HTTPException: On retrieval failure
    """
    try:
        # Get artifacts based on project filter
        if project_id:
            # Get artifacts for specific project
            all_artifacts = cache_manager.get_artifacts(project_id)
        else:
            # Get all artifacts across all projects
            all_projects = cache_manager.get_projects(include_stale=True)
            all_artifacts = []
            for project in all_projects:
                all_artifacts.extend(cache_manager.get_artifacts(project.id))

        # Apply filters
        filtered_artifacts = all_artifacts

        if artifact_type:
            filtered_artifacts = [
                a for a in filtered_artifacts if a.type == artifact_type
            ]

        if is_outdated is not None:
            filtered_artifacts = [
                a for a in filtered_artifacts if a.is_outdated == is_outdated
            ]

        total = len(filtered_artifacts)

        # Apply pagination
        paginated_artifacts = filtered_artifacts[skip : skip + limit]

        # Convert to response schema
        items = [
            CachedArtifactResponse(
                id=a.id,
                name=a.name,
                type=a.type,
                project_id=a.project_id,
                deployed_version=a.deployed_version,
                upstream_version=a.upstream_version,
                is_outdated=a.is_outdated,
            )
            for a in paginated_artifacts
        ]

        return CachedArtifactsListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Failed to list cached artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifacts: {str(e)}",
        )


@router.get(
    "/stale-artifacts",
    response_model=StaleArtifactsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List outdated artifacts",
    description="Get list of artifacts that have newer upstream versions available with sorting and filtering.",
)
async def list_stale_artifacts(
    cache_manager: CacheManagerDep,
    artifact_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by artifact type",
        examples=["skill"],
    ),
    project_id: Optional[str] = Query(
        None,
        description="Filter by project ID",
        examples=["proj-1"],
    ),
    sort_by: str = Query(
        "name",
        description="Sort field (name, type, project, version_diff)",
        examples=["name"],
    ),
    sort_order: str = Query(
        "asc",
        description="Sort order (asc, desc)",
        examples=["asc"],
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of items to skip",
        examples=[0],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum items to return",
        examples=[100],
    ),
) -> StaleArtifactsListResponse:
    """List outdated artifacts with sorting and filtering.

    Args:
        cache_manager: CacheManager dependency
        artifact_type: Optional artifact type filter
        project_id: Optional project ID filter
        sort_by: Field to sort by (name, type, project, version_diff)
        sort_order: Sort order (asc, desc)
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        List of outdated artifacts

    Raises:
        HTTPException: On retrieval failure or invalid sort parameters
    """
    try:
        # Import version comparison utility
        from skillmeat.cache.version_utils import VersionComparator

        # Get outdated artifacts
        outdated_artifacts = cache_manager.get_outdated_artifacts()

        # Apply type filter if specified
        if artifact_type:
            outdated_artifacts = [
                a for a in outdated_artifacts if a.type == artifact_type
            ]

        # Apply project filter if specified
        if project_id:
            outdated_artifacts = [
                a for a in outdated_artifacts if a.project_id == project_id
            ]

        # Build artifact data with project info and version diff
        artifact_data = []
        for artifact in outdated_artifacts:
            project = cache_manager.get_project(artifact.project_id)
            project_name = project.name if project else "Unknown"

            # Calculate version difference
            version_diff = None
            if artifact.deployed_version and artifact.upstream_version:
                version_diff = VersionComparator.get_version_difference(
                    artifact.deployed_version, artifact.upstream_version
                )

            artifact_data.append(
                {
                    "artifact": artifact,
                    "project_name": project_name,
                    "version_diff": version_diff,
                }
            )

        # Sort artifacts
        reverse = sort_order.lower() == "desc"

        if sort_by == "name":
            artifact_data.sort(
                key=lambda x: x["artifact"].name.lower(),
                reverse=reverse,
            )
        elif sort_by == "type":
            artifact_data.sort(
                key=lambda x: x["artifact"].type,
                reverse=reverse,
            )
        elif sort_by == "project":
            artifact_data.sort(
                key=lambda x: x["project_name"].lower(),
                reverse=reverse,
            )
        elif sort_by == "version_diff":
            # Sort by version difference (nulls last)
            artifact_data.sort(
                key=lambda x: (
                    x["version_diff"] is None,
                    x["version_diff"] or "",
                ),
                reverse=reverse,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field: {sort_by}. "
                "Valid options: name, type, project, version_diff",
            )

        total = len(artifact_data)

        # Apply pagination
        paginated_data = artifact_data[skip : skip + limit]

        # Convert to response schema
        items = []
        for data in paginated_data:
            artifact = data["artifact"]
            items.append(
                StaleArtifactResponse(
                    id=artifact.id,
                    name=artifact.name,
                    type=artifact.type,
                    project_name=data["project_name"],
                    project_id=artifact.project_id,
                    deployed_version=artifact.deployed_version,
                    upstream_version=artifact.upstream_version,
                    version_difference=data["version_diff"],
                )
            )

        return StaleArtifactsListResponse(
            items=items,
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list stale artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list stale artifacts: {str(e)}",
        )


# =============================================================================
# Cache Management Endpoints
# =============================================================================


@router.get(
    "/search",
    response_model=SearchResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Search cached artifacts",
    description=(
        "Search artifacts by name with pagination and sorting. "
        "Supports relevance scoring (exact > prefix > contains)."
    ),
)
async def search_cache(
    cache_manager: CacheManagerDep,
    query: str = Query(
        ...,
        min_length=1,
        description="Search query string",
        examples=["docker"],
    ),
    project_id: Optional[str] = Query(
        None,
        description="Filter by project ID",
        examples=["proj-1"],
    ),
    artifact_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by artifact type",
        examples=["skill"],
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of items to skip",
        examples=[0],
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum items to return",
        examples=[50],
    ),
    sort_by: str = Query(
        "relevance",
        description="Sort order (relevance, name, type, updated)",
        examples=["relevance"],
    ),
) -> SearchResultsResponse:
    """Search cached artifacts.

    Args:
        cache_manager: CacheManager dependency
        query: Search query string
        project_id: Optional project ID filter
        artifact_type: Optional artifact type filter
        skip: Number of items to skip
        limit: Maximum items to return
        sort_by: Sort order

    Returns:
        Paginated search results with relevance scores

    Raises:
        HTTPException: On search failure
    """
    try:
        # Validate sort_by parameter
        valid_sorts = ["relevance", "name", "type", "updated"]
        if sort_by not in valid_sorts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by value. Must be one of: {', '.join(valid_sorts)}",
            )

        # Perform search
        artifacts, total = cache_manager.search_artifacts(
            query=query,
            project_id=project_id,
            artifact_type=artifact_type,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
        )

        # Calculate scores and get project names
        items = []
        for artifact in artifacts:
            # Get project name
            project = cache_manager.get_project(artifact.project_id)
            project_name = project.name if project else "Unknown"

            # Calculate relevance score (same logic as repository)
            name_lower = artifact.name.lower()
            query_lower = query.lower()
            if name_lower == query_lower:
                score = 100.0  # Exact match
            elif name_lower.startswith(query_lower):
                score = 80.0  # Prefix match
            else:
                score = 60.0  # Contains match

            items.append(
                SearchResult(
                    id=artifact.id,
                    name=artifact.name,
                    type=artifact.type,
                    project_id=artifact.project_id,
                    project_name=project_name,
                    score=score,
                )
            )

        return SearchResultsResponse(
            items=items,
            total=total,
            query=query,
            skip=skip,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


# =============================================================================
# Cache Management Endpoints
# =============================================================================


@router.post(
    "/invalidate",
    response_model=CacheInvalidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Invalidate cache",
    description=(
        "Mark cache as stale to force refresh on next access. "
        "Can invalidate entire cache or specific project."
    ),
)
async def invalidate_cache(
    request: CacheInvalidateRequest,
    cache_manager: CacheManagerDep,
) -> CacheInvalidateResponse:
    """Invalidate cache.

    Args:
        request: Invalidation request parameters
        cache_manager: CacheManager dependency

    Returns:
        Invalidation result

    Raises:
        HTTPException: On invalidation failure or if project not found
    """
    try:
        # Check if project exists (if specific project invalidation)
        if request.project_id:
            project = cache_manager.get_project(request.project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{request.project_id}' not found",
                )

        # Invalidate cache
        count = cache_manager.invalidate_cache(project_id=request.project_id)

        message = (
            f"Invalidated {count} project(s) successfully"
            if request.project_id
            else f"Invalidated entire cache ({count} projects)"
        )

        logger.info(
            f"Cache invalidated (project_id={request.project_id}, count={count})"
        )

        return CacheInvalidateResponse(
            success=True,
            invalidated_count=count,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}",
        )


# =============================================================================
# Marketplace Cache Endpoints
# =============================================================================


@router.get(
    "/marketplace",
    response_model=MarketplaceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get cached marketplace entries",
    description=(
        "Get list of cached marketplace artifact entries with optional filtering "
        "by artifact type. Returns cached data with 24-hour TTL."
    ),
)
async def get_marketplace_cache(
    cache_manager: CacheManagerDep,
    entry_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by artifact type",
        examples=["skill"],
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Number of items to skip",
        examples=[0],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum items to return",
        examples=[100],
    ),
) -> MarketplaceListResponse:
    """Get cached marketplace entries.

    Args:
        cache_manager: CacheManager dependency
        entry_type: Optional artifact type filter
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        Paginated list of marketplace entries

    Raises:
        HTTPException: On retrieval failure
    """
    try:
        # Get marketplace entries
        all_entries = cache_manager.get_marketplace_entries(entry_type=entry_type)

        total = len(all_entries)

        # Apply pagination
        paginated_entries = all_entries[skip : skip + limit]

        # Convert to response schema
        items = []
        for entry in paginated_entries:
            # Parse data JSON if present
            data_dict = None
            if entry.data:
                try:
                    import json

                    data_dict = json.loads(entry.data)
                except Exception as e:
                    logger.warning(f"Failed to parse entry data: {e}")

            items.append(
                MarketplaceEntryResponse(
                    id=entry.id,
                    name=entry.name,
                    type=entry.type,
                    url=entry.url,
                    description=entry.description,
                    cached_at=entry.cached_at,
                    data=data_dict,
                )
            )

        return MarketplaceListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Failed to get marketplace cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get marketplace cache: {str(e)}",
        )
