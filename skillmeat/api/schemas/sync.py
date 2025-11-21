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


class ResolveRequest(BaseModel):
    """Request to resolve conflicts for an artifact."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    resolution: str = Field(
        description="Resolution strategy (ours|theirs|manual)",
        examples=["ours"],
    )
    project_path: Optional[str] = Field(
        default=None, description="Project path if resolving a project artifact"
    )
    collection: Optional[str] = Field(
        default=None, description="Collection name (defaults to active)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "resolution": "ours",
                "project_path": "/path/to/project",
                "collection": "default",
            }
        }


class ResolveResponse(BaseModel):
    """Response for conflict resolution."""

    status: str = Field(description="Resolution status")
    message: Optional[str] = Field(default=None, description="Human-readable message")
    job_id: Optional[str] = Field(default=None, description="Async job id when queued")
    unresolved_files: List[str] = Field(
        default_factory=list, description="Files still containing conflict markers"
    )


class PatchRequest(BaseModel):
    """Request to generate patch bundle from project to upstream/collection."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    project_path: str = Field(description="Project path containing deployment")
    collection: Optional[str] = Field(default=None, description="Collection name (defaults to active)")

    class Config:
        json_schema_extra = {
            "example": {
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "project_path": "/path/to/project",
                "collection": "default",
            }
        }


class PatchResponse(BaseModel):
    """Response for patch bundle generation."""

    status: str = Field(description="Result status (success|error)")
    download_path: Optional[str] = Field(default=None, description="Path to generated patch bundle")
    sha256: Optional[str] = Field(default=None, description="SHA256 of bundle")
    size_bytes: Optional[int] = Field(default=None, description="Size of bundle in bytes")
    message: Optional[str] = Field(default=None, description="Additional info or errors")
