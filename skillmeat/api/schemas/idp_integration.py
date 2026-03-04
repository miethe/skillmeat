"""Pydantic schemas for IDP (Internal Developer Portal) integration endpoints.

Defines request and response models for Backstage/IDP scaffold generation and
deployment registration operations.
"""

import re
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ====================
# Shared Helpers
# ====================

_TARGET_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+:[a-zA-Z0-9_/-]+$")


# ====================
# Request Schemas
# ====================


class IDPScaffoldRequest(BaseModel):
    """Request to generate scaffold files for an IDP target.

    Renders a set of template files (e.g. CLAUDE.md, project config) for a
    given composite or skill target, with optional variable substitution.

    Examples:
        >>> request = IDPScaffoldRequest(
        ...     target_id="composite:fin-serv-compliance",
        ...     variables={"PROJECT_NAME": "customer-api"},
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "target_id": "composite:fin-serv-compliance",
                "variables": {
                    "PROJECT_NAME": "customer-api",
                    "AUTHOR": "Jane Doe",
                },
            }
        },
    )

    target_id: str = Field(
        description=(
            "Target artifact identifier in 'type:name' format "
            "(e.g. 'composite:fin-serv-compliance', 'skill:canvas')"
        ),
        examples=["composite:fin-serv-compliance", "skill:canvas"],
    )
    variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional key/value pairs substituted into rendered template files",
        examples=[{"PROJECT_NAME": "customer-api", "AUTHOR": "Jane Doe"}],
    )

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, v: str) -> str:
        """Validate target_id follows 'type:name' format.

        Args:
            v: Target ID value

        Returns:
            Validated target_id

        Raises:
            ValueError: If format is not 'type:name'
        """
        if not _TARGET_ID_PATTERN.match(v):
            raise ValueError(
                "target_id must be in 'type:name' format "
                "(e.g. 'composite:fin-serv-compliance'). "
                "Allowed characters: letters, digits, hyphens, underscores, "
                "and forward-slashes in the name segment."
            )
        return v


class IDPRegisterDeploymentRequest(BaseModel):
    """Request to register an IDP deployment for an artifact target.

    Records that a repository has deployed a given artifact target.  The
    operation is idempotent: re-submitting the same ``repo_url`` + ``target_id``
    pair updates the existing deployment record rather than creating a duplicate.

    Examples:
        >>> request = IDPRegisterDeploymentRequest(
        ...     repo_url="https://github.com/org/customer-api",
        ...     target_id="composite:fin-serv-compliance",
        ...     metadata={"team": "platform"},
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "repo_url": "https://github.com/org/customer-api",
                "target_id": "composite:fin-serv-compliance",
                "metadata": {"team": "platform", "environment": "production"},
            }
        },
    )

    repo_url: str = Field(
        description=(
            "HTTPS URL of the repository being registered "
            "(e.g. 'https://github.com/org/customer-api')"
        ),
        examples=["https://github.com/org/customer-api"],
    )
    target_id: str = Field(
        description=(
            "Target artifact identifier in 'type:name' format "
            "(e.g. 'composite:fin-serv-compliance')"
        ),
        examples=["composite:fin-serv-compliance"],
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional key/value metadata stored alongside the deployment record",
        examples=[{"team": "platform", "environment": "production"}],
    )

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, v: str) -> str:
        """Validate target_id follows 'type:name' format.

        Args:
            v: Target ID value

        Returns:
            Validated target_id

        Raises:
            ValueError: If format is not 'type:name'
        """
        if not _TARGET_ID_PATTERN.match(v):
            raise ValueError(
                "target_id must be in 'type:name' format "
                "(e.g. 'composite:fin-serv-compliance'). "
                "Allowed characters: letters, digits, hyphens, underscores, "
                "and forward-slashes in the name segment."
            )
        return v

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Validate repo_url is an HTTPS URL.

        Args:
            v: Repository URL value

        Returns:
            Validated URL

        Raises:
            ValueError: If URL does not start with https://
        """
        if not v.startswith("https://"):
            raise ValueError(
                "repo_url must be an HTTPS URL (e.g. 'https://github.com/org/repo')"
            )
        return v


# ====================
# Response Schemas
# ====================


class RenderedFile(BaseModel):
    """A single rendered scaffold file.

    Represents a file generated from a template during IDP scaffold rendering.
    Content is base64-encoded to safely transport arbitrary text (including
    CLAUDE.md files that may contain non-ASCII characters).
    """

    path: str = Field(
        description=(
            "Relative path of the rendered file within the project "
            "(e.g. '.claude/CLAUDE.md')"
        ),
        examples=[".claude/CLAUDE.md", ".claude/rules/api-patterns.md"],
    )
    content_base64: str = Field(
        description="Base64-encoded UTF-8 file content",
        examples=["IyBDTEFVREUubWQKCk15IHByb2plY3QuCg=="],
    )


class IDPScaffoldResponse(BaseModel):
    """Response containing rendered scaffold files for an IDP target.

    Returns a list of files that should be written to the repository by the
    IDP scaffolder (e.g. a Backstage software template action).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": [
                    {
                        "path": ".claude/CLAUDE.md",
                        "content_base64": "IyBDTEFVREUubWQ=",
                    },
                    {
                        "path": ".claude/rules/compliance.md",
                        "content_base64": "IyBDb21wbGlhbmNlIFJ1bGVz",
                    },
                ]
            }
        }
    )

    files: List[RenderedFile] = Field(
        description=(
            "Rendered template files to be written to the target repository"
        ),
        examples=[
            [
                {
                    "path": ".claude/CLAUDE.md",
                    "content_base64": "IyBDTEFVREUubWQ=",
                }
            ]
        ],
    )


class IDPRegisterDeploymentResponse(BaseModel):
    """Response for a successful IDP deployment registration.

    Returns the UUID of the created or updated DeploymentSet together with an
    idempotency flag indicating whether the record was newly created.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "deployment_set_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "created": True,
            }
        }
    )

    deployment_set_id: str = Field(
        description="UUID of the DeploymentSet record created or updated by this request",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    created: bool = Field(
        description=(
            "True when a new DeploymentSet was created; "
            "False when an existing record was updated (idempotent re-registration)"
        ),
        examples=[True],
    )


# Export all schemas
__all__ = [
    "IDPScaffoldRequest",
    "IDPRegisterDeploymentRequest",
    "RenderedFile",
    "IDPScaffoldResponse",
    "IDPRegisterDeploymentResponse",
]
