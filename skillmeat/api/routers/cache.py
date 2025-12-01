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
    RefreshJobStatus,
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
    description="Get list of artifacts that have newer upstream versions available.",
)
async def list_stale_artifacts(
    cache_manager: CacheManagerDep,
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
        100,
        ge=1,
        le=500,
        description="Maximum items to return",
        examples=[100],
    ),
) -> StaleArtifactsListResponse:
    """List outdated artifacts.

    Args:
        cache_manager: CacheManager dependency
        artifact_type: Optional artifact type filter
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        List of outdated artifacts

    Raises:
        HTTPException: On retrieval failure
    """
    try:
        # Get outdated artifacts
        outdated_artifacts = cache_manager.get_outdated_artifacts()

        # Apply type filter if specified
        if artifact_type:
            outdated_artifacts = [
                a for a in outdated_artifacts if a.type == artifact_type
            ]

        total = len(outdated_artifacts)

        # Apply pagination
        paginated_artifacts = outdated_artifacts[skip : skip + limit]

        # Get project names for each artifact
        items = []
        for artifact in paginated_artifacts:
            project = cache_manager.get_project(artifact.project_id)
            project_name = project.name if project else "Unknown"

            items.append(
                StaleArtifactResponse(
                    id=artifact.id,
                    name=artifact.name,
                    type=artifact.type,
                    project_name=project_name,
                    deployed_version=artifact.deployed_version,
                    upstream_version=artifact.upstream_version,
                )
            )

        return StaleArtifactsListResponse(
            items=items,
            total=total,
        )

    except Exception as e:
        logger.error(f"Failed to list stale artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list stale artifacts: {str(e)}",
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
