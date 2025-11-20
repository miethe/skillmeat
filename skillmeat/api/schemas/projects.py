"""Project API schemas for request and response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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
