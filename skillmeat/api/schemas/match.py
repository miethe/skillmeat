"""API schemas for artifact matching/search endpoints.

Pydantic models for request/response serialization of artifact matching operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of scoring components.

    Provides transparency into how the confidence score was calculated.
    """

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
    match_score: float = Field(
        description="Query-specific relevance score (0-100)",
        ge=0,
        le=100,
        examples=[78.3],
    )
    semantic_used: bool = Field(
        default=False,
        description="Whether semantic embeddings were used for matching",
    )
    context_boost_applied: bool = Field(
        default=False,
        description="Whether contextual boost was applied to score",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "trust_score": 85.0,
                "quality_score": 92.5,
                "match_score": 78.3,
                "semantic_used": True,
                "context_boost_applied": False,
            }
        }


class MatchedArtifact(BaseModel):
    """Single matched artifact with confidence score.

    Represents an artifact that matched the search query with its
    relevance score and optional breakdown.
    """

    artifact_id: str = Field(
        description="Artifact composite key (type:name)",
        examples=["skill:pdf-processor"],
    )
    name: str = Field(
        description="Artifact name",
        examples=["pdf-processor"],
    )
    artifact_type: str = Field(
        description="Type of artifact (skill, command, agent, etc.)",
        examples=["skill"],
    )
    confidence: float = Field(
        description="Composite confidence score (0-100)",
        ge=0,
        le=100,
        examples=[84.2],
    )
    title: Optional[str] = Field(
        default=None,
        description="Human-readable title from artifact metadata",
        examples=["PDF Processing Tool"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Brief description from artifact metadata",
        examples=["Extract and manipulate PDF documents"],
    )
    breakdown: Optional[ScoreBreakdown] = Field(
        default=None,
        description="Detailed score breakdown (only if requested)",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "artifact_id": "skill:pdf-processor",
                "name": "pdf-processor",
                "artifact_type": "skill",
                "confidence": 84.2,
                "title": "PDF Processing Tool",
                "description": "Extract and manipulate PDF documents",
                "breakdown": {
                    "trust_score": 85.0,
                    "quality_score": 92.5,
                    "match_score": 78.3,
                    "semantic_used": True,
                    "context_boost_applied": False,
                },
            }
        }


class MatchResponse(BaseModel):
    """Response schema for artifact matching endpoint.

    Returns list of artifacts matching the query, sorted by confidence score.
    """

    query: str = Field(
        description="Original search query",
        examples=["pdf tool"],
    )
    matches: List[MatchedArtifact] = Field(
        description="Matched artifacts ordered by confidence (descending)",
    )
    total: int = Field(
        description="Total number of matches before limit applied",
        ge=0,
        examples=[47],
    )
    limit: int = Field(
        description="Maximum results requested",
        ge=1,
        le=100,
        examples=[10],
    )
    min_confidence: float = Field(
        description="Minimum confidence threshold applied",
        ge=0,
        le=100,
        examples=[0.0],
    )
    schema_version: str = Field(
        default="1.0.0",
        description="Schema version for future migrations",
    )
    scored_at: datetime = Field(
        description="Timestamp when scoring was performed",
    )
    degraded: bool = Field(
        default=False,
        description="Whether semantic scoring was unavailable (degraded to keyword-only)",
    )
    degradation_reason: Optional[str] = Field(
        default=None,
        description="Reason for degradation (if degraded=true)",
        examples=["Embedding service unavailable", "Semantic scoring timeout"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "query": "pdf tool",
                "matches": [
                    {
                        "artifact_id": "skill:pdf-processor",
                        "name": "pdf-processor",
                        "artifact_type": "skill",
                        "confidence": 84.2,
                        "title": "PDF Processing Tool",
                        "description": "Extract and manipulate PDF documents",
                    }
                ],
                "total": 47,
                "limit": 10,
                "min_confidence": 0.0,
                "schema_version": "1.0.0",
                "scored_at": "2025-12-22T10:30:00Z",
                "degraded": False,
                "degradation_reason": None,
            }
        }
