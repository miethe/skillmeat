"""Project template API schemas for request and response models.

Project templates define collections of context entities that can be deployed
together to initialize Claude Code project structures. They support variable
substitution for customization and selective entity deployment.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .common import PaginatedResponse


class TemplateEntitySchema(BaseModel):
    """Entity information within a project template.

    Represents a context entity that is part of a template, including
    deployment order and path pattern information.
    """

    artifact_id: str = Field(
        description="Context entity artifact identifier",
        examples=["ctx_abc123def456"],
    )
    name: str = Field(
        description="Entity name",
        examples=["web-api-patterns"],
    )
    type: str = Field(
        description="Entity type (e.g., rule_file, context_file)",
        examples=["rule_file"],
    )
    deploy_order: int = Field(
        description="Deployment order (lower values deploy first)",
        examples=[1],
    )
    required: bool = Field(
        default=True,
        description="Whether entity is required for template deployment",
        examples=[True],
    )
    path_pattern: Optional[str] = Field(
        default=None,
        description="Path pattern within .claude/ directory",
        examples=[".claude/rules/web/api-client.md"],
    )


class ProjectTemplateBase(BaseModel):
    """Base schema for project template data.

    Contains common fields shared between create and response schemas.
    """

    name: str = Field(
        description="Template name (must be unique)",
        min_length=1,
        max_length=255,
        examples=["web-fullstack-starter"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Template description",
        examples=["Full-stack web application starter with API and frontend rules"],
    )


class ProjectTemplateCreateRequest(ProjectTemplateBase):
    """Request schema for creating a new project template.

    Templates can be created from a collection or by specifying individual
    entity IDs. They support variable substitution and selective deployment.

    Examples:
        >>> # Create template from specific entities
        >>> request = ProjectTemplateCreateRequest(
        ...     name="web-fullstack-starter",
        ...     description="Full-stack web application starter",
        ...     entity_ids=["ctx_abc123", "ctx_def456"],
        ... )
    """

    collection_id: Optional[str] = Field(
        default=None,
        description="Source collection ID (optional, for template from collection)",
        examples=["col_abc123def456"],
    )
    entity_ids: list[str] = Field(
        description="List of context entity IDs to include in template",
        min_length=1,
        max_length=50,
        examples=[["ctx_abc123def456", "ctx_def789ghi012"]],
    )
    default_project_config_id: Optional[str] = Field(
        default=None,
        description="Default project config entity ID (optional)",
        examples=["ctx_config123"],
    )

    @field_validator("entity_ids")
    @classmethod
    def validate_entity_ids(cls, v: list[str]) -> list[str]:
        """Validate entity IDs list.

        Args:
            v: List of entity IDs

        Returns:
            Validated list

        Raises:
            ValueError: If list is empty or has duplicates
        """
        if not v:
            raise ValueError("entity_ids must contain at least one entity")
        if len(v) != len(set(v)):
            raise ValueError("entity_ids must not contain duplicates")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "web-fullstack-starter",
                "description": "Full-stack web application starter",
                "entity_ids": ["ctx_abc123def456", "ctx_def789ghi012"],
                "collection_id": None,
                "default_project_config_id": None,
            }
        }


class ProjectTemplateUpdateRequest(BaseModel):
    """Request schema for updating a project template.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(
        default=None,
        description="Updated template name",
        min_length=1,
        max_length=255,
        examples=["web-fullstack-starter-v2"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated template description",
        examples=["Enhanced full-stack web application starter"],
    )
    entity_ids: Optional[list[str]] = Field(
        default=None,
        description="Updated list of context entity IDs",
        min_length=1,
        max_length=50,
        examples=[["ctx_abc123def456", "ctx_xyz789"]],
    )

    @field_validator("entity_ids")
    @classmethod
    def validate_entity_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate entity IDs list if provided.

        Args:
            v: List of entity IDs or None

        Returns:
            Validated list or None

        Raises:
            ValueError: If list is empty or has duplicates
        """
        if v is None:
            return None
        if not v:
            raise ValueError("entity_ids must contain at least one entity if provided")
        if len(v) != len(set(v)):
            raise ValueError("entity_ids must not contain duplicates")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "web-fullstack-starter-v2",
                "description": "Enhanced full-stack web application starter",
                "entity_ids": ["ctx_abc123def456", "ctx_xyz789"],
            }
        }


class ProjectTemplateResponse(BaseModel):
    """Response schema for a single project template.

    Provides complete template information including entity list,
    configuration, and metadata.
    """

    id: str = Field(
        description="Unique identifier for the template",
        examples=["tpl_abc123def456"],
    )
    name: str = Field(
        description="Template name",
        examples=["web-fullstack-starter"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Template description",
        examples=["Full-stack web application starter"],
    )
    collection_id: Optional[str] = Field(
        default=None,
        description="Source collection ID if template was created from collection",
        examples=["col_abc123def456"],
    )
    default_project_config_id: Optional[str] = Field(
        default=None,
        description="Default project config entity ID",
        examples=["ctx_config123"],
    )
    entities: list[TemplateEntitySchema] = Field(
        description="List of entities in the template",
        examples=[
            [
                {
                    "artifact_id": "ctx_abc123",
                    "name": "web-api-patterns",
                    "type": "rule_file",
                    "deploy_order": 1,
                    "required": True,
                    "path_pattern": ".claude/rules/web/api-client.md",
                }
            ]
        ],
    )
    entity_count: int = Field(
        description="Total number of entities in template",
        examples=[5],
    )
    created_at: datetime = Field(
        description="Timestamp when template was created",
    )
    updated_at: datetime = Field(
        description="Timestamp when template was last updated",
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True  # Enable ORM mode for SQLAlchemy models
        json_schema_extra = {
            "example": {
                "id": "tpl_abc123def456",
                "name": "web-fullstack-starter",
                "description": "Full-stack web application starter",
                "collection_id": None,
                "default_project_config_id": None,
                "entities": [
                    {
                        "artifact_id": "ctx_abc123",
                        "name": "web-api-patterns",
                        "type": "rule_file",
                        "deploy_order": 1,
                        "required": True,
                        "path_pattern": ".claude/rules/web/api-client.md",
                    }
                ],
                "entity_count": 1,
                "created_at": "2025-12-14T10:00:00Z",
                "updated_at": "2025-12-14T15:30:00Z",
            }
        }


class ProjectTemplateListResponse(PaginatedResponse[ProjectTemplateResponse]):
    """Paginated response for project template listings.

    Inherits pagination metadata from PaginatedResponse:
    - items: List of project templates
    - page_info: Cursor-based pagination information

    Example:
        >>> response = ProjectTemplateListResponse(
        ...     items=[template1, template2],
        ...     page_info=PageInfo(
        ...         has_next_page=True,
        ...         has_previous_page=False,
        ...         end_cursor="cursor123"
        ...     )
        ... )
    """

    pass


class TemplateVariableValue(BaseModel):
    """Variable values for template deployment.

    These variables are substituted into entity content during deployment,
    allowing customization of generated files.

    Common Variables:
        - PROJECT_NAME: Name of the project being initialized
        - PROJECT_DESCRIPTION: Brief project description
        - AUTHOR: Project author name
        - DATE: Current date (defaults to current date if not provided)
        - ARCHITECTURE_DESCRIPTION: Architecture overview
    """

    PROJECT_NAME: str = Field(
        description="Name of the project",
        min_length=1,
        examples=["my-awesome-project"],
    )
    PROJECT_DESCRIPTION: Optional[str] = Field(
        default=None,
        description="Brief description of the project",
        examples=["Full-stack web application for managing tasks"],
    )
    AUTHOR: Optional[str] = Field(
        default=None,
        description="Project author name",
        examples=["John Doe"],
    )
    DATE: Optional[str] = Field(
        default=None,
        description="Date string (defaults to current date if not provided)",
        examples=["2025-12-15"],
    )
    ARCHITECTURE_DESCRIPTION: Optional[str] = Field(
        default=None,
        description="High-level architecture description",
        examples=["Next.js frontend with FastAPI backend"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "PROJECT_NAME": "my-awesome-project",
                "PROJECT_DESCRIPTION": "Full-stack web application for managing tasks",
                "AUTHOR": "John Doe",
                "DATE": "2025-12-15",
                "ARCHITECTURE_DESCRIPTION": "Next.js frontend with FastAPI backend",
            }
        }


class DeployTemplateRequest(BaseModel):
    """Request schema for deploying a project template.

    Deploys template entities to a target project path with variable substitution.
    Supports selective entity deployment and overwrite control.
    """

    project_path: str = Field(
        description="Path to target project directory (must be valid filesystem path)",
        examples=["/path/to/project"],
    )
    variables: TemplateVariableValue = Field(
        description="Variable values for template substitution",
    )
    selected_entity_ids: Optional[list[str]] = Field(
        default=None,
        description="Subset of entity IDs to deploy (deploys all if not specified)",
        examples=[["ctx_abc123", "ctx_def456"]],
    )
    overwrite: bool = Field(
        default=False,
        description="Whether to overwrite existing files at target paths",
        examples=[False],
    )
    deployment_profile_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional deployment profile id to rewrite profile-rooted template paths "
            "(defaults to project primary profile)"
        ),
        examples=["codex"],
    )

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        """Validate project path format.

        Args:
            v: Project path value

        Returns:
            Validated path

        Raises:
            ValueError: If path is invalid
        """
        if not v or not v.strip():
            raise ValueError("project_path cannot be empty")
        if ".." in v:
            raise ValueError("project_path cannot contain '..' (path traversal)")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "project_path": "/path/to/project",
                "variables": {
                    "PROJECT_NAME": "my-awesome-project",
                    "PROJECT_DESCRIPTION": "Full-stack web application",
                    "AUTHOR": "John Doe",
                },
                "selected_entity_ids": None,
                "overwrite": False,
                "deployment_profile_id": "codex",
            }
        }


class DeployTemplateResponse(BaseModel):
    """Response schema for template deployment operation.

    Provides deployment results including deployed files, skipped files,
    and overall status.
    """

    success: bool = Field(
        description="Whether deployment completed successfully",
        examples=[True],
    )
    project_path: str = Field(
        description="Target project path where template was deployed",
        examples=["/path/to/project"],
    )
    deployed_files: list[str] = Field(
        description="List of files successfully deployed (relative paths)",
        examples=[[".claude/rules/web/api-client.md", ".claude/config.toml"]],
    )
    skipped_files: list[str] = Field(
        description="List of files skipped (already exist, overwrite=False)",
        examples=[[".claude/CLAUDE.md"]],
    )
    message: str = Field(
        description="Human-readable deployment status message",
        examples=["Successfully deployed 2 files, skipped 1 existing file"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "success": True,
                "project_path": "/path/to/project",
                "deployed_files": [
                    ".claude/rules/web/api-client.md",
                    ".claude/config.toml",
                ],
                "skipped_files": [".claude/CLAUDE.md"],
                "message": "Successfully deployed 2 files, skipped 1 existing file",
            }
        }


# Export all schemas
__all__ = [
    "TemplateEntitySchema",
    "ProjectTemplateBase",
    "ProjectTemplateCreateRequest",
    "ProjectTemplateUpdateRequest",
    "ProjectTemplateResponse",
    "ProjectTemplateListResponse",
    "TemplateVariableValue",
    "DeployTemplateRequest",
    "DeployTemplateResponse",
]
