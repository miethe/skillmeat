"""Settings API schemas for configuration management.

Provides Pydantic models for settings-related API endpoints,
including GitHub token management and similarity badge configuration.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


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


# ---------------------------------------------------------------------------
# Similarity settings schemas
# ---------------------------------------------------------------------------

_THRESHOLD_KEYS = frozenset({"high", "partial", "low", "floor"})
_COLOR_KEYS = frozenset({"high", "partial", "low"})


class SimilarityThresholdsResponse(BaseModel):
    """Current similarity score band thresholds.

    Each value is a float in [0.0, 1.0] representing the *minimum* cosine
    similarity score required to fall into that band.  The floor threshold
    acts as a lower cutoff — scores below it are not displayed.

    Ordering invariant: floor < low < partial < high.
    """

    high: float = Field(
        description="Minimum score for the 'high' similarity band",
        examples=[0.80],
    )
    partial: float = Field(
        description="Minimum score for the 'partial' similarity band",
        examples=[0.55],
    )
    low: float = Field(
        description="Minimum score for the 'low' similarity band",
        examples=[0.35],
    )
    floor: float = Field(
        description="Minimum score to display at all (results below this are hidden)",
        examples=[0.20],
    )


class SimilarityThresholdsUpdateRequest(BaseModel):
    """Partial update for similarity score thresholds.

    Only the supplied keys are updated; omitted keys retain their current values.
    All supplied values must be floats in [0.0, 1.0] and the resulting
    merged thresholds must satisfy: floor < low < partial < high.
    """

    high: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum score for the 'high' similarity band",
        examples=[0.80],
    )
    partial: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum score for the 'partial' similarity band",
        examples=[0.55],
    )
    low: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum score for the 'low' similarity band",
        examples=[0.35],
    )
    floor: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum score to display at all",
        examples=[0.20],
    )


class SimilarityColorsResponse(BaseModel):
    """Current similarity band color configuration.

    Each value is a CSS hex color string (e.g. '#22c55e').
    """

    high: str = Field(
        description="CSS hex color for the 'high' similarity band",
        examples=["#22c55e"],
    )
    partial: str = Field(
        description="CSS hex color for the 'partial' similarity band",
        examples=["#eab308"],
    )
    low: str = Field(
        description="CSS hex color for the 'low' similarity band",
        examples=["#f97316"],
    )


class SimilarityColorsUpdateRequest(BaseModel):
    """Partial update for similarity band colors.

    Only the supplied keys are updated; omitted keys retain their current values.
    All supplied values must be valid CSS hex color strings.
    """

    high: Optional[str] = Field(
        default=None,
        description="CSS hex color for the 'high' band (e.g. '#22c55e')",
        examples=["#22c55e"],
    )
    partial: Optional[str] = Field(
        default=None,
        description="CSS hex color for the 'partial' band (e.g. '#eab308')",
        examples=["#eab308"],
    )
    low: Optional[str] = Field(
        default=None,
        description="CSS hex color for the 'low' band (e.g. '#f97316')",
        examples=["#f97316"],
    )

    @field_validator("high", "partial", "low", mode="before")
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate that color values are CSS hex strings."""
        import re

        if v is None:
            return v
        if not re.match(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$", v):
            raise ValueError(
                f"Color must be a CSS hex string (e.g. '#22c55e'), got {v!r}"
            )
        return v


class SimilaritySettingsResponse(BaseModel):
    """Combined similarity settings: thresholds and colors."""

    thresholds: SimilarityThresholdsResponse = Field(
        description="Score band threshold configuration"
    )
    colors: SimilarityColorsResponse = Field(
        description="Score band color configuration"
    )
