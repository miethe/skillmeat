"""Pydantic schemas for version history and conflict resolution APIs."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class VersionEntry(BaseModel):
    """Represents an entry in an artifact's version lineage."""

    hash: str = Field(description="Version hash (content hash)")
    timestamp: datetime = Field(description="Timestamp recorded")
    source: Optional[str] = Field(default=None, description="Source tier (upstream|collection|project|local)")
    parent_hash: Optional[str] = Field(default=None, description="Parent hash in lineage")
    message: Optional[str] = Field(default=None, description="Optional message or reason")


class VersionHistoryResponse(BaseModel):
    """Response containing version lineage for an artifact."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    versions: List[VersionEntry] = Field(default_factory=list, description="Ordered newest-first lineage entries")

