"""Pydantic schemas for deployment API endpoints.

Defines request and response models for artifact deployment operations.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from skillmeat.core.enums import Platform


# ====================
# Request Schemas
# ====================


class DeployRequest(BaseModel):
    """Request to deploy an artifact to a project."""

    artifact_id: str = Field(
        description="Artifact identifier (format: 'type:name')",
        examples=["skill:pdf"],
    )
    artifact_name: str = Field(
        description="Artifact name for display",
        examples=["pdf"],
    )
    artifact_type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    project_path: Optional[str] = Field(
        default=None,
        description="Path to project directory (uses CWD if not specified)",
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Source collection name (uses active collection if None)",
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing deployment without prompting",
    )
    dest_path: Optional[str] = Field(
        default=None,
        description="Custom destination path relative to project root "
        "(e.g., '.claude/skills/dev/'). If provided, artifact will be deployed "
        "to {dest_path}/{artifact_name}/. Must not contain '..' or be absolute.",
        examples=[".claude/skills/", ".claude/skills/dev/"],
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description="Optional deployment profile ID (uses primary profile when omitted)",
        examples=["codex-default"],
    )
    all_profiles: bool = Field(
        default=False,
        description="Deploy to all project deployment profiles",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf",
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "project_path": "/path/to/project",
                "collection_name": "default",
                "overwrite": False,
                "dest_path": ".claude/skills/dev/",
                "deployment_profile_id": "codex-default",
                "all_profiles": False,
            }
        }


class UndeployRequest(BaseModel):
    """Request to undeploy (remove) an artifact from a project."""

    artifact_name: str = Field(
        description="Artifact name",
        examples=["pdf"],
    )
    artifact_type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    project_path: Optional[str] = Field(
        default=None,
        description="Path to project directory (uses CWD if not specified)",
    )
    profile_id: Optional[str] = Field(
        default=None,
        description="Optional profile ID to undeploy from a single profile",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "project_path": "/path/to/project",
                "profile_id": "codex-default",
            }
        }


# ====================
# Response Schemas
# ====================


class DeploymentResponse(BaseModel):
    """Response from a deployment operation."""

    success: bool = Field(description="Whether deployment succeeded")
    message: str = Field(description="Status message")
    deployment_id: Optional[str] = Field(
        default=None,
        description="Deployment identifier (format: 'type:name')",
    )
    stream_url: Optional[str] = Field(
        default=None,
        description="SSE stream URL for progress updates (if supported)",
    )
    artifact_name: str = Field(description="Deployed artifact name")
    artifact_type: str = Field(description="Deployed artifact type")
    project_path: str = Field(description="Target project path")
    deployed_path: str = Field(description="Path where artifact was deployed")
    deployed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of deployment",
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description="Profile used for deployment (single-profile deploy)",
    )
    deployed_profiles: List[str] = Field(
        default_factory=list,
        description="Profiles that received the artifact deployment",
    )
    platform: Optional[Platform] = Field(
        default=None,
        description="Platform associated with deployment_profile_id",
    )
    profile_root_dir: Optional[str] = Field(
        default=None,
        description="Resolved profile root directory used for deployment",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Artifact deployed successfully",
                "deployment_id": "skill:pdf",
                "stream_url": None,
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "project_path": "/path/to/project",
                "deployed_path": ".claude/skills/pdf",
                "deployed_at": "2025-11-18T12:00:00Z",
            }
        }


class UndeployResponse(BaseModel):
    """Response from an undeploy operation."""

    success: bool = Field(description="Whether undeploy succeeded")
    message: str = Field(description="Status message")
    artifact_name: str = Field(description="Undeployed artifact name")
    artifact_type: str = Field(description="Undeployed artifact type")
    project_path: str = Field(description="Project path")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Artifact removed successfully",
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "project_path": "/path/to/project",
            }
        }


class DeploymentSummary(BaseModel):
    """Lightweight deployment summary for collection artifact responses.

    This schema matches the structure stored in CollectionArtifact.deployments_json
    and is used for efficient display of deployment counts and basic info.
    """

    project_path: str = Field(
        description="Absolute path to the project directory",
        examples=["/Users/user/project"],
    )
    project_name: str = Field(
        description="Display name of the project",
        examples=["myproject"],
    )
    deployed_at: datetime = Field(
        description="Deployment timestamp",
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 content hash at deployment time",
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description="Deployment profile identifier (e.g., 'claude_code', 'codex')",
    )
    local_modifications: Optional[bool] = Field(
        default=None,
        description="Whether local drift has been detected",
    )
    platform: Optional[str] = Field(
        default=None,
        description="Target platform for the deployment",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "project_path": "/Users/user/project",
                "project_name": "myproject",
                "deployed_at": "2026-02-01T10:00:00Z",
                "content_hash": "abc123def456",
                "deployment_profile_id": "claude_code",
                "local_modifications": False,
                "platform": "claude-code",
            }
        }


class DeploymentInfo(BaseModel):
    """Information about a single deployment."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    from_collection: str = Field(description="Source collection name")
    deployed_at: datetime = Field(description="Deployment timestamp")
    artifact_path: str = Field(description="Relative path within .claude/")
    project_path: str = Field(description="Absolute path to the project directory")
    collection_sha: str = Field(description="SHA at deployment time")
    local_modifications: bool = Field(
        default=False,
        description="Whether local modifications detected",
    )
    sync_status: Optional[str] = Field(
        default=None,
        description="Sync status: synced, modified, outdated",
    )
    merge_base_snapshot: Optional[str] = Field(
        default=None,
        description="Content hash (SHA-256) used as merge base for 3-way merges",
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description="Deployment profile identifier used for this deployment",
    )
    platform: Optional[Platform] = Field(
        default=None,
        description="Platform associated with the deployment profile",
    )
    profile_root_dir: Optional[str] = Field(
        default=None,
        description="Resolved profile root directory used for deployment",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "from_collection": "default",
                "deployed_at": "2025-11-18T12:00:00Z",
                "artifact_path": "skills/pdf",
                "project_path": "/path/to/project",
                "collection_sha": "abc123def456",
                "local_modifications": False,
                "sync_status": "synced",
            }
        }


class DeploymentListResponse(BaseModel):
    """Response listing all deployments in a project."""

    project_path: str = Field(description="Project directory path")
    deployments: List[DeploymentInfo] = Field(
        default_factory=list,
        description="List of deployments",
    )
    deployments_by_profile: Dict[str, List[DeploymentInfo]] = Field(
        default_factory=dict,
        description="Deployments grouped by deployment profile ID",
    )
    total: int = Field(description="Total number of deployments")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "project_path": "/path/to/project",
                "deployments": [
                    {
                        "artifact_name": "pdf",
                        "artifact_type": "skill",
                        "from_collection": "default",
                        "deployed_at": "2025-11-18T12:00:00Z",
                        "artifact_path": "skills/pdf",
                        "collection_sha": "abc123def456",
                        "local_modifications": False,
                        "sync_status": "synced",
                    }
                ],
                "total": 1,
            }
        }
