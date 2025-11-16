"""Collection API schemas for request and response models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .common import PageInfo, PaginatedResponse


class CollectionCreateRequest(BaseModel):
    """Request schema for creating a new collection.

    This schema is currently minimal as collections are auto-initialized.
    Future versions may support custom collection settings.
    """

    name: str = Field(
        description="Collection name (must be unique)",
        min_length=1,
        max_length=100,
        examples=["my-collection"],
    )


class CollectionUpdateRequest(BaseModel):
    """Request schema for updating collection metadata.

    Currently supports minimal updates. Future versions will add
    more configuration options.
    """

    name: Optional[str] = Field(
        default=None,
        description="New collection name",
        min_length=1,
        max_length=100,
        examples=["renamed-collection"],
    )


class ArtifactSummary(BaseModel):
    """Summary of an artifact within a collection.

    Lightweight artifact representation for collection listings.
    """

    name: str = Field(
        description="Artifact name",
        examples=["pdf-skill"],
    )
    type: str = Field(
        description="Artifact type (skill, command, agent)",
        examples=["skill"],
    )
    version: Optional[str] = Field(
        default=None,
        description="Current version",
        examples=["1.2.3"],
    )
    source: str = Field(
        description="Source specification",
        examples=["anthropics/skills/pdf"],
    )


class CollectionResponse(BaseModel):
    """Response schema for a single collection.

    Provides complete collection metadata including artifact count
    and timestamps.
    """

    id: str = Field(
        description="Collection unique identifier",
        examples=["default"],
    )
    name: str = Field(
        description="Collection name",
        examples=["default"],
    )
    version: str = Field(
        description="Collection format version",
        examples=["1.0.0"],
    )
    artifact_count: int = Field(
        description="Number of artifacts in collection",
        examples=[5],
    )
    created: datetime = Field(
        description="Collection creation timestamp",
    )
    updated: datetime = Field(
        description="Last update timestamp",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "default",
                "name": "default",
                "version": "1.0.0",
                "artifact_count": 5,
                "created": "2024-11-16T12:00:00Z",
                "updated": "2024-11-16T15:30:00Z",
            }
        }


class CollectionListResponse(PaginatedResponse[CollectionResponse]):
    """Paginated response for collection listings.

    Extends the generic paginated response with collection-specific items.
    """

    pass


class CollectionArtifactsResponse(PaginatedResponse[ArtifactSummary]):
    """Paginated response for artifacts within a collection.

    Returns lightweight artifact summaries for efficient collection browsing.
    """

    pass
