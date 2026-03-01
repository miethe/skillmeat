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

# Reserved slugs that map to the five built-in entity types.  Custom type
# creation must reject these to prevent shadowing built-in validation logic.
RESERVED_BUILTIN_SLUGS: frozenset[str] = frozenset(
    {"skill", "command", "agent", "mcp_server", "hook"}
)


def _validate_frontmatter_schema_value(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Validate that *value* is a valid JSON Schema subset dict.

    The accepted subset has two optional keys:
    - ``required``: list of strings (frontmatter keys that must be present).
    - ``properties``: dict mapping key names to type descriptors
      (each descriptor must be a dict, typically ``{"type": "<json-type>"}``).

    Any extra top-level keys are rejected to keep the schema surface minimal
    and prevent confusion with full JSON Schema usage.

    Args:
        value: The candidate schema dict, or ``None``.

    Returns:
        The validated dict unchanged, or ``None``.

    Raises:
        ValueError: If the dict structure is invalid.
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        raise ValueError("frontmatter_schema must be a dict or null")

    allowed_top_keys = {"required", "properties"}
    extra_keys = set(value.keys()) - allowed_top_keys
    if extra_keys:
        raise ValueError(
            f"frontmatter_schema contains unexpected keys: {sorted(extra_keys)}. "
            f"Only 'required' and 'properties' are supported."
        )

    # Validate 'required' field
    if "required" in value:
        required = value["required"]
        if not isinstance(required, list):
            raise ValueError("frontmatter_schema.required must be a list of strings")
        for i, item in enumerate(required):
            if not isinstance(item, str):
                raise ValueError(
                    f"frontmatter_schema.required[{i}] must be a string, got {type(item).__name__}"
                )

    # Validate 'properties' field
    if "properties" in value:
        props = value["properties"]
        if not isinstance(props, dict):
            raise ValueError("frontmatter_schema.properties must be a dict")
        for key, descriptor in props.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"frontmatter_schema.properties keys must be strings, got {type(key).__name__!r}"
                )
            if not isinstance(descriptor, dict):
                raise ValueError(
                    f"frontmatter_schema.properties[{key!r}] must be a dict "
                    f"(e.g. {{\"type\": \"string\"}}), got {type(descriptor).__name__}"
                )

    return value


class EntityTypeConfigCreateRequest(BaseModel):
    """Request schema for creating a new entity type configuration.

    Attributes:
        slug: Machine-readable unique identifier for the new type.
              Must match ``^[a-z][a-z0-9_]{0,63}$``.  Reserved built-in
              slugs (``skill``, ``command``, ``agent``, ``mcp_server``,
              ``hook``) are rejected with a validation error.
        label: Human-readable display name shown in the UI.
        description: Optional long-form description of this entity type.
        icon: Optional icon identifier for UI rendering.
        path_prefix: Default filesystem path prefix for this type.
        required_frontmatter_keys: Frontmatter keys that MUST be present.
        example_path: An example path illustrating this entity type.
        content_template: Default Markdown template for new entities.
        applicable_platforms: Optional list of platform slugs this type
            applies to.  ``None`` (the default) means all platforms.
        frontmatter_schema: Optional JSON Schema subset for validating
            custom type frontmatter.  Accepted keys: ``required`` (list of
            strings) and ``properties`` (dict of key → type descriptor).
    """

    slug: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    path_prefix: Optional[str] = None
    required_frontmatter_keys: Optional[List[str]] = None
    example_path: Optional[str] = None
    content_template: Optional[str] = None
    applicable_platforms: Optional[List[str]] = None
    frontmatter_schema: Optional[Dict[str, Any]] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """Ensure slug matches the allowed pattern and is not reserved."""
        if not _SLUG_RE.match(value):
            raise ValueError(
                "slug must start with a lowercase letter and contain only lowercase "
                "letters, digits, and underscores (max 64 characters total)"
            )
        if value in RESERVED_BUILTIN_SLUGS:
            raise ValueError(
                f"slug '{value}' is reserved for a built-in entity type and cannot "
                f"be used for custom types. Reserved slugs: "
                f"{sorted(RESERVED_BUILTIN_SLUGS)}"
            )
        return value

    @field_validator("frontmatter_schema")
    @classmethod
    def validate_frontmatter_schema(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validate frontmatter_schema is a well-formed JSON Schema subset."""
        return _validate_frontmatter_schema_value(value)


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
        content_template: Default Markdown template for new entities.
        applicable_platforms: Optional list of platform slugs this type
            applies to.  ``None`` leaves the existing value unchanged.
        frontmatter_schema: Optional JSON Schema subset for validating
            custom type frontmatter.  ``None`` leaves the existing value
            unchanged.
    """

    label: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    path_prefix: Optional[str] = None
    required_frontmatter_keys: Optional[List[str]] = None
    example_path: Optional[str] = None
    content_template: Optional[str] = None
    applicable_platforms: Optional[List[str]] = None
    frontmatter_schema: Optional[Dict[str, Any]] = None

    @field_validator("frontmatter_schema")
    @classmethod
    def validate_frontmatter_schema(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validate frontmatter_schema is a well-formed JSON Schema subset."""
        return _validate_frontmatter_schema_value(value)


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
        example_path: An example path illustrating this entity type.
        content_template: Default Markdown template used when creating a new
                          entity of this type.
        applicable_platforms: List of platform slugs this type applies to.
                              ``None`` means applicable to all platforms.
        frontmatter_schema: JSON Schema subset for custom type frontmatter
                            validation.  ``None`` means no structured
                            schema validation.
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
    example_path: Optional[str] = None
    content_template: Optional[str] = None
    applicable_platforms: Optional[List[str]] = None
    frontmatter_schema: Optional[Dict[str, Any]] = None
    is_builtin: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
