"""User Collections API schemas for request and response models.

Database-backed user collections (distinct from file-based collections).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .common import PageInfo, PaginatedResponse


class UserCollectionCreateRequest(BaseModel):
    """Request schema for creating a new user collection."""

    name: str = Field(
        description="Collection name (must be unique)",
        min_length=1,
        max_length=255,
        examples=["My Favorite Skills"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional collection description",
        examples=["Collection of my most-used skills"],
    )


class UserCollectionUpdateRequest(BaseModel):
    """Request schema for updating user collection metadata.

    Supports partial updates - only provided fields will be modified.
    """

    name: Optional[str] = Field(
        default=None,
        description="New collection name",
        min_length=1,
        max_length=255,
        examples=["Renamed Collection"],
    )
    description: Optional[str] = Field(
        default=None,
        description="New collection description",
        examples=["Updated description"],
    )


class AddArtifactsRequest(BaseModel):
    """Request schema for adding artifacts to a collection."""

    artifact_ids: List[str] = Field(
        description="List of artifact IDs to add to collection",
        min_length=1,
        examples=[["artifact-1", "artifact-2"]],
    )


class GroupSummary(BaseModel):
    """Summary of a group within a collection.

    Lightweight group representation for collection listings.
    """

    id: str = Field(
        description="Group unique identifier",
        examples=["abc123"],
    )
    name: str = Field(
        description="Group name",
        examples=["Data Science Tools"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Group description",
        examples=["Tools for data analysis"],
    )
    position: int = Field(
        description="Display order within collection",
        examples=[0],
    )
    artifact_count: int = Field(
        description="Number of artifacts in group",
        examples=[5],
    )

    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class UserCollectionResponse(BaseModel):
    """Response schema for a single user collection.

    Provides complete collection metadata including counts.
    """

    id: str = Field(
        description="Collection unique identifier",
        examples=["abc123def456"],
    )
    name: str = Field(
        description="Collection name",
        examples=["My Favorite Skills"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Collection description",
        examples=["Collection of my most-used skills"],
    )
    created_by: Optional[str] = Field(
        default=None,
        description="User identifier (for future multi-user support)",
        examples=["user@example.com"],
    )
    created_at: datetime = Field(
        description="Collection creation timestamp",
    )
    updated_at: datetime = Field(
        description="Last update timestamp",
    )
    group_count: int = Field(
        description="Number of groups in collection",
        examples=[3],
    )
    artifact_count: int = Field(
        description="Total number of artifacts in collection",
        examples=[15],
    )

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc123def456",
                "name": "My Favorite Skills",
                "description": "Collection of my most-used skills",
                "created_by": None,
                "created_at": "2024-11-16T12:00:00Z",
                "updated_at": "2024-11-16T15:30:00Z",
                "group_count": 3,
                "artifact_count": 15,
            }
        }


class UserCollectionWithGroupsResponse(UserCollectionResponse):
    """Response schema for a collection with nested groups.

    Extends UserCollectionResponse with full group details.
    """

    groups: List[GroupSummary] = Field(
        description="List of groups in this collection",
        default=[],
    )


class UserCollectionListResponse(PaginatedResponse[UserCollectionResponse]):
    """Paginated response for user collection listings.

    Extends the generic paginated response with collection-specific items.
    """

    pass


class ArtifactSummary(BaseModel):
    """Lightweight artifact summary for collection listings."""

    name: str = Field(description="Artifact name")
    type: str = Field(description="Artifact type (skill, command, agent, etc.)")
    version: Optional[str] = Field(default=None, description="Current version")
    source: str = Field(description="Source specification")

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class CollectionArtifactsResponse(PaginatedResponse[ArtifactSummary]):
    """Paginated response for collection artifacts."""

    pass
