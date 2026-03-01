"""Pydantic schemas for ContextEntityCategory API requests and responses.

ContextEntityCategory rows define named buckets for grouping context entity
artifacts.  Categories can optionally be scoped to a specific entity type
(e.g. "skill") or platform (e.g. "github-actions").
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


def _slugify(name: str) -> str:
    """Generate a URL-safe slug from a human-readable name.

    Args:
        name: Human-readable category name.

    Returns:
        Lowercase, hyphen-separated slug derived from *name*.
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class ContextEntityCategoryCreateRequest(BaseModel):
    """Request schema for creating a new entity category.

    Attributes:
        name: Human-readable label shown in the UI (required).
        slug: URL-safe machine identifier.  Auto-generated from *name* when
              omitted.  Must contain only lowercase letters, digits, and
              hyphens.
        description: Optional longer description of the category's purpose.
        color: Optional hex colour code for UI badge rendering (e.g.
               ``"#3B82F6"``).
        entity_type_slug: When set, restrict this category to artifacts of
                          this entity type slug (e.g. ``"skill"``).
        platform: When set, restrict this category to artifacts targeting this
                  platform (e.g. ``"github-actions"``).
        sort_order: Ascending display order in the UI.  Defaults to ``0``.
    """

    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    entity_type_slug: Optional[str] = None
    platform: Optional[str] = None
    sort_order: int = 0

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: Optional[str]) -> Optional[str]:
        """Ensure slug contains only lowercase letters, digits, and hyphens."""
        if value is None:
            return value
        if not re.match(r"^[a-z0-9][a-z0-9\-]{0,98}[a-z0-9]$|^[a-z0-9]$", value):
            raise ValueError(
                "slug must contain only lowercase letters, digits, and hyphens, "
                "and must start and end with a letter or digit"
            )
        return value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        """Ensure color is a valid 6-digit hex colour code."""
        if value is None:
            return value
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError(
                "color must be a 6-digit hex colour code, e.g. '#3B82F6'"
            )
        return value


class ContextEntityCategoryUpdateRequest(BaseModel):
    """Request schema for updating an existing entity category.

    All fields are optional; only supplied (non-``None``) fields are updated.

    Attributes:
        name: Human-readable label shown in the UI.
        slug: URL-safe machine identifier.  Must contain only lowercase
              letters, digits, and hyphens.
        description: Optional longer description.
        color: Optional hex colour code for UI badge rendering.
        entity_type_slug: When set, restrict this category to a specific
                          entity type slug.
        platform: When set, restrict this category to a specific platform.
        sort_order: Ascending display order in the UI.
    """

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    entity_type_slug: Optional[str] = None
    platform: Optional[str] = None
    sort_order: Optional[int] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: Optional[str]) -> Optional[str]:
        """Ensure slug contains only lowercase letters, digits, and hyphens."""
        if value is None:
            return value
        if not re.match(r"^[a-z0-9][a-z0-9\-]{0,98}[a-z0-9]$|^[a-z0-9]$", value):
            raise ValueError(
                "slug must contain only lowercase letters, digits, and hyphens, "
                "and must start and end with a letter or digit"
            )
        return value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        """Ensure color is a valid 6-digit hex colour code."""
        if value is None:
            return value
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError(
                "color must be a 6-digit hex colour code, e.g. '#3B82F6'"
            )
        return value


class ContextEntityCategoryResponse(BaseModel):
    """Response schema for a single entity category.

    Mirrors the ``ContextEntityCategory`` ORM model defined in
    ``skillmeat/cache/models.py``.

    Attributes:
        id: Auto-incrementing integer primary key.
        name: Human-readable label shown in the UI.
        slug: URL-safe machine identifier.
        description: Optional longer description of the category.
        color: Optional hex colour code for UI badge rendering.
        entity_type_slug: Optional entity type scope filter.
        platform: Optional platform scope filter.
        sort_order: Ascending display order in the UI.
        is_builtin: ``True`` for system-seeded categories.
        created_at: Row creation timestamp (UTC).
        updated_at: Row last-modified timestamp (UTC).
    """

    id: int
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    entity_type_slug: Optional[str] = None
    platform: Optional[str] = None
    sort_order: int
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
