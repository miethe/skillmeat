"""Pydantic schemas for artifact diff responses."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ArtifactFileDiff(BaseModel):
    """Diff info for a single file."""

    path: str = Field(description="Relative path")
    status: str = Field(description="added|removed|modified|unchanged|binary")
    lines_added: int = Field(default=0, description="Added lines")
    lines_removed: int = Field(default=0, description="Removed lines")
    unified_diff: Optional[str] = Field(default=None, description="Unified diff text when available")


class ArtifactDiffResponse(BaseModel):
    """Aggregate diff response."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    lhs: str = Field(description="Left tier")
    rhs: str = Field(description="Right tier")
    files_added: int = Field(default=0, description="Count of added files")
    files_removed: int = Field(default=0, description="Count of removed files")
    files_modified: int = Field(default=0, description="Count of modified files")
    total_lines_added: int = Field(default=0, description="Total added lines")
    total_lines_removed: int = Field(default=0, description="Total removed lines")
    truncated: bool = Field(default=False, description="True if diff payload truncated or too large")
    download_path: Optional[str] = Field(
        default=None, description="Path to full diff bundle when truncated/large"
    )
    files: List[ArtifactFileDiff] = Field(default_factory=list, description="File-level diffs")
