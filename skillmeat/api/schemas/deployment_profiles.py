"""Pydantic schemas for deployment profile API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from skillmeat.core.enums import Platform


class DeploymentProfileCreate(BaseModel):
    """Request schema for creating a deployment profile."""

    profile_id: str = Field(description="Profile identifier unique per project")
    platform: Platform = Field(description="Target platform for this profile")
    root_dir: str = Field(description="Profile root directory")
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Human-readable description of the deployment profile",
    )
    artifact_path_map: Dict[str, str] = Field(default_factory=dict)
    project_config_filenames: List[str] = Field(default_factory=list)
    context_path_prefixes: List[str] = Field(default_factory=list)
    supported_artifact_types: List[str] = Field(default_factory=list)


class DeploymentProfileUpdate(BaseModel):
    """Request schema for updating a deployment profile.

    profile_id is intentionally immutable and therefore excluded.
    """

    platform: Optional[Platform] = None
    root_dir: Optional[str] = None
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Human-readable description of the deployment profile",
    )
    artifact_path_map: Optional[Dict[str, str]] = None
    project_config_filenames: Optional[List[str]] = None
    context_path_prefixes: Optional[List[str]] = None
    supported_artifact_types: Optional[List[str]] = None


class DeploymentProfileRead(BaseModel):
    """Response schema for deployment profiles."""

    id: str
    project_id: str
    profile_id: str
    platform: Platform
    root_dir: str
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Human-readable description of the deployment profile",
    )
    artifact_path_map: Dict[str, str] = Field(default_factory=dict)
    project_config_filenames: List[str] = Field(default_factory=list)
    context_path_prefixes: List[str] = Field(default_factory=list)
    supported_artifact_types: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic model configuration."""

        from_attributes = True

