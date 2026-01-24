"""Settings API schemas for configuration management.

Provides Pydantic models for settings-related API endpoints,
including GitHub token management.
"""

from typing import Optional

from pydantic import BaseModel, Field


class GitHubTokenRequest(BaseModel):
    """Request to set GitHub Personal Access Token.

    The token must be a valid GitHub PAT starting with 'ghp_' (classic)
    or 'github_pat_' (fine-grained).
    """

    token: str = Field(
        ...,
        min_length=10,
        description="GitHub Personal Access Token (must start with 'ghp_' or 'github_pat_')",
        examples=["ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )


class GitHubTokenStatusResponse(BaseModel):
    """Response for GitHub token status check.

    Returns whether a token is configured and, if so, a masked version
    along with the associated GitHub username and rate limit information.
    """

    is_set: bool = Field(
        description="Whether a GitHub token is currently configured",
        examples=[True],
    )
    masked_token: Optional[str] = Field(
        default=None,
        description="Masked token showing first 7 characters (e.g., 'ghp_xxx...')",
        examples=["ghp_abc..."],
    )
    username: Optional[str] = Field(
        default=None,
        description="GitHub username associated with the token",
        examples=["octocat"],
    )
    rate_limit: Optional[int] = Field(
        default=None,
        description="Maximum requests per hour (5000 with token, 60 without)",
        examples=[5000],
    )
    rate_remaining: Optional[int] = Field(
        default=None,
        description="Remaining requests in current rate limit window",
        examples=[4999],
    )


class GitHubTokenValidationResponse(BaseModel):
    """Response for GitHub token validation.

    Returns validation results including rate limit information
    and token scopes without storing the token.
    """

    valid: bool = Field(
        description="Whether the token is valid and can authenticate with GitHub",
        examples=[True],
    )
    username: Optional[str] = Field(
        default=None,
        description="GitHub username associated with the token",
        examples=["octocat"],
    )
    scopes: Optional[list[str]] = Field(
        default=None,
        description="OAuth scopes granted to the token",
        examples=[["repo", "read:user"]],
    )
    rate_limit: Optional[int] = Field(
        default=None,
        description="Maximum requests per hour with this token",
        examples=[5000],
    )
    rate_remaining: Optional[int] = Field(
        default=None,
        description="Remaining requests in current rate limit window",
        examples=[4999],
    )


class IndexingModeResponse(BaseModel):
    """Response for indexing mode configuration.

    Returns the current global artifact search indexing mode.
    """

    indexing_mode: str = Field(
        description="Global indexing mode: 'off', 'on', or 'opt_in'",
        examples=["opt_in"],
    )


class MessageResponse(BaseModel):
    """Generic message response for simple operations.

    Used for operations that don't return specific data,
    such as successful deletion or updates.
    """

    message: str = Field(
        description="Human-readable message describing the operation result",
        examples=["GitHub token configured successfully"],
    )
