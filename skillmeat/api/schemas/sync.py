"""Pydantic schemas for sync API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    """Request for sync operations."""

    project_path: Optional[str] = Field(
        default=None, description="Project path (required for push/pull)"
    )
    collection: Optional[str] = Field(
        default=None, description="Collection name override"
    )
    artifacts: Optional[List[str]] = Field(
        default=None, description="Artifacts to sync; syncs all if omitted"
    )
    dry_run: bool = Field(default=False, description="Preview without applying changes")
    strategy: Optional[str] = Field(
        default=None,
        description="Strategy for project->collection pulls (overwrite|merge|fork|prompt)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_path": "/path/to/project",
                "collection": "default",
                "artifacts": ["pdf", "canvas"],
                "dry_run": True,
                "strategy": "overwrite",
            }
        }


class ConflictEntry(BaseModel):
    """Conflict or error entry from sync operations."""

    artifact_name: str = Field(description="Artifact name")
    error: Optional[str] = Field(
        default=None, description="Error message, if any"
    )
    conflict_files: List[str] = Field(
        default_factory=list, description="Files with conflicts (if applicable)"
    )


class SyncResponse(BaseModel):
    """Response for sync operations."""

    status: str = Field(description="Result status (success|partial|no_changes|dry_run)")
    message: Optional[str] = Field(default=None, description="Human-readable summary")
    artifacts_synced: List[str] = Field(
        default_factory=list, description="Artifacts successfully synced"
    )
    conflicts: List[ConflictEntry] = Field(
        default_factory=list, description="Conflicts or failed artifacts"
    )

