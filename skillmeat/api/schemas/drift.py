"""Pydantic schemas for drift detection."""

from typing import List, Optional

from pydantic import BaseModel, Field


class DriftArtifact(BaseModel):
    """Represents drift state for a single artifact."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    drift_type: str = Field(description="Drift type (modified|added|removed|version_mismatch)")
    collection_sha: Optional[str] = Field(default=None, description="Collection SHA")
    project_sha: Optional[str] = Field(default=None, description="Project SHA")
    collection_version: Optional[str] = Field(default=None, description="Collection version")
    project_version: Optional[str] = Field(default=None, description="Project version")
    recommendation: Optional[str] = Field(default=None, description="Recommended action")
    sync_status: Optional[str] = Field(default=None, description="Sync status enum")


class DriftResponse(BaseModel):
    """Response for drift detection."""

    drift_detected: bool = Field(description="Whether any drift detected")
    drift_count: int = Field(description="Number of drifted artifacts")
    artifacts: List[DriftArtifact] = Field(default_factory=list)

