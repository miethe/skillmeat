"""Pydantic schemas for EntityTypeConfig API requests and responses.

EntityTypeConfig rows define the built-in (and future user-defined) context
entity types supported by SkillMeat.  The five built-in types ship with every
installation; custom types may be added by users.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Slug pattern: lowercase letter, then up to 63 lowercase letters, digits, or underscores.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class EntityTypeConfigCreateRequest(BaseModel):
    """Request schema for creating a new entity type configuration.

    Attributes:
        slug: Machine-readable unique identifier for the new type.
              Must match ``^[a-z][a-z0-9_]{0,63}$``.
        label: Human-readable display name shown in the UI.
        description: Optional long-form description of this entity type.
        icon: Optional icon identifier for UI rendering.
        path_prefix: Default filesystem path prefix for this type.
        required_frontmatter_keys: Frontmatter keys that MUST be present.
        example_path: An example path illustrating this entity type.
    """

    slug: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    path_prefix: Optional[str] = None
    required_frontmatter_keys: Optional[List[str]] = None
    example_path: Optional[str] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """Ensure slug matches the allowed pattern."""
        if not _SLUG_RE.match(value):
            raise ValueError(
                "slug must start with a lowercase letter and contain only lowercase "
                "letters, digits, and underscores (max 64 characters total)"
            )
        return value


class EntityTypeConfigUpdateRequest(BaseModel):
    """Request schema for updating an existing entity type configuration.

    All fields are optional; only supplied fields are updated.

    Attributes:
        label: Human-readable display name shown in the UI.
        description: Optional long-form description of this entity type.
        icon: Optional icon identifier for UI rendering.
        path_prefix: Default filesystem path prefix for this type.
        required_frontmatter_keys: Frontmatter keys that MUST be present.
        example_path: An example path illustrating this entity type.
    """

    label: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    path_prefix: Optional[str] = None
    required_frontmatter_keys: Optional[List[str]] = None
    example_path: Optional[str] = None


class EntityTypeConfigResponse(BaseModel):
    """Response schema for a single entity type configuration.

    Mirrors the ``EntityTypeConfig`` ORM model defined in
    ``skillmeat/cache/models.py``.

    Attributes:
        id: Auto-incrementing integer primary key.
        slug: Machine-readable unique identifier (e.g. "skill", "command").
        display_name: Human-readable name shown in the UI.
        description: Optional long-form description of this entity type.
        icon: Optional icon identifier for UI rendering.
        path_prefix: Default filesystem path prefix for this type
                     (e.g. ".claude/skills").
        required_frontmatter_keys: JSON list of frontmatter keys that MUST be
                                   present in files of this type.
        optional_frontmatter_keys: JSON list of frontmatter keys that MAY be
                                   present.
        validation_rules: JSON object of additional validation configuration.
        content_template: Default Markdown template used when creating a new
                          entity of this type.
        is_builtin: ``True`` for the five shipped types; ``False`` for any
                    user-created types.
        sort_order: Display ordering in the UI (ascending).
        created_at: Row creation timestamp (UTC).
        updated_at: Row last-modified timestamp (UTC).
    """

    id: int
    slug: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    path_prefix: Optional[str] = None
    required_frontmatter_keys: Optional[List[str]] = None
    optional_frontmatter_keys: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    content_template: Optional[str] = None
    is_builtin: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
