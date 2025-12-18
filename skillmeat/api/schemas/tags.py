"""Tag API schemas for request and response models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import PageInfo


class TagBase(BaseModel):
    """Base schema for shared tag fields."""

    name: str = Field(
        description="Tag name",
        min_length=1,
        max_length=100,
        examples=["productivity"],
    )
    slug: str = Field(
        description="URL-friendly slug (kebab-case)",
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        examples=["productivity", "ai-tools"],
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex color code (e.g., #FF5733)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        examples=["#FF5733", "#3498DB"],
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug follows kebab-case pattern."""
        if not v.islower():
            raise ValueError("Slug must be lowercase")
        if "--" in v:
            raise ValueError("Slug cannot contain consecutive hyphens")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with hyphen")
        return v


class TagCreateRequest(TagBase):
    """Request schema for creating a tag.

    All fields from TagBase are required except color (optional).
    """

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "Productivity",
                "slug": "productivity",
                "color": "#FF5733",
            }
        }


class TagUpdateRequest(BaseModel):
    """Request schema for updating a tag.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = Field(
        default=None,
        description="Tag name",
        min_length=1,
        max_length=100,
        examples=["Productivity Tools"],
    )
    slug: Optional[str] = Field(
        default=None,
        description="URL-friendly slug (kebab-case)",
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        examples=["productivity-tools"],
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex color code (e.g., #FF5733)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        examples=["#3498DB"],
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """Validate slug follows kebab-case pattern if provided."""
        if v is None:
            return v
        if not v.islower():
            raise ValueError("Slug must be lowercase")
        if "--" in v:
            raise ValueError("Slug cannot contain consecutive hyphens")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with hyphen")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "Productivity Tools",
                "color": "#3498DB",
            }
        }


class TagResponse(BaseModel):
    """Response schema for a single tag.

    Provides complete tag information including metadata
    and optional artifact count for list views.
    """

    id: str = Field(
        description="Tag unique identifier",
        examples=["tag-123abc"],
    )
    name: str = Field(
        description="Tag name",
        examples=["Productivity"],
    )
    slug: str = Field(
        description="URL-friendly slug",
        examples=["productivity"],
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex color code",
        examples=["#FF5733"],
    )
    created_at: datetime = Field(
        description="Timestamp when tag was created",
    )
    updated_at: datetime = Field(
        description="Timestamp of last update",
    )
    artifact_count: Optional[int] = Field(
        default=None,
        description="Number of artifacts with this tag (included when fetching list)",
        ge=0,
        examples=[12],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "tag-123abc",
                "name": "Productivity",
                "slug": "productivity",
                "color": "#FF5733",
                "created_at": "2025-12-18T10:00:00Z",
                "updated_at": "2025-12-18T15:30:00Z",
                "artifact_count": 12,
            }
        },
    )


class TagListResponse(BaseModel):
    """Paginated response for tag listings."""

    items: List[TagResponse] = Field(
        description="List of tags for this page",
    )
    page_info: PageInfo = Field(
        description="Pagination metadata",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "tag-123abc",
                        "name": "Productivity",
                        "slug": "productivity",
                        "color": "#FF5733",
                        "created_at": "2025-12-18T10:00:00Z",
                        "updated_at": "2025-12-18T15:30:00Z",
                        "artifact_count": 12,
                    },
                    {
                        "id": "tag-456def",
                        "name": "AI Tools",
                        "slug": "ai-tools",
                        "color": "#3498DB",
                        "created_at": "2025-12-18T11:00:00Z",
                        "updated_at": "2025-12-18T11:00:00Z",
                        "artifact_count": 8,
                    },
                ],
                "page_info": {
                    "has_next_page": False,
                    "has_previous_page": False,
                    "start_cursor": "Y3Vyc29yOjA=",
                    "end_cursor": "Y3Vyc29yOjE=",
                    "total_count": 2,
                },
            }
        }


class ArtifactTagRequest(BaseModel):
    """Request schema for adding a tag to an artifact."""

    tag_id: str = Field(
        description="Tag identifier to add",
        examples=["tag-123abc"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "tag_id": "tag-123abc",
            }
        }
