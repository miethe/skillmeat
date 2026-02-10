"""User Collections API schemas for request and response models.

Database-backed user collections (distinct from file-based collections).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .artifacts import ArtifactCollectionInfo
from .common import PageInfo, PaginatedResponse
from .deployments import DeploymentInfo, DeploymentSummary


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
    collection_type: Optional[str] = Field(
        default=None,
        description="Collection type (e.g., 'context', 'artifacts')",
        examples=["context"],
    )
    context_category: Optional[str] = Field(
        default=None,
        description="Category for context collections (e.g., 'rules', 'specs', 'context')",
        examples=["rules"],
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
    collection_type: Optional[str] = Field(
        default=None,
        description="Collection type",
        examples=["context"],
    )
    context_category: Optional[str] = Field(
        default=None,
        description="Context category",
        examples=["rules"],
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
    collection_type: Optional[str] = Field(
        default=None,
        description="Collection type",
        examples=["context"],
    )
    context_category: Optional[str] = Field(
        default=None,
        description="Context category",
        examples=["rules"],
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


class ArtifactGroupMembership(BaseModel):
    """Group membership info for an artifact."""

    id: str = Field(description="Group unique identifier")
    name: str = Field(description="Group name")
    position: int = Field(description="Artifact position within the group")


class ArtifactSummary(BaseModel):
    """Lightweight artifact summary for collection listings.

    When include_groups=true query parameter is used, the groups field
    will be populated with group membership information.

    This schema includes metadata fields (description, author, tags, collections)
    to support the frontend entity-mapper which expects these fields for
    consistent Entity rendering including collection badges.
    """

    id: str = Field(description="Unique artifact identifier")
    name: str = Field(description="Artifact name")
    type: str = Field(description="Artifact type (skill, command, agent, etc.)")
    version: Optional[str] = Field(default=None, description="Current version")
    source: str = Field(description="Source specification")
    description: Optional[str] = Field(
        default=None,
        description="Artifact description from metadata",
    )
    author: Optional[str] = Field(
        default=None,
        description="Artifact author from metadata",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Artifact tags",
    )
    tools: Optional[List[str]] = Field(
        default=None,
        description="Claude Code tools used by this artifact",
    )
    origin: Optional[str] = Field(
        default=None,
        description="Origin of the artifact (e.g., 'marketplace', 'local')",
    )
    origin_source: Optional[str] = Field(
        default=None,
        description="Source identifier within the origin (e.g., marketplace source ID)",
    )
    collections: Optional[List[ArtifactCollectionInfo]] = Field(
        default=None,
        description="Collections this artifact belongs to (for collection badges)",
    )
    groups: Optional[List[ArtifactGroupMembership]] = Field(
        default=None,
        description="Groups this artifact belongs to (only populated when include_groups=true)",
    )
    deployments: Optional[List[DeploymentSummary]] = Field(
        default=None,
        description="Lightweight deployment summaries for this artifact",
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ArtifactSummaryWithGroups(ArtifactSummary):
    """Artifact summary with guaranteed group memberships.

    Deprecated: Use ArtifactSummary with groups field instead.
    Kept for backward compatibility.
    """

    groups: List[ArtifactGroupMembership] = Field(
        default=[],
        description="Groups this artifact belongs to within the collection",
    )


class CollectionArtifactsResponse(PaginatedResponse[ArtifactSummary]):
    """Paginated response for collection artifacts.

    When include_groups=true query parameter is used, each artifact's
    groups field will be populated with group membership information.
    """

    pass
