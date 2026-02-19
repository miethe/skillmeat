"""Composite artifact API schemas for request and response models.

Provides Pydantic models for the composites CRUD endpoints.  Composite
artifacts group one or more child artifacts (skills, commands, agents, hooks,
MCP servers) into a single installable unit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------

COMPOSITE_TYPES = {"plugin", "stack", "suite"}
"""Valid values for the ``composite_type`` discriminator field."""


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CompositeCreateRequest(BaseModel):
    """Request schema for creating a new composite artifact.

    The ``composite_id`` must follow the ``type:name`` convention already used
    throughout the collection layer (e.g. ``"composite:my-plugin"``).
    """

    composite_id: str = Field(
        description=(
            "Primary key for the new composite in 'type:name' format "
            "(e.g. 'composite:my-plugin')."
        ),
        min_length=1,
        max_length=255,
        examples=["composite:my-plugin"],
    )
    collection_id: str = Field(
        description="ID of the owning collection.",
        examples=["default"],
    )
    composite_type: Literal["plugin", "stack", "suite"] = Field(
        default="plugin",
        description="Composite variant classifier.",
        examples=["plugin", "stack", "suite"],
    )
    display_name: Optional[str] = Field(
        default=None,
        description="Human-readable label shown in UI.",
        max_length=255,
        examples=["My Awesome Plugin"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Free-text description of the composite.",
        examples=["Bundles canvas design and code-review skills."],
    )
    initial_members: List[str] = Field(
        default_factory=list,
        description=(
            "Optional list of child artifact IDs in 'type:name' format to add "
            "immediately.  Each must already exist in the collection cache."
        ),
        examples=[["skill:canvas-design", "skill:code-review"]],
    )
    pinned_version_hash: Optional[str] = Field(
        default=None,
        description=(
            "Optional content hash applied to all initial members.  Pass "
            "null to track latest."
        ),
        examples=["abc123def456"],
    )

    @field_validator("composite_id")
    @classmethod
    def validate_composite_id_format(cls, v: str) -> str:
        """Ensure composite_id starts with 'composite:' prefix."""
        if not v.startswith("composite:"):
            raise ValueError(
                "composite_id must start with 'composite:' (e.g. 'composite:my-plugin')"
            )
        return v


class CompositeUpdateRequest(BaseModel):
    """Request schema for updating a composite artifact.

    All fields are optional — only provided fields are updated.
    """

    display_name: Optional[str] = Field(
        default=None,
        description="New human-readable label.",
        max_length=255,
        examples=["Updated Plugin Name"],
    )
    description: Optional[str] = Field(
        default=None,
        description="New description.",
        examples=["Updated description of this composite."],
    )
    composite_type: Optional[Literal["plugin", "stack", "suite"]] = Field(
        default=None,
        description="New composite variant classifier.",
        examples=["stack"],
    )


class MembershipCreateRequest(BaseModel):
    """Request schema for adding a child artifact to a composite."""

    artifact_id: str = Field(
        description=(
            "Child artifact ID in 'type:name' format "
            "(e.g. 'skill:canvas-design').  Must exist in the collection cache."
        ),
        min_length=1,
        examples=["skill:canvas-design"],
    )
    relationship_type: str = Field(
        default="contains",
        description="Semantic edge label for the membership.",
        examples=["contains"],
    )
    pinned_version_hash: Optional[str] = Field(
        default=None,
        description="Optional content hash to pin this member to a specific version.",
        examples=["abc123def456"],
    )
    position: Optional[int] = Field(
        default=None,
        ge=0,
        description="Display order within the composite (0-based).  Null means unordered.",
        examples=[0, 1, 2],
    )


class MemberPositionUpdate(BaseModel):
    """A single artifact → position entry for bulk reorder requests."""

    artifact_id: str = Field(
        description="Child artifact ID in 'type:name' format.",
        examples=["skill:canvas-design"],
    )
    position: int = Field(
        ge=0,
        description="New 0-based position within the composite.",
        examples=[0, 1, 2],
    )


class MembershipReorderRequest(BaseModel):
    """Request schema for bulk reordering members within a composite."""

    members: List[MemberPositionUpdate] = Field(
        description="List of artifact_id → position mappings.",
        min_length=1,
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MembershipResponse(BaseModel):
    """Response schema for a single composite membership edge."""

    collection_id: str = Field(description="Owning collection ID.")
    composite_id: str = Field(description="Parent composite ID (type:name).")
    child_artifact_uuid: str = Field(
        description="Stable UUID (ADR-007) of the child artifact."
    )
    relationship_type: str = Field(description="Semantic edge label.")
    pinned_version_hash: Optional[str] = Field(
        default=None, description="Version pin hash, or null for 'track latest'."
    )
    position: Optional[int] = Field(
        default=None, description="Display order (0-based), or null if unordered."
    )
    created_at: datetime = Field(description="When this membership was created.")
    child_artifact: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Lightweight child artifact summary (id, uuid, name, type) when "
            "the artifact row is available in the cache."
        ),
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "collection_id": "default",
                "composite_id": "composite:my-plugin",
                "child_artifact_uuid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                "relationship_type": "contains",
                "pinned_version_hash": None,
                "position": 0,
                "created_at": "2026-02-19T12:00:00Z",
                "child_artifact": {
                    "id": "skill:canvas-design",
                    "uuid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                    "name": "canvas-design",
                    "type": "skill",
                },
            }
        }


class CompositeResponse(BaseModel):
    """Response schema for a single composite artifact."""

    id: str = Field(
        description="Composite ID in 'type:name' format.",
        examples=["composite:my-plugin"],
    )
    collection_id: str = Field(
        description="Owning collection ID.",
        examples=["default"],
    )
    composite_type: str = Field(
        description="Composite variant: plugin, stack, or suite.",
        examples=["plugin"],
    )
    display_name: Optional[str] = Field(
        default=None,
        description="Human-readable label.",
        examples=["My Awesome Plugin"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Free-text description.",
    )
    created_at: datetime = Field(description="Creation timestamp (UTC).")
    updated_at: datetime = Field(description="Last updated timestamp (UTC).")
    memberships: List[MembershipResponse] = Field(
        default_factory=list,
        description=(
            "List of child membership edges, ordered by position (nulls last)."
        ),
    )
    member_count: int = Field(
        description="Number of child members.",
        examples=[2],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "composite:my-plugin",
                "collection_id": "default",
                "composite_type": "plugin",
                "display_name": "My Awesome Plugin",
                "description": "Bundles canvas design and code-review skills.",
                "created_at": "2026-02-19T12:00:00Z",
                "updated_at": "2026-02-19T12:00:00Z",
                "memberships": [
                    {
                        "collection_id": "default",
                        "composite_id": "composite:my-plugin",
                        "child_artifact_uuid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                        "relationship_type": "contains",
                        "pinned_version_hash": None,
                        "position": 0,
                        "created_at": "2026-02-19T12:00:00Z",
                        "child_artifact": {
                            "id": "skill:canvas-design",
                            "uuid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                            "name": "canvas-design",
                            "type": "skill",
                        },
                    }
                ],
                "member_count": 1,
            }
        }


class CompositeListResponse(BaseModel):
    """Paginated response schema for listing composite artifacts."""

    items: List[CompositeResponse] = Field(
        description="Composite artifacts for this collection.",
    )
    total: int = Field(
        description="Total number of composites in the collection.",
        examples=[3],
    )
