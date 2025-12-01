"""Project API schemas for request and response models."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .common import PageInfo, PaginatedResponse


class DeployedArtifact(BaseModel):
    """Summary of a deployed artifact within a project.

    Represents an artifact that has been deployed from a collection
    to a specific project location.
    """

    artifact_name: str = Field(
        description="Name of the deployed artifact",
        examples=["canvas-design"],
    )
    artifact_type: str = Field(
        description="Type of artifact (skill, command, agent, mcp, hook)",
        examples=["skill"],
    )
    from_collection: str = Field(
        description="Source collection name",
        examples=["default"],
    )
    deployed_at: datetime = Field(
        description="Deployment timestamp",
    )
    artifact_path: str = Field(
        description="Relative path within .claude/ directory",
        examples=["skills/canvas-design"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Artifact version at deployment time",
        examples=["v2.1.0"],
    )
    collection_sha: str = Field(
        description="Content hash at deployment time",
        examples=["abc123def456..."],
    )
    local_modifications: bool = Field(
        default=False,
        description="Whether local modifications detected",
    )


class CacheInfo(BaseModel):
    """Cache metadata for cached responses."""

    cache_hit: bool = Field(
        description="Whether this response was served from cache",
        examples=[True],
    )
    last_fetched: Optional[datetime] = Field(
        default=None,
        description="When this data was last fetched/refreshed",
    )
    is_stale: bool = Field(
        default=False,
        description="Whether the cached data is considered stale (past TTL)",
    )


class ProjectSummary(BaseModel):
    """Summary information about a project with deployments.

    Provides high-level project metadata including deployment counts
    and last deployment time.
    """

    id: str = Field(
        description="Base64-encoded project path (unique identifier)",
        examples=["L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA=="],
    )
    path: str = Field(
        description="Absolute filesystem path to project",
        examples=["/Users/john/projects/my-project"],
    )
    name: str = Field(
        description="Project name (directory name)",
        examples=["my-project"],
    )
    deployment_count: int = Field(
        description="Total number of deployed artifacts",
        examples=[5],
        ge=0,
    )
    last_deployment: Optional[datetime] = Field(
        default=None,
        description="Timestamp of most recent deployment",
    )
    cache_info: Optional[CacheInfo] = Field(
        default=None,
        description="Cache metadata (only present when served from cache)",
    )


class ProjectDetail(BaseModel):
    """Detailed information about a project including all deployments.

    Extends ProjectSummary with complete list of deployed artifacts
    and aggregated statistics.
    """

    id: str = Field(
        description="Base64-encoded project path (unique identifier)",
        examples=["L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA=="],
    )
    path: str = Field(
        description="Absolute filesystem path to project",
        examples=["/Users/john/projects/my-project"],
    )
    name: str = Field(
        description="Project name (directory name)",
        examples=["my-project"],
    )
    deployment_count: int = Field(
        description="Total number of deployed artifacts",
        examples=[5],
        ge=0,
    )
    last_deployment: Optional[datetime] = Field(
        default=None,
        description="Timestamp of most recent deployment",
    )
    deployments: List[DeployedArtifact] = Field(
        description="Complete list of deployed artifacts",
        default_factory=list,
    )
    stats: dict = Field(
        description="Aggregated deployment statistics",
        examples=[
            {
                "by_type": {"skill": 3, "command": 2},
                "by_collection": {"default": 4, "custom": 1},
                "modified_count": 1,
            }
        ],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA==",
                "path": "/Users/john/projects/my-project",
                "name": "my-project",
                "deployment_count": 5,
                "last_deployment": "2024-11-16T15:30:00Z",
                "deployments": [
                    {
                        "artifact_name": "canvas-design",
                        "artifact_type": "skill",
                        "from_collection": "default",
                        "deployed_at": "2024-11-16T15:30:00Z",
                        "artifact_path": "skills/canvas-design",
                        "version": "v2.1.0",
                        "collection_sha": "abc123",
                        "local_modifications": False,
                    }
                ],
                "stats": {
                    "by_type": {"skill": 3, "command": 2},
                    "by_collection": {"default": 5},
                    "modified_count": 0,
                },
            }
        }


class ProjectListResponse(PaginatedResponse[ProjectSummary]):
    """Paginated response for project listings.

    Extends the generic paginated response with project-specific items.
    """

    pass


class ModifiedArtifactInfo(BaseModel):
    """Information about a modified artifact in a project."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    deployed_sha: str = Field(description="SHA-256 hash at deployment time")
    current_sha: str = Field(description="Current SHA-256 hash")
    modification_detected_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when modification was first detected",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf-processor",
                "artifact_type": "skill",
                "deployed_sha": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
                "current_sha": "def789ghi012345ghijkl678901234ghijkl678901234ghijkl678901234gh",
                "modification_detected_at": "2025-11-20T15:45:00Z",
            }
        }


class ModifiedArtifactsResponse(BaseModel):
    """Response for modified artifacts in a project.

    Lists all artifacts in a project that have been modified
    since deployment.
    """

    project_id: str = Field(
        description="Base64-encoded project path",
        examples=["L1VzZXJzL21lL3Byb2plY3Qx"],
    )
    modified_artifacts: List[ModifiedArtifactInfo] = Field(
        description="List of modified artifacts"
    )
    total_count: int = Field(
        description="Total number of modified artifacts",
        ge=0,
    )
    last_checked: datetime = Field(
        description="Timestamp when modifications were last checked"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "project_id": "L1VzZXJzL21lL3Byb2plY3Qx",
                "modified_artifacts": [
                    {
                        "artifact_name": "pdf-processor",
                        "artifact_type": "skill",
                        "deployed_sha": "abc123",
                        "current_sha": "def456",
                        "modification_detected_at": "2025-11-20T15:45:00Z",
                    }
                ],
                "total_count": 2,
                "last_checked": "2025-11-20T16:00:00Z",
            }
        }


class ProjectCreateRequest(BaseModel):
    """Request schema for creating a project."""

    name: str = Field(
        description="Project name (1-100 characters, letters, numbers, hyphens, underscores only)",
        examples=["my-awesome-project"],
        min_length=1,
        max_length=100,
    )
    path: str = Field(
        description="Absolute path to project directory",
        examples=["/Users/john/projects/my-awesome-project"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Project description",
        examples=["A project for managing Claude configurations"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate project name format.

        Requirements:
        - 1-100 characters (handled by Field constraints)
        - Only letters, numbers, hyphens, underscores
        - Cannot start or end with hyphen or underscore

        Args:
            v: The project name to validate

        Returns:
            The validated name

        Raises:
            ValueError: If name format is invalid
        """
        # Check for valid characters: alphanumeric, hyphen, underscore
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$", v):
            raise ValueError(
                "Project name must start and end with alphanumeric characters "
                "and can only contain letters, numbers, hyphens, and underscores"
            )
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate project path format.

        Requirements:
        - Must be an absolute path
        - Must have valid filesystem path characters
        - Platform-specific invalid character detection

        Args:
            v: The project path to validate

        Returns:
            The validated path

        Raises:
            ValueError: If path is invalid
        """
        # Must be absolute path
        if not os.path.isabs(v):
            raise ValueError("Project path must be an absolute path (e.g., /home/user/project or C:\\Users\\project)")

        # Check for invalid characters (platform-specific)
        # Windows reserved characters
        if os.name == "nt":
            invalid_chars = '<>"|?*'
            if any(c in v for c in invalid_chars):
                raise ValueError(
                    f"Project path contains invalid Windows characters: {invalid_chars}"
                )
        # Unix null character
        else:
            if "\0" in v:
                raise ValueError("Project path contains null character")

        # Validate path doesn't have consecutive separators or other obvious issues
        try:
            Path(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid path format: {str(e)}")

        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "my-awesome-project",
                "path": "/Users/john/projects/my-awesome-project",
                "description": "A project for managing Claude configurations",
            }
        }


class ProjectUpdateRequest(BaseModel):
    """Request schema for updating a project."""

    name: Optional[str] = Field(
        default=None,
        description="New project name (1-100 characters, letters, numbers, hyphens, underscores only)",
        examples=["renamed-project"],
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="New project description",
        examples=["Updated project description"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate project name format if provided.

        Requirements:
        - 1-100 characters (handled by Field constraints)
        - Only letters, numbers, hyphens, underscores
        - Cannot start or end with hyphen or underscore

        Args:
            v: The project name to validate (or None)

        Returns:
            The validated name or None

        Raises:
            ValueError: If name format is invalid
        """
        # Skip validation if name is not provided
        if v is None:
            return v

        # Check for valid characters: alphanumeric, hyphen, underscore
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$", v):
            raise ValueError(
                "Project name must start and end with alphanumeric characters "
                "and can only contain letters, numbers, hyphens, and underscores"
            )
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "renamed-project",
                "description": "Updated project description",
            }
        }


class ProjectCreateResponse(BaseModel):
    """Response for project creation."""

    id: str = Field(
        description="Base64-encoded project path (unique identifier)",
        examples=["L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA=="],
    )
    path: str = Field(
        description="Absolute filesystem path to project",
        examples=["/Users/john/projects/my-project"],
    )
    name: str = Field(
        description="Project name",
        examples=["my-project"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Project description",
    )
    created_at: datetime = Field(
        description="Project creation timestamp",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "L1VzZXJzL2pvaG4vcHJvamVjdHMvbXktcHJvamVjdA==",
                "path": "/Users/john/projects/my-project",
                "name": "my-project",
                "description": "A sample project",
                "created_at": "2025-11-24T12:00:00Z",
            }
        }


class ProjectDeleteResponse(BaseModel):
    """Response for project deletion."""

    success: bool = Field(
        description="Whether the deletion was successful",
        examples=[True],
    )
    message: str = Field(
        description="Human-readable status message",
        examples=["Project removed from tracking successfully"],
    )
    deleted_files: bool = Field(
        default=False,
        description="Whether project files were deleted from disk",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Project removed from tracking successfully",
                "deleted_files": False,
            }
        }
