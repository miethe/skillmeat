"""Core dataclasses for artifact scoring and rating system.

This module provides the domain models for SkillMeat's confidence scoring system,
which combines trust scores (source reputation), quality scores (community ratings),
and match scores (query relevance) into a composite confidence metric.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class ArtifactScore:
    """Composite scoring for an artifact combining multiple confidence factors.

    The confidence score is calculated as:
        confidence = (trust_score * 0.25) + (quality_score * 0.25) + (match_score * 0.50)

    Attributes:
        artifact_id: Unique identifier for the artifact (format: type:name)
        trust_score: Source trust/reputation score (0-100), from source configuration
        quality_score: Aggregated quality score (0-100), from community ratings
        match_score: Query-specific relevance score (0-100), None if not query-dependent
        confidence: Composite confidence score weighted by factors
        schema_version: Version of scoring schema for future migrations
        last_updated: Timestamp of last score calculation
    """

    artifact_id: str
    trust_score: float  # 0-100, from source config
    quality_score: float  # 0-100, aggregated from ratings
    match_score: float | None  # 0-100, query-dependent (None if not applicable)
    confidence: float  # Composite: (trust*0.25 + quality*0.25 + match*0.50)
    schema_version: str = "1.0.0"
    last_updated: datetime | None = None

    def __post_init__(self):
        """Validate score ranges and calculate confidence if not provided."""
        # Validate score ranges
        if not 0 <= self.trust_score <= 100:
            raise ValueError(f"trust_score must be 0-100, got {self.trust_score}")
        if not 0 <= self.quality_score <= 100:
            raise ValueError(f"quality_score must be 0-100, got {self.quality_score}")
        if self.match_score is not None and not 0 <= self.match_score <= 100:
            raise ValueError(
                f"match_score must be 0-100 or None, got {self.match_score}"
            )

        # Calculate composite confidence
        # If match_score is None, redistribute weight to trust and quality
        if self.match_score is None:
            # No match score: 50/50 between trust and quality
            self.confidence = (self.trust_score * 0.5) + (self.quality_score * 0.5)
        else:
            # Full weighting: trust 25%, quality 25%, match 50%
            self.confidence = (
                (self.trust_score * 0.25)
                + (self.quality_score * 0.25)
                + (self.match_score * 0.50)
            )


@dataclass
class UserRating:
    """User-submitted rating for an artifact.

    Captures individual user feedback including numeric rating,
    optional text feedback, and opt-in community sharing.

    Attributes:
        id: Database primary key (None for new ratings)
        artifact_id: Artifact being rated (format: type:name)
        rating: Numeric rating from 1 (poor) to 5 (excellent)
        feedback: Optional text feedback from user
        share_with_community: Whether user consents to sharing rating publicly
        rated_at: Timestamp when rating was submitted
    """

    id: int | None
    artifact_id: str
    rating: int  # 1-5
    feedback: str | None
    share_with_community: bool = False
    rated_at: datetime | None = None

    def __post_init__(self):
        """Validate rating is within valid range."""
        if not 1 <= self.rating <= 5:
            raise ValueError(f"rating must be 1-5, got {self.rating}")


@dataclass
class CommunityScore:
    """Aggregated community score from external sources.

    Represents quality signals imported from various community sources
    such as GitHub stars, official registries, or user-exported ratings.

    Attributes:
        artifact_id: Artifact being scored (format: type:name)
        source: Source of the score (e.g., "github_stars", "registry", "user_export")
        score: Normalized score value (0-100)
        last_updated: Timestamp when score was last refreshed
        imported_from: Optional identifier of the import source
    """

    artifact_id: str
    source: str  # "github_stars", "registry", "user_export"
    score: float  # 0-100
    last_updated: datetime
    imported_from: str | None = None

    def __post_init__(self):
        """Validate score range."""
        if not 0 <= self.score <= 100:
            raise ValueError(f"score must be 0-100, got {self.score}")


@dataclass
class ScoringResult:
    """Result of a scoring operation with metadata and degradation info.

    This class captures not just the scores, but also metadata about how
    those scores were computed, enabling clients to understand when
    degradation occurred and adjust UI accordingly.

    Attributes:
        scores: List of artifact scores ordered by relevance
        used_semantic: Whether semantic scoring was used (True) or degraded to keyword-only (False)
        degraded: Whether any fallback/degradation occurred during scoring
        degradation_reason: Human-readable explanation of why degradation occurred (if any)
        duration_ms: Total time taken for scoring operation in milliseconds
        query: Original search query that was scored

    Example:
        >>> result = await scoring_service.score_artifacts("pdf tool", artifacts)
        >>> if result.degraded:
        ...     print(f"Warning: {result.degradation_reason}")
        >>> print(f"Found {len(result.scores)} matches in {result.duration_ms:.1f}ms")
        >>> if result.used_semantic:
        ...     print("✓ Using semantic scoring")
        ... else:
        ...     print("⚠ Using keyword-only scoring")
    """

    scores: List[ArtifactScore]
    used_semantic: bool
    degraded: bool
    degradation_reason: str | None
    duration_ms: float
    query: str = ""

    def __post_init__(self):
        """Validate scoring result data."""
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms must be >= 0, got {self.duration_ms}")

        # If degraded=True, must have a reason
        if self.degraded and not self.degradation_reason:
            raise ValueError("degraded=True requires degradation_reason to be set")
