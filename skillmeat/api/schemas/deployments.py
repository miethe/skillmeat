"""Pydantic schemas for deployment API endpoints.

Defines request and response models for artifact deployment operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


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

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "project_path": "/path/to/project",
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


class DeploymentInfo(BaseModel):
    """Information about a single deployment."""

    artifact_name: str = Field(description="Artifact name")
    artifact_type: str = Field(description="Artifact type")
    from_collection: str = Field(description="Source collection name")
    deployed_at: datetime = Field(description="Deployment timestamp")
    artifact_path: str = Field(description="Relative path within .claude/")
    collection_sha: str = Field(description="SHA at deployment time (deprecated; see content_hash)")
    content_hash: Optional[str] = Field(
        default=None,
        description="Canonical content hash at deployment time",
    )
    parent_hash: Optional[str] = Field(
        default=None,
        description="Parent hash when deployed (previous version hash)",
    )
    version_lineage: List[str] = Field(
        default_factory=list,
        description="Ordered list of version hashes, newest first",
    )
    last_modified_check: Optional[datetime] = Field(
        default=None, description="Timestamp of last drift check"
    )
    modification_detected_at: Optional[datetime] = Field(
        default=None, description="When local modification was first detected"
    )
    upstream_ref: Optional[str] = Field(
        default=None, description="Upstream reference (e.g., github URL)"
    )
    upstream_version: Optional[str] = Field(
        default=None, description="Resolved upstream version/tag"
    )
    upstream_sha: Optional[str] = Field(
        default=None, description="Resolved upstream commit SHA"
    )
    last_upstream_check: Optional[datetime] = Field(
        default=None, description="Last time upstream was checked for updates"
    )
    local_modifications: bool = Field(
        default=False,
        description="Whether local modifications detected",
    )
    sync_status: Optional[str] = Field(
        default=None,
        description="Sync status: synced, modified, outdated",
    )
    pending_conflicts: List[dict] = Field(
        default_factory=list,
        description="Structured conflict entries awaiting resolution",
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
                "collection_sha": "abc123def456",
                "content_hash": "abc123def456",
                "parent_hash": "xyz789",
                "version_lineage": ["abc123def456", "xyz789"],
                "last_modified_check": "2025-11-18T12:05:00Z",
                "modification_detected_at": None,
                "upstream_ref": "https://github.com/org/repo/tree/main/skills/pdf",
                "upstream_version": "v1.2.0",
                "upstream_sha": "abc123def456",
                "last_upstream_check": "2025-11-18T12:01:00Z",
                "local_modifications": False,
                "sync_status": "synced",
                "pending_conflicts": [],
            }
        }


class DeploymentListResponse(BaseModel):
    """Response listing all deployments in a project."""

    project_path: str = Field(description="Project directory path")
    deployments: List[DeploymentInfo] = Field(
        default_factory=list,
        description="List of deployments",
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
