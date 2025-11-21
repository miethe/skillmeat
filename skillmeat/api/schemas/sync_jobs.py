"""Pydantic schemas for async sync jobs."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SyncJobCreateRequest(BaseModel):
    """Create a new sync job."""

    direction: str = Field(
        description="Direction of sync: upstream_to_collection|collection_to_project|project_to_collection"
    )
    artifacts: Optional[List[str]] = Field(
        default=None, description="Artifacts to sync; syncs all if omitted"
    )
    project_path: Optional[str] = Field(
        default=None, description="Project path (required for project directions)"
    )
    collection: Optional[str] = Field(
        default=None, description="Collection name override"
    )
    strategy: Optional[str] = Field(
        default=None,
        description="Strategy for project->collection pulls (overwrite|merge|fork|prompt|ours|theirs)",
    )
    dry_run: bool = Field(default=False, description="Preview without applying changes")


class SyncJobStatusResponse(BaseModel):
    """Status payload for a sync job."""

    job_id: str = Field(description="Job identifier")
    direction: str = Field(description="Sync direction")
    state: str = Field(description="Job state: queued|running|success|conflict|error|canceled")
    pct_complete: float = Field(description="Progress (0-1.0)")
    duration_ms: Optional[int] = Field(default=None, description="Duration in ms if available")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    ended_at: Optional[datetime] = Field(default=None, description="End timestamp")
    trace_id: Optional[str] = Field(default=None, description="Trace identifier")
    log_excerpt: Optional[str] = Field(default=None, description="Short log/summary")
    conflicts: List[dict] = Field(
        default_factory=list, description="Conflicts encountered (if any)"
    )
    artifacts: List[str] = Field(default_factory=list, description="Artifacts requested")
    project_path: Optional[str] = Field(default=None, description="Project path")
    collection: Optional[str] = Field(default=None, description="Collection name")
    strategy: Optional[str] = Field(default=None, description="Strategy used")
