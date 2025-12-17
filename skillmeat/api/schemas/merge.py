"""Merge operation API schemas for request and response models.

Provides schemas for version merge operations including safety analysis,
previews, execution, and conflict resolution.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .version import ConflictMetadataResponse


class MergeAnalyzeRequest(BaseModel):
    """Request schema for analyzing merge safety.

    Performs safety analysis without executing the merge to identify
    potential conflicts and auto-mergeable files.
    """

    base_snapshot_id: str = Field(
        description="Snapshot ID of base/ancestor version",
        examples=["snap_20241215_120000"],
    )
    local_collection: str = Field(
        description="Name of the local collection",
        examples=["default"],
    )
    remote_snapshot_id: str = Field(
        description="Snapshot ID of remote version to merge",
        examples=["snap_20241216_150000"],
    )
    remote_collection: Optional[str] = Field(
        default=None,
        description="Name of remote collection (defaults to local_collection)",
        examples=["upstream"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "base_snapshot_id": "snap_20241215_120000",
                "local_collection": "default",
                "remote_snapshot_id": "snap_20241216_150000",
            }
        }


class MergeSafetyResponse(BaseModel):
    """Response schema for merge safety analysis.

    Provides detailed information about merge safety including conflicts
    and warnings.
    """

    can_auto_merge: bool = Field(
        description="Whether merge can be performed automatically",
        examples=[True],
    )
    auto_mergeable_count: int = Field(
        description="Number of files that can auto-merge",
        examples=[5],
    )
    conflict_count: int = Field(
        description="Number of files with conflicts",
        examples=[2],
    )
    conflicts: List[ConflictMetadataResponse] = Field(
        description="List of conflict metadata for files requiring resolution",
        default_factory=list,
    )
    warnings: List[str] = Field(
        description="List of warning messages about the merge",
        default_factory=list,
        examples=[["Binary file conflict detected: image.png"]],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "can_auto_merge": False,
                "auto_mergeable_count": 5,
                "conflict_count": 2,
                "conflicts": [
                    {
                        "file_path": "SKILL.md",
                        "conflict_type": "both_modified",
                        "auto_mergeable": False,
                        "is_binary": False,
                    }
                ],
                "warnings": ["Binary file conflict detected: image.png"],
            }
        }


class MergePreviewRequest(BaseModel):
    """Request schema for previewing merge changes.

    Shows what files will be added, removed, or changed by the merge
    without executing it.
    """

    base_snapshot_id: str = Field(
        description="Snapshot ID of base/ancestor version",
        examples=["snap_20241215_120000"],
    )
    local_collection: str = Field(
        description="Name of the local collection",
        examples=["default"],
    )
    remote_snapshot_id: str = Field(
        description="Snapshot ID of remote version to merge",
        examples=["snap_20241216_150000"],
    )
    remote_collection: Optional[str] = Field(
        default=None,
        description="Name of remote collection (defaults to local_collection)",
        examples=["upstream"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "base_snapshot_id": "snap_20241215_120000",
                "local_collection": "default",
                "remote_snapshot_id": "snap_20241216_150000",
            }
        }


class MergePreviewResponse(BaseModel):
    """Response schema for merge preview.

    Provides a preview of merge changes without executing the merge.
    """

    files_added: List[str] = Field(
        description="List of file paths added in remote",
        default_factory=list,
        examples=[["new_feature.py"]],
    )
    files_removed: List[str] = Field(
        description="List of file paths removed in remote",
        default_factory=list,
        examples=[["deprecated.py"]],
    )
    files_changed: List[str] = Field(
        description="List of file paths that differ between versions",
        default_factory=list,
        examples=[["SKILL.md", "main.py"]],
    )
    potential_conflicts: List[ConflictMetadataResponse] = Field(
        description="List of conflict metadata for potential conflicts",
        default_factory=list,
    )
    can_auto_merge: bool = Field(
        description="Whether merge can be performed automatically",
        examples=[True],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "files_added": ["new_feature.py"],
                "files_removed": ["deprecated.py"],
                "files_changed": ["SKILL.md", "main.py"],
                "potential_conflicts": [],
                "can_auto_merge": True,
            }
        }


class MergeExecuteRequest(BaseModel):
    """Request schema for executing a merge.

    Performs the actual merge operation with automatic snapshot creation
    for safety.
    """

    base_snapshot_id: str = Field(
        description="Snapshot ID of base/ancestor version",
        examples=["snap_20241215_120000"],
    )
    local_collection: str = Field(
        description="Name of the local collection",
        examples=["default"],
    )
    remote_snapshot_id: str = Field(
        description="Snapshot ID of remote version to merge",
        examples=["snap_20241216_150000"],
    )
    remote_collection: Optional[str] = Field(
        default=None,
        description="Name of remote collection (defaults to local_collection)",
        examples=["upstream"],
    )
    auto_snapshot: bool = Field(
        default=True,
        description="Whether to automatically create a safety snapshot before merge",
        examples=[True],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "base_snapshot_id": "snap_20241215_120000",
                "local_collection": "default",
                "remote_snapshot_id": "snap_20241216_150000",
                "auto_snapshot": True,
            }
        }


class MergeExecuteResponse(BaseModel):
    """Response schema for merge execution.

    Provides result of merge operation including files merged and any
    unresolved conflicts.
    """

    success: bool = Field(
        description="True if merge completed successfully",
        examples=[True],
    )
    files_merged: List[str] = Field(
        description="List of file paths that were merged",
        default_factory=list,
        examples=[["SKILL.md", "main.py"]],
    )
    conflicts: List[ConflictMetadataResponse] = Field(
        description="List of conflict metadata for unresolved conflicts",
        default_factory=list,
    )
    pre_merge_snapshot_id: Optional[str] = Field(
        default=None,
        description="ID of safety snapshot created before merge",
        examples=["snap_20241216_150000_premerge"],
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if merge failed",
        examples=["Merge failed: base snapshot not found"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "files_merged": ["SKILL.md", "main.py"],
                "conflicts": [],
                "pre_merge_snapshot_id": "snap_20241216_150000_premerge",
                "error": None,
            }
        }


class ConflictResolveRequest(BaseModel):
    """Request schema for resolving a single conflict.

    Allows manual resolution of merge conflicts by specifying which
    version to use or providing custom content.
    """

    file_path: str = Field(
        description="Relative path to the conflicting file",
        examples=["SKILL.md"],
    )
    resolution: Literal["use_local", "use_remote", "use_base", "custom"] = Field(
        description="Resolution strategy to apply",
        examples=["use_local"],
    )
    custom_content: Optional[str] = Field(
        default=None,
        description="Custom content to use (required if resolution='custom')",
        examples=["# Manually merged content"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "file_path": "SKILL.md",
                "resolution": "use_local",
            }
        }


class ConflictResolveResponse(BaseModel):
    """Response schema for conflict resolution.

    Indicates whether the conflict was successfully resolved.
    """

    success: bool = Field(
        description="True if conflict was resolved successfully",
        examples=[True],
    )
    file_path: str = Field(
        description="Path to the file that was resolved",
        examples=["SKILL.md"],
    )
    resolution_applied: str = Field(
        description="Resolution strategy that was applied",
        examples=["use_local"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "file_path": "SKILL.md",
                "resolution_applied": "use_local",
            }
        }
