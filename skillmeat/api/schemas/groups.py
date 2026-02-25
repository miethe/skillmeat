"""Groups API schemas for request and response models."""

from datetime import datetime
import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


GROUP_COLOR_OPTIONS = {"slate", "blue", "green", "amber", "rose"}
GROUP_TAG_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
GROUP_HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$")
GROUP_MAX_TAGS = 20


def _normalize_and_validate_tags(value: object) -> List[str]:
    """Normalize tags to a lowercase unique list with strict token validation."""
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValueError("tags must be a list of strings")

    normalized: List[str] = []
    seen = set()
    for raw in value:
        if not isinstance(raw, str):
            raise ValueError("tags must be a list of strings")
        tag = raw.strip().lower()
        if not tag:
            continue
        if tag in seen:
            continue
        if not GROUP_TAG_PATTERN.match(tag):
            raise ValueError(
                "invalid tag token: use 1-32 chars from [a-z0-9_-] only"
            )
        normalized.append(tag)
        seen.add(tag)

    if len(normalized) > GROUP_MAX_TAGS:
        raise ValueError(f"maximum {GROUP_MAX_TAGS} tags are allowed")

    return normalized


def _normalize_and_validate_choice(
    value: object,
    *,
    options: set[str],
    field_name: str,
) -> str:
    """Normalize a string enum-like field and validate against known options."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip().lower()
    if normalized not in options:
        allowed = ", ".join(sorted(options))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return normalized


def _normalize_and_validate_color(value: object) -> str:
    """Normalize and validate group color as token or HEX."""
    if not isinstance(value, str):
        raise ValueError("color must be a string")

    normalized = value.strip().lower()
    if normalized in GROUP_COLOR_OPTIONS:
        return normalized

    if GROUP_HEX_COLOR_PATTERN.match(normalized):
        hex_value = normalized[1:]
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        elif len(hex_value) == 8:
            hex_value = hex_value[:6]
        return f"#{hex_value}"

    allowed = ", ".join(sorted(GROUP_COLOR_OPTIONS))
    raise ValueError(
        f"color must be one of: {allowed}, or a HEX value like #22c55e"
    )


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
    tags: List[str] = Field(
        default_factory=list,
        description="Group-local tags used for categorization and filtering",
        examples=[["frontend", "critical"]],
    )
    color: str = Field(
        default="slate",
        description="Visual color token or custom HEX color for group card accents",
        examples=["slate", "blue", "#22c55e"],
    )
    icon: str = Field(
        default="layers",
        description="Icon token used for group display",
        examples=["layers", "folder", "tag"],
    )
    position: int = Field(
        default=0,
        ge=0,
        description="Display order within collection (0-based)",
        examples=[0, 1, 2],
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: object) -> List[str]:
        """Validate and normalize group tags."""
        return _normalize_and_validate_tags(value)

    @field_validator("color", mode="before")
    @classmethod
    def validate_color(cls, value: object) -> str:
        """Validate color token."""
        return _normalize_and_validate_color(value)

    @field_validator("icon", mode="before")
    @classmethod
    def validate_icon(cls, value: object) -> str:
        """Validate icon token is a non-empty string within the DB column limit."""
        if not isinstance(value, str):
            raise ValueError("icon must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("icon must not be empty")
        if len(stripped) > 32:
            raise ValueError("icon must be 32 characters or fewer")
        return stripped


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
    tags: Optional[List[str]] = Field(
        default=None,
        description="Updated group-local tags",
        examples=[["frontend", "critical"]],
    )
    color: Optional[str] = Field(
        default=None,
        description="Updated visual color token or custom HEX color",
        examples=["slate", "blue", "#22c55e"],
    )
    icon: Optional[str] = Field(
        default=None,
        description="Updated icon token",
        examples=["layers", "folder", "tag"],
    )
    position: Optional[int] = Field(
        default=None,
        ge=0,
        description="New position in collection",
        examples=[0, 1, 2],
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: object) -> Optional[List[str]]:
        """Validate and normalize tags when supplied."""
        if value is None:
            return None
        return _normalize_and_validate_tags(value)

    @field_validator("color", mode="before")
    @classmethod
    def validate_color(cls, value: object) -> Optional[str]:
        """Validate color token when supplied."""
        if value is None:
            return None
        return _normalize_and_validate_color(value)

    @field_validator("icon", mode="before")
    @classmethod
    def validate_icon(cls, value: object) -> Optional[str]:
        """Validate icon token is a non-empty string within the DB column limit."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("icon must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("icon must not be empty")
        if len(stripped) > 32:
            raise ValueError("icon must be 32 characters or fewer")
        return stripped


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

    artifact_uuid: str = Field(
        description="Artifact UUID (ADR-007 stable identity)",
        examples=["a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"],
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

    artifact_uuid: str = Field(
        description="Artifact UUID (ADR-007 stable identity)",
        examples=["a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"],
    )
    artifact_id: Optional[str] = Field(
        default=None,
        description=(
            "Resolved artifact ID (type:name format) for API lookups. "
            "Populated when the artifact exists in the local cache; "
            "None for orphaned UUIDs."
        ),
        examples=["skill:canvas-design"],
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
                "artifact_uuid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                "artifact_id": "skill:canvas-design",
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
    tags: List[str] = Field(
        default_factory=list,
        description="Group-local tags",
        examples=[["frontend", "critical"]],
    )
    color: str = Field(
        description="Visual color token or custom HEX color for group card accents",
        examples=["slate", "blue", "#22c55e"],
    )
    icon: str = Field(
        description="Icon token for group display",
        examples=["layers", "folder"],
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
                "tags": ["frontend", "critical"],
                "color": "blue",
                "icon": "layers",
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
                "tags": ["frontend", "critical"],
                "color": "blue",
                "icon": "layers",
                "position": 0,
                "created_at": "2024-11-16T12:00:00Z",
                "updated_at": "2024-11-16T15:30:00Z",
                "artifact_count": 2,
                "artifacts": [
                    {
                        "artifact_uuid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                        "position": 0,
                        "added_at": "2024-11-16T12:00:00Z",
                    },
                    {
                        "artifact_uuid": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
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
                        "tags": ["frontend", "critical"],
                        "color": "blue",
                        "icon": "layers",
                        "position": 0,
                        "created_at": "2024-11-16T12:00:00Z",
                        "updated_at": "2024-11-16T15:30:00Z",
                        "artifact_count": 5,
                    }
                ],
                "total": 1,
            }
        }
