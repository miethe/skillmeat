"""Pydantic schemas for artifact version metadata surfaces."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArtifactTierVersion(BaseModel):
    """Metadata for a specific tier (upstream|collection|project)."""

    tier: str = Field(description="Tier identifier")
    hash: Optional[str] = Field(default=None, description="Content hash")
    timestamp: Optional[datetime] = Field(
        default=None, description="Timestamp for this version if known"
    )
    source: Optional[str] = Field(default=None, description="Source reference (branch/tag/path)")
    sync_status: Optional[str] = Field(default=None, description="Sync status flag if known")


class ArtifactVersionsResponse(BaseModel):
    """Response payload for artifact versions across tiers."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    upstream: ArtifactTierVersion = Field(description="Upstream tier metadata")
    collection: ArtifactTierVersion = Field(description="Collection tier metadata")
    project: ArtifactTierVersion = Field(description="Project tier metadata")
