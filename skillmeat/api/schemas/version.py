"""Pydantic schemas for version management API endpoints.

Defines request and response models for snapshot and rollback operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .common import PageInfo, PaginatedResponse


# ====================
# Response Schemas
# ====================


class SnapshotResponse(BaseModel):
    """Single snapshot representation.

    Provides metadata about a collection snapshot including artifact count
    and timestamp information.
    """

    id: str = Field(
        description="Snapshot unique identifier (SHA-256 hash)",
        examples=["abc123def456789..."],
    )
    timestamp: datetime = Field(
        description="Snapshot creation timestamp",
        examples=["2025-12-17T12:00:00Z"],
    )
    message: str = Field(
        description="Snapshot description or commit message",
        examples=["Manual snapshot before upgrade"],
    )
    collection_name: str = Field(
        description="Name of the collection this snapshot belongs to",
        examples=["default"],
    )
    artifact_count: int = Field(
        description="Number of artifacts captured in this snapshot",
        examples=[15],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "abc123def456789...",
                "timestamp": "2025-12-17T12:00:00Z",
                "message": "Manual snapshot before upgrade",
                "collection_name": "default",
                "artifact_count": 15,
            }
        }


class SnapshotListResponse(PaginatedResponse[SnapshotResponse]):
    """Paginated response for snapshot listings.

    Returns list of snapshots with pagination metadata following
    cursor-based pagination pattern.
    """

    pass


class ConflictMetadataResponse(BaseModel):
    """Conflict information for a single file.

    Describes the type and nature of a merge conflict detected
    during rollback analysis.
    """

    file_path: str = Field(
        description="Relative path to the conflicting file",
        examples=[".claude/skills/pdf/SKILL.md"],
    )
    conflict_type: str = Field(
        description="Type of conflict: content, deletion, add_add, both_modified",
        examples=["content"],
    )
    auto_mergeable: bool = Field(
        description="Whether the conflict can be automatically merged",
        examples=[True],
    )
    is_binary: bool = Field(
        description="Whether the file is binary (cannot be text-merged)",
        examples=[False],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "file_path": ".claude/skills/pdf/SKILL.md",
                "conflict_type": "content",
                "auto_mergeable": True,
                "is_binary": False,
            }
        }


class RollbackSafetyAnalysisResponse(BaseModel):
    """Pre-flight rollback safety analysis.

    Provides analysis of potential conflicts and safety information
    before executing a rollback operation.
    """

    is_safe: bool = Field(
        description="Whether rollback can proceed without data loss",
        examples=[True],
    )
    files_with_conflicts: List[str] = Field(
        default_factory=list,
        description="Files that have conflicts requiring manual resolution",
        examples=[[".claude/skills/pdf/SKILL.md"]],
    )
    files_safe_to_restore: List[str] = Field(
        default_factory=list,
        description="Files that can be safely restored without conflicts",
        examples=[[".claude/skills/canvas/SKILL.md"]],
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warning messages about potential issues",
        examples=[["2 files have been modified since snapshot"]],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "is_safe": True,
                "files_with_conflicts": [".claude/skills/pdf/SKILL.md"],
                "files_safe_to_restore": [".claude/skills/canvas/SKILL.md"],
                "warnings": ["2 files have been modified since snapshot"],
            }
        }


class RollbackResponse(BaseModel):
    """Rollback operation result.

    Contains detailed information about files restored, merged, and
    any conflicts encountered during rollback.
    """

    success: bool = Field(
        description="Whether rollback operation completed successfully",
        examples=[True],
    )
    files_merged: List[str] = Field(
        default_factory=list,
        description="Files that were successfully merged",
        examples=[[".claude/skills/pdf/SKILL.md"]],
    )
    files_restored: List[str] = Field(
        default_factory=list,
        description="Files that were restored from snapshot",
        examples=[[".claude/skills/canvas/SKILL.md"]],
    )
    conflicts: List[ConflictMetadataResponse] = Field(
        default_factory=list,
        description="Conflicts that require manual resolution",
    )
    safety_snapshot_id: Optional[str] = Field(
        default=None,
        description="ID of safety snapshot created before rollback",
        examples=["def789abc123..."],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "files_merged": [".claude/skills/pdf/SKILL.md"],
                "files_restored": [".claude/skills/canvas/SKILL.md"],
                "conflicts": [],
                "safety_snapshot_id": "def789abc123...",
            }
        }


class VersionDiffResponse(BaseModel):
    """Diff result between two snapshots.

    Provides statistical comparison of changes between two
    collection snapshots.
    """

    files_added: List[str] = Field(
        default_factory=list,
        description="Files added between snapshots",
        examples=[[".claude/skills/new-skill/SKILL.md"]],
    )
    files_removed: List[str] = Field(
        default_factory=list,
        description="Files removed between snapshots",
        examples=[[".claude/skills/old-skill/SKILL.md"]],
    )
    files_modified: List[str] = Field(
        default_factory=list,
        description="Files modified between snapshots",
        examples=[[".claude/skills/pdf/SKILL.md"]],
    )
    total_lines_added: int = Field(
        description="Total number of lines added across all files",
        examples=[150],
    )
    total_lines_removed: int = Field(
        description="Total number of lines removed across all files",
        examples=[75],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "files_added": [".claude/skills/new-skill/SKILL.md"],
                "files_removed": [".claude/skills/old-skill/SKILL.md"],
                "files_modified": [".claude/skills/pdf/SKILL.md"],
                "total_lines_added": 150,
                "total_lines_removed": 75,
            }
        }


# ====================
# Request Schemas
# ====================


class SnapshotCreateRequest(BaseModel):
    """Request to create a new snapshot.

    Creates a point-in-time snapshot of a collection for later rollback.
    """

    collection_name: Optional[str] = Field(
        default=None,
        description="Collection name (uses active collection if not specified)",
        examples=["default"],
    )
    message: str = Field(
        default="Manual snapshot",
        description="Snapshot description or commit message",
        max_length=500,
        examples=["Manual snapshot before major upgrade"],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "collection_name": "default",
                "message": "Manual snapshot before major upgrade",
            }
        }


class SnapshotCreateResponse(BaseModel):
    """Response after creating a snapshot.

    Returns the newly created snapshot with confirmation flag.
    """

    snapshot: SnapshotResponse = Field(
        description="Newly created snapshot metadata",
    )
    created: bool = Field(
        default=True,
        description="Confirmation that snapshot was created",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "snapshot": {
                    "id": "abc123def456789...",
                    "timestamp": "2025-12-17T12:00:00Z",
                    "message": "Manual snapshot before major upgrade",
                    "collection_name": "default",
                    "artifact_count": 15,
                },
                "created": True,
            }
        }


class RollbackRequest(BaseModel):
    """Request to rollback to a previous snapshot.

    Supports both simple rollback and intelligent merge-based rollback
    with selective path restoration.
    """

    snapshot_id: str = Field(
        description="ID of snapshot to rollback to",
        examples=["abc123def456789..."],
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Collection name (uses active collection if not specified)",
        examples=["default"],
    )
    preserve_changes: bool = Field(
        default=True,
        description="Use intelligent merge to preserve local changes (recommended)",
        examples=[True],
    )
    selective_paths: Optional[List[str]] = Field(
        default=None,
        description="Only rollback these specific paths (optional)",
        examples=[[".claude/skills/pdf/"]],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "snapshot_id": "abc123def456789...",
                "collection_name": "default",
                "preserve_changes": True,
                "selective_paths": None,
            }
        }


class VersionDiffRequest(BaseModel):
    """Request to compare two snapshots.

    Generates a diff showing changes between two collection snapshots.
    """

    snapshot_id_1: str = Field(
        description="First snapshot ID (older)",
        examples=["abc123def456789..."],
    )
    snapshot_id_2: str = Field(
        description="Second snapshot ID (newer)",
        examples=["def789abc123..."],
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Collection name (uses active collection if not specified)",
        examples=["default"],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "snapshot_id_1": "abc123def456789...",
                "snapshot_id_2": "def789abc123...",
                "collection_name": "default",
            }
        }
