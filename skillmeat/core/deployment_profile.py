"""Core deployment profile model for multi-platform project deployments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator

from skillmeat.core.enums import Platform


class DeploymentProfile(BaseModel):
    """Platform-specific deployment contract for a project.

    Attributes:
        profile_id: Stable profile identifier unique within a project.
        platform: Target platform this profile serves.
        root_dir: Profile root directory relative to project root.
        artifact_path_map: Mapping of artifact type to relative target path.
        project_config_filenames: Supported project config filenames in this profile.
        context_path_prefixes: Allowed context entity path prefixes for this profile.
        supported_artifact_types: Artifact types deployable to this profile.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    profile_id: str = Field(description="Unique profile identifier within the project")
    platform: Platform = Field(description="Deployment platform for this profile")
    root_dir: str = Field(description="Profile root directory path")
    artifact_path_map: Dict[str, str] = Field(default_factory=dict)
    project_config_filenames: List[str] = Field(default_factory=list)
    context_path_prefixes: List[str] = Field(default_factory=list)
    supported_artifact_types: List[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )

    @field_validator("profile_id")
    @classmethod
    def _validate_profile_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("profile_id cannot be empty")
        return value

    @field_validator("root_dir")
    @classmethod
    def _validate_root_dir(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("root_dir cannot be empty")
        return value
