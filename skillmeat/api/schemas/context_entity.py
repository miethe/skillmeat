"""Context entity API schemas for request and response models.

Context entities represent artifacts with special roles in Claude Code projects:
- PROJECT_CONFIG: Configuration files (e.g., .claude/config.toml)
- SPEC_FILE: Specification documents (e.g., .claude/specs/*.md)
- RULE_FILE: Path-scoped rules (e.g., .claude/rules/web/*.md)
- CONTEXT_FILE: Knowledge documents (e.g., .claude/context/*.md)
- PROGRESS_TEMPLATE: Progress tracking templates

These entities support path-pattern matching for auto-loading and categorization
for progressive disclosure patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import DEFAULT_PROFILE_ROOTS
from skillmeat.core.validators.context_path_validator import validate_context_path

from .common import PaginatedResponse


class ContextEntityType(str, Enum):
    """Type of context entity.

    Defines the role and purpose of the context entity within a project.
    Each type has specific conventions for path patterns and content structure.
    """

    PROJECT_CONFIG = "project_config"
    SPEC_FILE = "spec_file"
    RULE_FILE = "rule_file"
    CONTEXT_FILE = "context_file"
    PROGRESS_TEMPLATE = "progress_template"


class ContextEntityCreateRequest(BaseModel):
    """Request schema for creating a context entity.

    Context entities are artifacts with special roles in Claude Code projects.
    They support path-pattern matching for auto-loading and categorization.

    Path Pattern Security:
    - Must start with a profile root (e.g. '.claude/', '.codex/')
    - Cannot contain '..' for path traversal prevention

    Examples:
        >>> # Rule file that auto-loads for web path edits
        >>> request = ContextEntityCreateRequest(
        ...     name="web-hooks-rules",
        ...     entity_type=ContextEntityType.RULE_FILE,
        ...     content="# Web Hooks Patterns\\n...",
        ...     path_pattern=".claude/rules/web/hooks.md",
        ...     category="web",
        ...     auto_load=True
        ... )
    """

    name: str = Field(
        description="Human-readable name for the context entity",
        min_length=1,
        max_length=255,
        examples=["web-api-patterns"],
    )
    entity_type: ContextEntityType = Field(
        description="Type of context entity (determines role and conventions)",
        examples=[ContextEntityType.RULE_FILE],
    )
    content: str = Field(
        description="Markdown content of the context entity",
        examples=["# Web API Patterns\n\nFollow REST conventions..."],
    )
    path_pattern: str = Field(
        description="Path pattern within a profile root (must start with '.claude/'/'.codex/' etc, no '..')",
        examples=[".claude/rules/web/api-client.md"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional detailed description",
        examples=["API client conventions for web frontend"],
    )
    category: Optional[str] = Field(
        default=None,
        description="Category for progressive disclosure (e.g., 'api', 'frontend', 'debugging')",
        examples=["api"],
    )
    auto_load: bool = Field(
        default=False,
        description="Whether to auto-load when path pattern matches edited files",
        examples=[True],
    )
    version: Optional[str] = Field(
        default=None,
        description="Version identifier (semantic versioning recommended)",
        examples=["1.0.0"],
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description="Optional profile id used when validating/deploying this entity",
        examples=["claude_code"],
    )
    target_platforms: Optional[List[Platform]] = Field(
        default=None,
        description="Optional deployment platform restrictions (null means deployable on all platforms)",
    )

    @field_validator("path_pattern")
    @classmethod
    def validate_path_pattern(cls, v: str) -> str:
        """Validate path pattern for security and conventions.

        Args:
            v: Path pattern value to validate

        Returns:
            Validated path pattern

        Raises:
            ValueError: If path pattern is invalid
        """
        validate_context_path(
            v,
            allowed_prefixes=[f"{root.rstrip('/')}/" for root in DEFAULT_PROFILE_ROOTS],
        )
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "web-api-patterns",
                "entity_type": "rule_file",
                "content": "# Web API Patterns\n\nFollow REST conventions...",
                "path_pattern": ".claude/rules/web/api-client.md",
                "description": "API client conventions for web frontend",
                "category": "web",
                "auto_load": True,
                "version": "1.0.0",
                "deployment_profile_id": "claude_code",
                "target_platforms": ["claude_code", "codex"],
            }
        }


class ContextEntityUpdateRequest(BaseModel):
    """Request schema for updating a context entity.

    All fields are optional - only provided fields will be updated.
    Path pattern validation applies when provided.
    """

    name: Optional[str] = Field(
        default=None,
        description="Updated name",
        min_length=1,
        max_length=255,
        examples=["web-api-patterns-v2"],
    )
    entity_type: Optional[ContextEntityType] = Field(
        default=None,
        description="Updated entity type",
        examples=[ContextEntityType.RULE_FILE],
    )
    content: Optional[str] = Field(
        default=None,
        description="Updated markdown content",
        examples=["# Web API Patterns v2\n\nEnhanced REST conventions..."],
    )
    path_pattern: Optional[str] = Field(
        default=None,
        description="Updated path pattern (must start with profile root, no '..')",
        examples=[".claude/rules/web/api-client-v2.md"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated description",
        examples=["Enhanced API client conventions"],
    )
    category: Optional[str] = Field(
        default=None,
        description="Updated category",
        examples=["api"],
    )
    auto_load: Optional[bool] = Field(
        default=None,
        description="Updated auto-load setting",
        examples=[False],
    )
    version: Optional[str] = Field(
        default=None,
        description="Updated version",
        examples=["2.0.0"],
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description="Updated deployment profile id",
        examples=["codex"],
    )
    target_platforms: Optional[List[Platform]] = Field(
        default=None,
        description="Updated platform restrictions",
    )

    @field_validator("path_pattern")
    @classmethod
    def validate_path_pattern(cls, v: Optional[str]) -> Optional[str]:
        """Validate path pattern if provided.

        Args:
            v: Path pattern value to validate

        Returns:
            Validated path pattern or None

        Raises:
            ValueError: If path pattern is invalid
        """
        if v is None:
            return None
        validate_context_path(
            v,
            allowed_prefixes=[f"{root.rstrip('/')}/" for root in DEFAULT_PROFILE_ROOTS],
        )
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "content": "# Web API Patterns v2\n\nEnhanced REST conventions...",
                "description": "Enhanced API client conventions",
                "version": "2.0.0",
            }
        }


class ContextEntityResponse(BaseModel):
    """Response schema for a single context entity.

    Provides complete context entity information including metadata,
    path pattern, and auto-load settings.
    """

    id: str = Field(
        description="Unique identifier for the context entity",
        examples=["ctx_abc123def456"],
    )
    name: str = Field(
        description="Human-readable name",
        examples=["web-api-patterns"],
    )
    entity_type: ContextEntityType = Field(
        alias="type",  # Database model uses 'type' field
        description="Type of context entity",
        examples=[ContextEntityType.RULE_FILE],
    )
    path_pattern: str = Field(
        description="Path pattern within profile root directory",
        examples=[".claude/rules/web/api-client.md"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed description",
        examples=["API client conventions for web frontend"],
    )
    category: Optional[str] = Field(
        default=None,
        description="Category for progressive disclosure",
        examples=["api"],
    )
    auto_load: bool = Field(
        description="Whether to auto-load when path pattern matches",
        examples=[True],
    )
    version: Optional[str] = Field(
        default=None,
        description="Version identifier",
        examples=["1.0.0"],
    )
    target_platforms: Optional[List[Platform]] = Field(
        default=None,
        description="Platform restrictions for deployment (null means deployable anywhere)",
    )
    deployed_to: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Deployment paths grouped by profile/platform key",
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of content (for change detection)",
        examples=["abc123def456..."],
    )
    created_at: datetime = Field(
        description="Timestamp when entity was created",
    )
    updated_at: datetime = Field(
        description="Timestamp when entity was last updated",
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True  # Enable ORM mode for SQLAlchemy models
        populate_by_name = True  # Accept both field name and alias
        json_schema_extra = {
            "example": {
                "id": "ctx_abc123def456",
                "name": "web-api-patterns",
                "entity_type": "rule_file",
                "path_pattern": ".claude/rules/web/api-client.md",
                "description": "API client conventions for web frontend",
                "category": "api",
                "auto_load": True,
                "version": "1.0.0",
                "content_hash": "abc123def456789abcdef123456789abcdef123456789abcdef123456789ab",
                "created_at": "2025-12-14T10:00:00Z",
                "updated_at": "2025-12-14T15:30:00Z",
            }
        }


class ContextEntityListResponse(PaginatedResponse[ContextEntityResponse]):
    """Paginated response for context entity listings.

    Inherits pagination metadata from PaginatedResponse:
    - items: List of context entities
    - page_info: Cursor-based pagination information

    Example:
        >>> response = ContextEntityListResponse(
        ...     items=[entity1, entity2],
        ...     page_info=PageInfo(
        ...         has_next_page=True,
        ...         has_previous_page=False,
        ...         end_cursor="cursor123"
        ...     )
        ... )
    """

    pass
