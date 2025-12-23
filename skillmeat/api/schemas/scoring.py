"""API schemas for artifact scoring and rating endpoints.

Pydantic models for request/response serialization of scoring operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ArtifactScoreResponse(BaseModel):
    """Response schema for artifact scoring information.

    Provides complete scoring breakdown including individual factors
    and composite confidence score.
    """

    artifact_id: str = Field(
        description="Artifact composite key (type:name)",
        examples=["skill:pdf-processor"],
    )
    trust_score: float = Field(
        description="Source trust/reputation score (0-100)",
        ge=0,
        le=100,
        examples=[85.0],
    )
    quality_score: float = Field(
        description="Aggregated quality score from community ratings (0-100)",
        ge=0,
        le=100,
        examples=[92.5],
    )
    match_score: Optional[float] = Field(
        default=None,
        description="Query-specific relevance score (0-100), None if not query-dependent",
        ge=0,
        le=100,
        examples=[78.3],
    )
    confidence: float = Field(
        description="Composite confidence score (weighted combination of factors)",
        ge=0,
        le=100,
        examples=[84.2],
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Scoring schema version",
    )
    last_updated: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last score calculation",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "trust_score": 85.0,
                "quality_score": 92.5,
                "match_score": 78.3,
                "confidence": 84.2,
                "schema_version": "1.0.0",
                "last_updated": "2025-12-22T10:30:00Z",
            }
        }


class UserRatingRequest(BaseModel):
    """Request schema for submitting artifact rating.

    Allows users to rate artifacts and optionally provide feedback.
    """

    rating: int = Field(
        description="Numeric rating from 1 (poor) to 5 (excellent)",
        ge=1,
        le=5,
        examples=[4],
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Optional text feedback from user",
        max_length=1000,
        examples=["Great skill, very useful for my workflow!"],
    )
    share_with_community: bool = Field(
        default=False,
        description="Whether to share rating with community (opt-in)",
    )

    @field_validator("rating")
    @classmethod
    def validate_rating_range(cls, v: int) -> int:
        """Ensure rating is within valid range."""
        if not 1 <= v <= 5:
            raise ValueError("rating must be between 1 and 5")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "rating": 4,
                "feedback": "Very helpful for PDF processing tasks",
                "share_with_community": True,
            }
        }


class UserRatingResponse(BaseModel):
    """Response schema for rating submission confirmation.

    Confirms successful rating submission and provides server-assigned metadata.
    """

    id: int = Field(
        description="Database-assigned rating ID",
        examples=[123],
    )
    artifact_id: str = Field(
        description="Artifact that was rated (type:name)",
        examples=["skill:pdf-processor"],
    )
    rating: int = Field(
        description="Submitted rating value (1-5)",
        ge=1,
        le=5,
        examples=[4],
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Submitted feedback text",
    )
    share_with_community: bool = Field(
        description="Whether rating is shared with community",
    )
    rated_at: datetime = Field(
        description="Timestamp when rating was recorded",
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Schema version for future migrations",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": 123,
                "artifact_id": "skill:pdf-processor",
                "rating": 4,
                "feedback": "Very helpful for PDF processing tasks",
                "share_with_community": True,
                "rated_at": "2025-12-22T10:35:00Z",
                "schema_version": "1.0.0",
            }
        }


class CommunityScoreResponse(BaseModel):
    """Response schema for community score information.

    Provides aggregated community scoring from external sources.
    """

    artifact_id: str = Field(
        description="Artifact composite key (type:name)",
        examples=["skill:pdf-processor"],
    )
    source: str = Field(
        description="Source of the score",
        examples=["github_stars", "registry", "user_export"],
    )
    score: float = Field(
        description="Normalized community score (0-100)",
        ge=0,
        le=100,
        examples=[87.5],
    )
    last_updated: datetime = Field(
        description="Timestamp when score was last refreshed",
    )
    imported_from: Optional[str] = Field(
        default=None,
        description="Identifier of import source (e.g., repo URL)",
        examples=["github.com/anthropics/skills"],
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Schema version for future migrations",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "source": "github_stars",
                "score": 87.5,
                "last_updated": "2025-12-22T09:00:00Z",
                "imported_from": "github.com/anthropics/skills/pdf",
                "schema_version": "1.0.0",
            }
        }
