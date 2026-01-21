"""Groups API schemas for request and response models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    """Request schema for creating a new group in a collection.

    Groups provide a way to organize artifacts within a collection.
    """

    collection_id: str = Field(
        description="ID of the collection this group belongs to",
        examples=["default"],
    )
    name: str = Field(
        description="Group name (must be unique within collection)",
        min_length=1,
        max_length=255,
        examples=["Frontend Development", "Backend Tools"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional detailed description of the group",
        examples=["Skills and tools for frontend development"],
    )
    position: int = Field(
        default=0,
        ge=0,
        description="Display order within collection (0-based)",
        examples=[0, 1, 2],
    )


class GroupUpdateRequest(BaseModel):
    """Request schema for updating a group.

    All fields are optional. Only provided fields will be updated.
    """

    name: Optional[str] = Field(
        default=None,
        description="New group name",
        min_length=1,
        max_length=255,
        examples=["Updated Group Name"],
    )
    description: Optional[str] = Field(
        default=None,
        description="New description",
        examples=["Updated description"],
    )
    position: Optional[int] = Field(
        default=None,
        ge=0,
        description="New position in collection",
        examples=[0, 1, 2],
    )


class GroupPositionUpdate(BaseModel):
    """Schema for updating group position in bulk reorder operations."""

    id: str = Field(
        description="Group ID",
        examples=["abc123"],
    )
    position: int = Field(
        ge=0,
        description="New position",
        examples=[0, 1, 2],
    )


class GroupReorderRequest(BaseModel):
    """Request schema for bulk reordering groups within a collection."""

    groups: List[GroupPositionUpdate] = Field(
        description="List of groups with their new positions",
        min_length=1,
    )


class AddGroupArtifactsRequest(BaseModel):
    """Request schema for adding artifacts to a group."""

    artifact_ids: List[str] = Field(
        description="List of artifact IDs to add to the group",
        min_length=1,
        examples=[["artifact1", "artifact2"]],
    )
    position: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position to insert artifacts at (default: append)",
        examples=[0, 1, 2],
    )


class ArtifactPositionUpdate(BaseModel):
    """Schema for updating artifact position in bulk reorder operations."""

    artifact_id: str = Field(
        description="Artifact ID",
        examples=["artifact1"],
    )
    position: int = Field(
        ge=0,
        description="New position",
        examples=[0, 1, 2],
    )


class ReorderArtifactsRequest(BaseModel):
    """Request schema for bulk reordering artifacts within a group."""

    artifacts: List[ArtifactPositionUpdate] = Field(
        description="List of artifacts with their new positions",
        min_length=1,
    )


class GroupArtifactResponse(BaseModel):
    """Response schema for an artifact in a group."""

    artifact_id: str = Field(
        description="Artifact ID",
        examples=["artifact1"],
    )
    position: int = Field(
        description="Position in group",
        examples=[0, 1, 2],
    )
    added_at: datetime = Field(
        description="When artifact was added to group",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "artifact1",
                "position": 0,
                "added_at": "2024-11-16T12:00:00Z",
            }
        }


class GroupResponse(BaseModel):
    """Response schema for a single group."""

    id: str = Field(
        description="Group unique identifier",
        examples=["abc123"],
    )
    collection_id: str = Field(
        description="Collection this group belongs to",
        examples=["default"],
    )
    name: str = Field(
        description="Group name",
        examples=["Frontend Development"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Group description",
        examples=["Skills and tools for frontend development"],
    )
    position: int = Field(
        description="Display order in collection",
        examples=[0, 1, 2],
    )
    created_at: datetime = Field(
        description="Group creation timestamp",
    )
    updated_at: datetime = Field(
        description="Last update timestamp",
    )
    artifact_count: int = Field(
        description="Number of artifacts in this group",
        examples=[5, 10],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "abc123",
                "collection_id": "default",
                "name": "Frontend Development",
                "description": "Skills and tools for frontend development",
                "position": 0,
                "created_at": "2024-11-16T12:00:00Z",
                "updated_at": "2024-11-16T15:30:00Z",
                "artifact_count": 5,
            }
        }


class GroupWithArtifactsResponse(GroupResponse):
    """Response schema for a group with its artifacts list."""

    artifacts: List[GroupArtifactResponse] = Field(
        description="List of artifacts in this group (ordered by position)",
        default_factory=list,
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "abc123",
                "collection_id": "default",
                "name": "Frontend Development",
                "description": "Skills and tools for frontend development",
                "position": 0,
                "created_at": "2024-11-16T12:00:00Z",
                "updated_at": "2024-11-16T15:30:00Z",
                "artifact_count": 2,
                "artifacts": [
                    {
                        "artifact_id": "artifact1",
                        "position": 0,
                        "added_at": "2024-11-16T12:00:00Z",
                    },
                    {
                        "artifact_id": "artifact2",
                        "position": 1,
                        "added_at": "2024-11-16T13:00:00Z",
                    },
                ],
            }
        }


class CopyGroupRequest(BaseModel):
    """Request schema for copying a group to another collection.

    Creates a copy of the group (with name + " (Copy)") in the target collection,
    including all artifacts from the source group.
    """

    target_collection_id: str = Field(
        description="ID of the collection to copy the group to",
        examples=["target-collection-123"],
    )


class GroupListResponse(BaseModel):
    """Response schema for listing groups."""

    groups: List[GroupResponse] = Field(
        description="List of groups",
        default_factory=list,
    )
    total: int = Field(
        description="Total number of groups",
        examples=[5],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "groups": [
                    {
                        "id": "abc123",
                        "collection_id": "default",
                        "name": "Frontend Development",
                        "description": "Skills and tools for frontend development",
                        "position": 0,
                        "created_at": "2024-11-16T12:00:00Z",
                        "updated_at": "2024-11-16T15:30:00Z",
                        "artifact_count": 5,
                    }
                ],
                "total": 1,
            }
        }
