"""Pydantic schemas for deployment sets API endpoints.

Defines request and response models for deployment set CRUD operations,
member management, artifact resolution, and batch deployment.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


# ====================
# Deployment Set Schemas
# ====================


class DeploymentSetCreate(BaseModel):
    """Request to create a new deployment set."""

    name: str = Field(
        description="Deployment set name",
        examples=["My Dev Setup"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the deployment set",
        examples=["Skills and commands for backend development"],
    )
    icon: Optional[str] = Field(
        default=None,
        description="Optional icon identifier or emoji",
        examples=["🛠️", "code"],
    )
    color: Optional[str] = Field(
        default=None,
        description="Optional color hex code or name",
        examples=["#3b82f6", "blue"],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional list of tag names to associate with this set",
        examples=[["backend", "python"]],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "My Dev Setup",
                "description": "Skills and commands for backend development",
                "icon": "🛠️",
                "color": "#3b82f6",
                "tags": ["backend", "python"],
            }
        }


class DeploymentSetUpdate(BaseModel):
    """Request to partially update a deployment set (all fields optional)."""

    name: Optional[str] = Field(
        default=None,
        description="Updated deployment set name",
        examples=["Updated Dev Setup"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated description",
        examples=["Updated description"],
    )
    icon: Optional[str] = Field(
        default=None,
        description="Updated icon identifier or emoji",
        examples=["🚀"],
    )
    color: Optional[str] = Field(
        default=None,
        description="Updated color hex code or name",
        examples=["#10b981"],
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Updated list of tag names (replaces existing tags)",
        examples=[["backend", "typescript"]],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "Updated Dev Setup",
                "color": "#10b981",
            }
        }


class DeploymentSetResponse(BaseModel):
    """Response schema for a deployment set."""

    id: int = Field(description="Deployment set primary key")
    name: str = Field(description="Deployment set name")
    description: Optional[str] = Field(
        default=None,
        description="Optional description",
    )
    icon: Optional[str] = Field(
        default=None,
        description="Optional icon identifier or emoji",
    )
    color: Optional[str] = Field(
        default=None,
        description="Optional color hex code or name",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tag names associated with this set",
    )
    owner_id: Optional[str] = Field(
        default=None,
        description="Owner identifier (user ID or collection ID)",
    )
    member_count: int = Field(
        default=0,
        description="Number of members in this deployment set",
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True

        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "My Dev Setup",
                "description": "Skills and commands for backend development",
                "icon": "🛠️",
                "color": "#3b82f6",
                "tags": ["backend", "python"],
                "owner_id": "user-123",
                "member_count": 5,
                "created_at": "2026-02-24T10:00:00Z",
                "updated_at": "2026-02-24T10:00:00Z",
            }
        }


class DeploymentSetListResponse(BaseModel):
    """Response listing deployment sets with pagination metadata."""

    items: List[DeploymentSetResponse] = Field(
        description="List of deployment sets",
    )
    total: int = Field(description="Total number of deployment sets")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "items": [],
                "total": 0,
            }
        }


# ====================
# Member Schemas
# ====================


class MemberCreate(BaseModel):
    """Request to add a member to a deployment set.

    Exactly one of artifact_uuid, group_id, or nested_set_id must be provided.
    """

    artifact_uuid: Optional[str] = Field(
        default=None,
        description="UUID of the artifact to add as a member",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    group_id: Optional[int] = Field(
        default=None,
        description="ID of the group to add as a member",
        examples=[42],
    )
    nested_set_id: Optional[int] = Field(
        default=None,
        description="ID of the nested deployment set to add as a member",
        examples=[7],
    )
    position: Optional[int] = Field(
        default=None,
        description="Optional ordering position within the set",
        examples=[0],
    )

    @model_validator(mode="after")
    def validate_exactly_one_ref(self) -> "MemberCreate":
        """Ensure exactly one of artifact_uuid, group_id, nested_set_id is set."""
        refs = [
            self.artifact_uuid is not None,
            self.group_id is not None,
            self.nested_set_id is not None,
        ]
        count = sum(refs)
        if count == 0:
            raise ValueError(
                "Exactly one of 'artifact_uuid', 'group_id', or 'nested_set_id' must be provided"
            )
        if count > 1:
            raise ValueError(
                "Only one of 'artifact_uuid', 'group_id', or 'nested_set_id' may be provided"
            )
        return self

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "position": 0,
            }
        }


class MemberUpdatePosition(BaseModel):
    """Request to update a member's position within a deployment set."""

    position: int = Field(
        description="New ordering position for this member",
        examples=[2],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "position": 2,
            }
        }


class MemberResponse(BaseModel):
    """Response schema for a deployment set member."""

    id: int = Field(description="Member primary key")
    deployment_set_id: int = Field(description="ID of the parent deployment set")
    artifact_uuid: Optional[str] = Field(
        default=None,
        description="UUID of the artifact member (if member_type is 'artifact')",
    )
    group_id: Optional[int] = Field(
        default=None,
        description="ID of the group member (if member_type is 'group')",
    )
    nested_set_id: Optional[int] = Field(
        default=None,
        description="ID of the nested deployment set (if member_type is 'set')",
    )
    member_type: str = Field(
        description="Type of member: 'artifact', 'group', or 'set'",
        examples=["artifact", "group", "set"],
    )
    position: Optional[int] = Field(
        default=None,
        description="Ordering position within the set",
    )
    added_at: datetime = Field(description="Timestamp when this member was added")

    class Config:
        """Pydantic config."""

        from_attributes = True

        json_schema_extra = {
            "example": {
                "id": 1,
                "deployment_set_id": 1,
                "artifact_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "group_id": None,
                "nested_set_id": None,
                "member_type": "artifact",
                "position": 0,
                "added_at": "2026-02-24T10:00:00Z",
            }
        }


# ====================
# Resolution Schemas
# ====================


class ResolvedArtifactItem(BaseModel):
    """A single artifact resolved from a deployment set traversal."""

    artifact_uuid: str = Field(
        description="UUID of the resolved artifact",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Human-readable artifact name",
        examples=["pdf-skill"],
    )
    artifact_type: Optional[str] = Field(
        default=None,
        description="Artifact type (e.g., 'skill', 'command', 'agent')",
        examples=["skill"],
    )
    source_path: List[str] = Field(
        default_factory=list,
        description="Resolution trace: ordered list of set/group names traversed to reach this artifact",
        examples=[["My Dev Setup", "Python Tools Group"]],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "artifact_name": "pdf-skill",
                "artifact_type": "skill",
                "source_path": ["My Dev Setup", "Python Tools Group"],
            }
        }


class ResolveResponse(BaseModel):
    """Response for deployment set artifact resolution."""

    set_id: int = Field(description="ID of the resolved deployment set")
    set_name: str = Field(description="Name of the resolved deployment set")
    resolved_artifacts: List[ResolvedArtifactItem] = Field(
        default_factory=list,
        description="All artifacts reachable from this deployment set",
    )
    total_count: int = Field(
        description="Total number of unique resolved artifacts",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "set_id": 1,
                "set_name": "My Dev Setup",
                "resolved_artifacts": [],
                "total_count": 0,
            }
        }


# ====================
# Batch Deploy Schemas
# ====================


class BatchDeployRequest(BaseModel):
    """Request to batch deploy all artifacts in a deployment set."""

    project_path: str = Field(
        description="Absolute path to the target project directory",
        examples=["/Users/user/my-project"],
    )
    dry_run: bool = Field(
        default=False,
        description="If true, simulate deployment without writing files",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "project_path": "/Users/user/my-project",
                "dry_run": False,
            }
        }


class DeployResultItem(BaseModel):
    """Result for a single artifact in a batch deployment."""

    artifact_uuid: str = Field(
        description="UUID of the artifact that was deployed (or attempted)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Human-readable artifact name",
        examples=["pdf-skill"],
    )
    status: str = Field(
        description="Deployment status: 'success', 'failed', or 'skipped'",
        examples=["success", "failed", "skipped"],
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if status is 'failed'",
        examples=["Artifact not found in collection"],
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "artifact_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "artifact_name": "pdf-skill",
                "status": "success",
                "error": None,
            }
        }


class BatchDeployResponse(BaseModel):
    """Response from a batch deployment operation."""

    set_id: int = Field(description="ID of the deployment set that was deployed")
    set_name: str = Field(description="Name of the deployment set")
    project_path: str = Field(description="Target project path")
    total: int = Field(description="Total number of artifacts attempted")
    succeeded: int = Field(description="Number of artifacts successfully deployed")
    failed: int = Field(description="Number of artifacts that failed to deploy")
    skipped: int = Field(description="Number of artifacts skipped (e.g., already up-to-date)")
    results: List[DeployResultItem] = Field(
        default_factory=list,
        description="Per-artifact deployment results",
    )
    dry_run: bool = Field(
        default=False,
        description="Whether this was a dry run (no files written)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "set_id": 1,
                "set_name": "My Dev Setup",
                "project_path": "/Users/user/my-project",
                "total": 3,
                "succeeded": 2,
                "failed": 1,
                "skipped": 0,
                "results": [],
                "dry_run": False,
            }
        }
