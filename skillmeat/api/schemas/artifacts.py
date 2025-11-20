"""Artifact API schemas for request and response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import PaginatedResponse


class ArtifactMetadataResponse(BaseModel):
    """Artifact metadata from SKILL.md / COMMAND.md / AGENT.md."""

    title: Optional[str] = Field(
        default=None,
        description="Artifact title",
        examples=["PDF Processing Skill"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Artifact description",
        examples=["Extract and analyze PDF documents"],
    )
    author: Optional[str] = Field(
        default=None,
        description="Artifact author",
        examples=["Anthropic"],
    )
    license: Optional[str] = Field(
        default=None,
        description="Artifact license",
        examples=["MIT"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Artifact version from metadata",
        examples=["1.2.3"],
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Artifact tags",
        examples=[["document", "pdf", "productivity"]],
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Required dependencies",
        examples=[["python-magic", "PyPDF2"]],
    )


class ArtifactUpstreamInfo(BaseModel):
    """Upstream tracking information for an artifact."""

    tracking_enabled: bool = Field(
        description="Whether upstream tracking is enabled",
        examples=[True],
    )
    current_sha: Optional[str] = Field(
        default=None,
        description="Current installed version SHA",
        examples=["abc123def456"],
    )
    upstream_sha: Optional[str] = Field(
        default=None,
        description="Latest upstream version SHA",
        examples=["def789ghi012"],
    )
    update_available: bool = Field(
        description="Whether an update is available",
        examples=[True],
    )
    has_local_modifications: bool = Field(
        description="Whether local modifications exist",
        examples=[False],
    )


class ArtifactResponse(BaseModel):
    """Response schema for a single artifact.

    Provides complete artifact information including metadata,
    deployment status, and upstream tracking.
    """

    id: str = Field(
        description="Artifact composite key (type:name)",
        examples=["skill:pdf"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["pdf"],
    )
    type: str = Field(
        description="Artifact type",
        examples=["skill"],
    )
    source: str = Field(
        description="Source specification",
        examples=["anthropics/skills/pdf"],
    )
    version: str = Field(
        description="Version specification",
        examples=["latest"],
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Artifact aliases",
        examples=[["pdf-processor", "doc-reader"]],
    )
    metadata: Optional[ArtifactMetadataResponse] = Field(
        default=None,
        description="Artifact metadata",
    )
    upstream: Optional[ArtifactUpstreamInfo] = Field(
        default=None,
        description="Upstream tracking information",
    )
    added: datetime = Field(
        description="Timestamp when artifact was added to collection",
    )
    updated: datetime = Field(
        description="Timestamp of last update",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "skill:pdf",
                "name": "pdf",
                "type": "skill",
                "source": "anthropics/skills/pdf",
                "version": "latest",
                "aliases": ["pdf-processor"],
                "metadata": {
                    "title": "PDF Processing Skill",
                    "description": "Extract and analyze PDF documents",
                    "author": "Anthropic",
                    "license": "MIT",
                    "tags": ["document", "pdf"],
                },
                "upstream": {
                    "tracking_enabled": True,
                    "current_sha": "abc123",
                    "upstream_sha": "def456",
                    "update_available": True,
                    "has_local_modifications": False,
                },
                "added": "2024-11-16T12:00:00Z",
                "updated": "2024-11-16T15:30:00Z",
            }
        }


class ArtifactListResponse(PaginatedResponse[ArtifactResponse]):
    """Paginated response for artifact listings."""

    pass


class ArtifactUpstreamResponse(BaseModel):
    """Response for upstream status check.

    Provides detailed information about available updates and
    local modifications.
    """

    artifact_id: str = Field(
        description="Artifact composite key",
        examples=["skill:pdf"],
    )
    tracking_enabled: bool = Field(
        description="Whether upstream tracking is enabled",
        examples=[True],
    )
    current_version: str = Field(
        description="Current installed version",
        examples=["1.2.3"],
    )
    current_sha: str = Field(
        description="Current version SHA",
        examples=["abc123def456"],
    )
    upstream_version: Optional[str] = Field(
        default=None,
        description="Latest upstream version",
        examples=["1.3.0"],
    )
    upstream_sha: Optional[str] = Field(
        default=None,
        description="Latest upstream SHA",
        examples=["def789ghi012"],
    )
    update_available: bool = Field(
        description="Whether an update is available",
        examples=[True],
    )
    has_local_modifications: bool = Field(
        description="Whether local modifications exist",
        examples=[False],
    )
    last_checked: datetime = Field(
        description="Timestamp of last upstream check",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf",
                "tracking_enabled": True,
                "current_version": "1.2.3",
                "current_sha": "abc123def456",
                "upstream_version": "1.3.0",
                "upstream_sha": "def789ghi012",
                "update_available": True,
                "has_local_modifications": False,
                "last_checked": "2024-11-16T15:30:00Z",
            }
        }


class ArtifactUpdateMetadataRequest(BaseModel):
    """Request schema for updating artifact metadata fields."""

    title: Optional[str] = Field(
        default=None,
        description="Artifact title",
        examples=["PDF Processing Skill"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Artifact description",
        examples=["Extract and analyze PDF documents"],
    )
    author: Optional[str] = Field(
        default=None,
        description="Artifact author",
        examples=["Anthropic"],
    )
    license: Optional[str] = Field(
        default=None,
        description="Artifact license",
        examples=["MIT"],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Artifact tags",
        examples=[["document", "pdf", "productivity"]],
    )


class ArtifactUpdateRequest(BaseModel):
    """Request schema for updating an artifact.

    Allows updating metadata and tags. Note: aliases are not yet
    implemented in the backend but are included for future compatibility.
    """

    aliases: Optional[List[str]] = Field(
        default=None,
        description="Artifact aliases (not yet implemented)",
        examples=[["pdf-processor", "doc-reader"]],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Artifact tags",
        examples=[["document", "pdf", "productivity"]],
    )
    metadata: Optional[ArtifactUpdateMetadataRequest] = Field(
        default=None,
        description="Artifact metadata to update",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "tags": ["document", "pdf", "productivity"],
                "metadata": {
                    "title": "Enhanced PDF Processor",
                    "description": "Advanced PDF extraction and analysis",
                    "tags": ["document", "pdf"],
                },
            }
        }

class ArtifactDeployRequest(BaseModel):
    """Request schema for deploying an artifact."""

    project_path: str = Field(
        description="Path to target project directory",
        examples=["/Users/me/my-project"],
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing artifact if already deployed",
    )


class ArtifactDeployResponse(BaseModel):
    """Response schema for artifact deployment."""

    success: bool = Field(description="Whether deployment succeeded")
    message: str = Field(description="Human-readable result message")
    artifact_name: str = Field(description="Name of deployed artifact")
    artifact_type: str = Field(description="Type of artifact (skill/command/agent)")
    deployed_path: Optional[str] = Field(
        default=None,
        description="Path where artifact was deployed",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if deployment failed",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Artifact 'pdf' deployed successfully",
                "artifact_name": "pdf",
                "artifact_type": "skill",
                "deployed_path": "/Users/me/my-project/.claude/skills/pdf",
                "error_message": None,
            }
        }
