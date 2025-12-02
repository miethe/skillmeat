"""Cache management API schemas.

Provides Pydantic models for cache-related API requests and responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CacheRefreshRequest(BaseModel):
    """Request to trigger cache refresh.

    Attributes:
        project_id: If provided, only refresh this project. If None, refresh all.
        force: If True, refresh even if cache is not stale.
    """

    project_id: Optional[str] = Field(
        default=None,
        description="Project ID to refresh (if None, refresh all projects)",
        examples=["proj-abc123"],
    )
    force: bool = Field(
        default=False,
        description="Force refresh even if not stale",
        examples=[False],
    )


class CacheRefreshResponse(BaseModel):
    """Response from cache refresh operation.

    Attributes:
        success: Whether the refresh completed successfully
        projects_refreshed: Number of projects refreshed
        changes_detected: Whether any changes were detected
        errors: List of error messages (if any)
        duration_seconds: Time taken for refresh operation
        message: Human-readable status message
    """

    success: bool = Field(
        description="Overall success status",
        examples=[True],
    )
    projects_refreshed: int = Field(
        description="Number of projects successfully refreshed",
        examples=[5],
    )
    changes_detected: bool = Field(
        description="Whether any changes were detected during refresh",
        examples=[True],
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages encountered",
        examples=[[]],
    )
    duration_seconds: float = Field(
        description="Total operation duration in seconds",
        examples=[1.23],
    )
    message: str = Field(
        description="Human-readable status message",
        examples=["Refresh completed successfully"],
    )


class RefreshJobStatus(BaseModel):
    """Status of the background refresh job.

    Attributes:
        is_running: Whether scheduler is currently running
        next_run_time: When next refresh will run (if scheduled)
        last_run_time: When last refresh completed
    """

    is_running: bool = Field(
        description="Whether refresh scheduler is running",
        examples=[True],
    )
    next_run_time: Optional[datetime] = Field(
        default=None,
        description="Next scheduled refresh time",
        examples=["2024-01-15T18:00:00Z"],
    )
    last_run_time: Optional[datetime] = Field(
        default=None,
        description="Last refresh completion time",
        examples=["2024-01-15T12:00:00Z"],
    )


class CacheStatusResponse(BaseModel):
    """Cache statistics and status information.

    Attributes:
        total_projects: Total number of cached projects
        total_artifacts: Total number of cached artifacts
        stale_projects: Number of projects past TTL
        outdated_artifacts: Number of artifacts with updates available
        cache_size_bytes: Database file size in bytes
        oldest_entry: Datetime of oldest cached entry
        newest_entry: Datetime of newest cached entry
        last_refresh: When cache was last refreshed
        refresh_job_status: Status of background refresh job
    """

    total_projects: int = Field(
        description="Total number of cached projects",
        examples=[10],
    )
    total_artifacts: int = Field(
        description="Total number of cached artifacts",
        examples=[45],
    )
    stale_projects: int = Field(
        description="Number of stale projects (past TTL)",
        examples=[2],
    )
    outdated_artifacts: int = Field(
        description="Number of artifacts with updates available",
        examples=[3],
    )
    cache_size_bytes: int = Field(
        description="Cache database size in bytes",
        examples=[1048576],
    )
    oldest_entry: Optional[datetime] = Field(
        default=None,
        description="Datetime of oldest cached entry",
        examples=["2024-01-01T00:00:00Z"],
    )
    newest_entry: Optional[datetime] = Field(
        default=None,
        description="Datetime of newest cached entry",
        examples=["2024-01-15T12:00:00Z"],
    )
    last_refresh: Optional[datetime] = Field(
        default=None,
        description="When cache was last refreshed",
        examples=["2024-01-15T12:00:00Z"],
    )
    refresh_job_status: RefreshJobStatus = Field(
        description="Background refresh job status",
    )


class CachedProjectResponse(BaseModel):
    """Cached project information.

    Attributes:
        id: Project ID
        name: Project name
        path: Filesystem path to project
        status: Project status (active, stale, error)
        last_fetched: When project was last fetched
        artifact_count: Number of artifacts in project
    """

    id: str = Field(
        description="Project ID",
        examples=["proj-1"],
    )
    name: str = Field(
        description="Project name",
        examples=["My Project"],
    )
    path: str = Field(
        description="Filesystem path to project",
        examples=["/path/to/project"],
    )
    status: str = Field(
        description="Project status",
        examples=["active"],
    )
    last_fetched: Optional[datetime] = Field(
        default=None,
        description="When project was last fetched",
        examples=["2024-01-15T12:00:00Z"],
    )
    artifact_count: int = Field(
        description="Number of artifacts in project",
        examples=[5],
    )


class CachedProjectsListResponse(BaseModel):
    """Paginated list of cached projects.

    Attributes:
        items: List of cached projects
        total: Total number of projects (before pagination)
        skip: Number of items skipped
        limit: Maximum items per page
    """

    items: List[CachedProjectResponse] = Field(
        description="List of cached projects",
    )
    total: int = Field(
        description="Total number of projects",
        examples=[10],
    )
    skip: int = Field(
        description="Number of items skipped",
        examples=[0],
    )
    limit: int = Field(
        description="Maximum items per page",
        examples=[100],
    )


class CachedArtifactResponse(BaseModel):
    """Cached artifact information.

    Attributes:
        id: Artifact ID
        name: Artifact name
        type: Artifact type (skill, command, etc.)
        project_id: Project ID this artifact belongs to
        deployed_version: Version deployed to project
        upstream_version: Latest available version
        is_outdated: Whether deployed version is behind upstream
    """

    id: str = Field(
        description="Artifact ID",
        examples=["art-1"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["my-skill"],
    )
    type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    project_id: str = Field(
        description="Project ID",
        examples=["proj-1"],
    )
    deployed_version: Optional[str] = Field(
        default=None,
        description="Version deployed to project",
        examples=["1.0.0"],
    )
    upstream_version: Optional[str] = Field(
        default=None,
        description="Latest available version",
        examples=["1.1.0"],
    )
    is_outdated: bool = Field(
        description="Whether artifact is outdated",
        examples=[True],
    )


class CachedArtifactsListResponse(BaseModel):
    """Paginated list of cached artifacts.

    Attributes:
        items: List of cached artifacts
        total: Total number of artifacts (before pagination/filtering)
        skip: Number of items skipped
        limit: Maximum items per page
    """

    items: List[CachedArtifactResponse] = Field(
        description="List of cached artifacts",
    )
    total: int = Field(
        description="Total number of artifacts",
        examples=[45],
    )
    skip: int = Field(
        description="Number of items skipped",
        examples=[0],
    )
    limit: int = Field(
        description="Maximum items per page",
        examples=[100],
    )


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate cache.

    Attributes:
        project_id: If provided, only invalidate this project. If None, invalidate all.
    """

    project_id: Optional[str] = Field(
        default=None,
        description="Project ID to invalidate (if None, invalidate all)",
        examples=["proj-abc123"],
    )


class CacheInvalidateResponse(BaseModel):
    """Response from cache invalidation.

    Attributes:
        success: Whether invalidation succeeded
        invalidated_count: Number of projects invalidated
        message: Human-readable status message
    """

    success: bool = Field(
        description="Whether invalidation succeeded",
        examples=[True],
    )
    invalidated_count: int = Field(
        description="Number of projects invalidated",
        examples=[5],
    )
    message: str = Field(
        description="Human-readable status message",
        examples=["Cache invalidated successfully"],
    )


class StaleArtifactResponse(BaseModel):
    """Information about a stale artifact.

    Attributes:
        id: Artifact ID
        name: Artifact name
        type: Artifact type
        project_name: Name of project this artifact belongs to
        project_id: Project ID this artifact belongs to
        deployed_version: Currently deployed version
        upstream_version: Available upstream version
        version_difference: Human-readable description of version difference
    """

    id: str = Field(
        description="Artifact ID",
        examples=["art-1"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["my-skill"],
    )
    type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    project_name: str = Field(
        description="Project name",
        examples=["My Project"],
    )
    project_id: str = Field(
        description="Project ID",
        examples=["proj-1"],
    )
    deployed_version: Optional[str] = Field(
        default=None,
        description="Currently deployed version",
        examples=["1.0.0"],
    )
    upstream_version: Optional[str] = Field(
        default=None,
        description="Available upstream version",
        examples=["1.1.0"],
    )
    version_difference: Optional[str] = Field(
        default=None,
        description="Human-readable description of version difference",
        examples=["minor version upgrade (0 -> 1)"],
    )


class StaleArtifactsListResponse(BaseModel):
    """List of stale artifacts.

    Attributes:
        items: List of stale artifacts
        total: Total number of stale artifacts
    """

    items: List[StaleArtifactResponse] = Field(
        description="List of stale artifacts",
    )
    total: int = Field(
        description="Total number of stale artifacts",
        examples=[3],
    )


class SearchResult(BaseModel):
    """Search result for a single artifact.

    Attributes:
        id: Artifact ID
        name: Artifact name
        type: Artifact type
        project_id: Project ID
        project_name: Project name
        score: Relevance score (100=exact, 80=prefix, 60=contains)
    """

    id: str = Field(
        description="Artifact ID",
        examples=["art-1"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["my-skill"],
    )
    type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    project_id: str = Field(
        description="Project ID",
        examples=["proj-1"],
    )
    project_name: str = Field(
        description="Project name",
        examples=["My Project"],
    )
    score: float = Field(
        description="Relevance score (100=exact match, 80=prefix, 60=contains)",
        examples=[80.0],
    )


class SearchResultsResponse(BaseModel):
    """Paginated search results.

    Attributes:
        items: List of search results
        total: Total number of matches (before pagination)
        query: Original search query
        skip: Number of items skipped
        limit: Maximum items per page
    """

    items: List[SearchResult] = Field(
        description="List of search results",
    )
    total: int = Field(
        description="Total number of matches",
        examples=[25],
    )
    query: str = Field(
        description="Search query",
        examples=["docker"],
    )
    skip: int = Field(
        description="Number of items skipped",
        examples=[0],
    )
    limit: int = Field(
        description="Maximum items per page",
        examples=[50],
    )


class MarketplaceEntryResponse(BaseModel):
    """Marketplace entry information.

    Attributes:
        id: Entry ID
        name: Artifact name
        type: Artifact type
        url: URL to artifact
        description: Entry description
        cached_at: When entry was cached
        data: Additional marketplace data (publisher, license, tags, etc.)
    """

    id: str = Field(
        description="Marketplace entry ID",
        examples=["mkt-1"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["awesome-skill"],
    )
    type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    url: str = Field(
        description="URL to artifact",
        examples=["https://github.com/user/skill"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Entry description",
        examples=["An awesome skill"],
    )
    cached_at: datetime = Field(
        description="When entry was cached",
        examples=["2024-01-15T12:00:00Z"],
    )
    data: Optional[dict] = Field(
        default=None,
        description="Additional marketplace data",
        examples=[
            {
                "publisher": "user",
                "license": "MIT",
                "tags": ["automation", "testing"],
                "version": "1.0.0",
            }
        ],
    )


class MarketplaceListResponse(BaseModel):
    """Paginated list of marketplace entries.

    Attributes:
        items: List of marketplace entries
        total: Total number of entries
        skip: Number of items skipped
        limit: Maximum items per page
    """

    items: List[MarketplaceEntryResponse] = Field(
        description="List of marketplace entries",
    )
    total: int = Field(
        description="Total number of marketplace entries",
        examples=[50],
    )
    skip: int = Field(
        description="Number of items skipped",
        examples=[0],
    )
    limit: int = Field(
        description="Maximum items per page",
        examples=[100],
    )
