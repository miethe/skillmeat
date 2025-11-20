"""Project API schemas for request and response models."""

from datetime import datetime
from typing import List, Optional

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
