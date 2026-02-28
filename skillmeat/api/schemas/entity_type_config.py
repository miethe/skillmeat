"""Pydantic schemas for EntityTypeConfig API responses.

EntityTypeConfig rows define the built-in (and future user-defined) context
entity types supported by SkillMeat.  The five built-in types ship with every
installation; custom types may be added by users.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


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
