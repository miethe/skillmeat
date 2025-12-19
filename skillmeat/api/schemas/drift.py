"""Pydantic schemas for drift detection API endpoints.

Defines request and response models for detecting and reporting drift
between collection artifacts and deployed project artifacts.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ====================
# Response Schemas
# ====================


class DriftDetectionResponse(BaseModel):
    """Response from drift detection for a single artifact.

    Represents the drift status between a collection artifact and its
    deployment in a project, including version lineage tracking for
    three-way merge support.
    """

    artifact_name: str = Field(
        description="Name of the artifact",
        examples=["pdf"],
    )
    artifact_type: str = Field(
        description="Type of artifact (skill, command, agent, etc.)",
        examples=["skill"],
    )
    drift_type: Literal[
        "modified",
        "outdated",
        "conflict",
        "added",
        "removed",
        "version_mismatch",
    ] = Field(
        description=(
            "Type of drift detected:\n"
            "- modified: Artifact modified in project only (local changes)\n"
            "- outdated: Artifact modified in collection only (upstream changes)\n"
            "- conflict: Both project and collection modified (three-way conflict)\n"
            "- added: Artifact added to collection (not in project)\n"
            "- removed: Artifact removed from collection\n"
            "- version_mismatch: Version changed but content may be same"
        ),
        examples=["modified"],
    )
    collection_sha: Optional[str] = Field(
        default=None,
        description="SHA from collection (None if artifact removed from collection)",
        examples=["abc123def456"],
    )
    project_sha: Optional[str] = Field(
        default=None,
        description="SHA from project (None if artifact added to collection)",
        examples=["def456ghi789"],
    )
    collection_version: Optional[str] = Field(
        default=None,
        description="Version in collection (None if removed)",
        examples=["v2.1.0"],
    )
    project_version: Optional[str] = Field(
        default=None,
        description="Version in project (None if added)",
        examples=["v2.0.0"],
    )
    last_deployed: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of last deployment (None if never deployed)",
        examples=["2025-12-13T10:00:00Z"],
    )
    recommendation: str = Field(
        description="Recommended sync action",
        examples=["pull_from_collection"],
    )

    # Phase 3: Change Attribution Fields
    change_origin: Optional[str] = Field(
        default=None,
        description=(
            "Origin of the change that caused drift:\n"
            "- 'deployment': Change came from deploying a collection artifact\n"
            "- 'sync': Change came from syncing with upstream\n"
            "- 'local_modification': Change made directly in project\n"
            "None if no change detected (drift_type='added')"
        ),
        examples=["local_modification"],
    )
    baseline_hash: Optional[str] = Field(
        default=None,
        description=(
            "Hash at deployment time (merge base for three-way merge).\n"
            "This is the deployed.sha from deployment metadata - represents\n"
            "the common ancestor for merge operations."
        ),
        examples=["xyz789abc123"],
    )
    current_hash: Optional[str] = Field(
        default=None,
        description="Current hash of the artifact in the project",
        examples=["def456ghi789"],
    )
    modification_detected_at: Optional[datetime] = Field(
        default=None,
        description="When modification was first detected (None if no drift)",
        examples=["2025-12-17T15:30:00Z"],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "drift_type": "modified",
                "collection_sha": "abc123def456",
                "project_sha": "def456ghi789",
                "collection_version": "v2.1.0",
                "project_version": "v2.1.0",
                "last_deployed": "2025-12-13T10:00:00Z",
                "recommendation": "review_manually",
                "change_origin": "local_modification",
                "baseline_hash": "xyz789abc123",
                "current_hash": "def456ghi789",
                "modification_detected_at": "2025-12-17T15:30:00Z",
            }
        }


class DriftSummaryResponse(BaseModel):
    """Summary of drift detection results across all artifacts."""

    project_path: str = Field(
        description="Path to the project directory",
        examples=["/path/to/project"],
    )
    collection_name: str = Field(
        description="Name of the collection being compared",
        examples=["default"],
    )
    total_artifacts: int = Field(
        description="Total number of artifacts checked",
        examples=[10],
    )
    drifted_count: int = Field(
        description="Number of artifacts with drift detected",
        examples=[3],
    )
    modified_count: int = Field(
        description="Number of artifacts modified in project only",
        examples=[1],
    )
    outdated_count: int = Field(
        description="Number of artifacts modified in collection only",
        examples=[1],
    )
    conflict_count: int = Field(
        description="Number of artifacts with three-way conflicts",
        examples=[0],
    )
    added_count: int = Field(
        description="Number of artifacts added to collection",
        examples=[1],
    )
    removed_count: int = Field(
        description="Number of artifacts removed from collection",
        examples=[0],
    )
    version_mismatch_count: int = Field(
        description="Number of artifacts with version mismatches",
        examples=[0],
    )
    # TASK-4.3: Summary count fields
    upstream_changes: int = Field(
        description="Count of upstream changes (outdated, added, removed drift)",
        examples=[2],
    )
    local_changes: int = Field(
        description="Count of local changes (modified drift)",
        examples=[1],
    )
    conflicts: int = Field(
        description="Count of conflicts (conflict drift)",
        examples=[0],
    )
    total: int = Field(
        description="Total artifacts with any drift",
        examples=[3],
    )
    drift_details: List[DriftDetectionResponse] = Field(
        default_factory=list,
        description="Detailed drift information for each drifted artifact",
    )
    checked_at: datetime = Field(
        description="Timestamp when drift detection was performed",
        examples=["2025-12-17T15:30:00Z"],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "project_path": "/path/to/project",
                "collection_name": "default",
                "total_artifacts": 10,
                "drifted_count": 3,
                "modified_count": 1,
                "outdated_count": 1,
                "conflict_count": 0,
                "added_count": 1,
                "removed_count": 0,
                "version_mismatch_count": 0,
                "upstream_changes": 2,  # outdated + added
                "local_changes": 1,  # modified
                "conflicts": 0,
                "total": 3,
                "drift_details": [
                    {
                        "artifact_name": "pdf",
                        "artifact_type": "skill",
                        "drift_type": "modified",
                        "collection_sha": "abc123def456",
                        "project_sha": "def456ghi789",
                        "collection_version": "v2.1.0",
                        "project_version": "v2.1.0",
                        "last_deployed": "2025-12-13T10:00:00Z",
                        "recommendation": "review_manually",
                        "change_origin": "local_modification",
                        "baseline_hash": "xyz789abc123",
                        "current_hash": "def456ghi789",
                        "modification_detected_at": "2025-12-17T15:30:00Z",
                    }
                ],
                "checked_at": "2025-12-17T15:30:00Z",
            }
        }
