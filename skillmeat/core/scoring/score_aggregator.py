"""Score aggregation using weighted Bayesian averaging.

This module provides a Bayesian aggregation framework for combining scores from
multiple sources (user ratings, GitHub stars, registry data, etc.) into a single
quality score with confidence metrics.

The aggregator uses weighted Bayesian averaging to handle cold-start scenarios
(few ratings) and provides confidence scores based on data quality indicators.

Example:
    >>> from skillmeat.core.scoring.score_aggregator import ScoreAggregator, ScoreSource
    >>> from datetime import datetime, timezone
    >>>
    >>> aggregator = ScoreAggregator()
    >>> sources = [
    ...     ScoreSource("user_rating", 85.0, 0.4, datetime.now(timezone.utc), 10),
    ...     ScoreSource("github_stars", 70.0, 0.25, datetime.now(timezone.utc), 150),
    ... ]
    >>> result = aggregator.aggregate(sources)
    >>> print(f"Score: {result.final_score:.1f}, Confidence: {result.confidence:.2f}")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from skillmeat.core.scoring.score_decay import ScoreDecay

logger = logging.getLogger(__name__)

# Default source weights (must sum to 1.0 for normalized weighting)
DEFAULT_SOURCE_WEIGHTS = {
    "user_rating": 0.4,  # User's own rating (highest weight)
    "github_stars": 0.25,  # GitHub stars normalized
    "registry": 0.2,  # Community registry data
    "maintenance": 0.15,  # Maintenance signals
}


@dataclass
class ScoreSource:
    """A single score source with metadata.

    Attributes:
        source_name: Identifier for the source (e.g., "github_stars", "user_rating")
        score: Normalized score value (0-100)
        weight: Source weight for aggregation (0-1)
        last_updated: Timestamp when score was last updated
        sample_size: Number of underlying ratings/signals (None = 1)
    """

    source_name: str
    score: float  # 0-100
    weight: float  # 0-1
    last_updated: datetime
    sample_size: Optional[int] = None

    def __post_init__(self):
        """Validate score and weight ranges."""
        if not 0 <= self.score <= 100:
            raise ValueError(f"score must be 0-100, got {self.score}")
        if not 0 <= self.weight <= 1:
            raise ValueError(f"weight must be 0-1, got {self.weight}")
        if self.sample_size is not None and self.sample_size < 0:
            raise ValueError(f"sample_size must be >= 0, got {self.sample_size}")


@dataclass
class AggregatedScore:
    """Result of score aggregation.

    Attributes:
        final_score: Aggregated score (0-100)
        confidence: Confidence in the score (0-1)
        source_count: Number of sources used
        sources: Original source data
        computed_at: Timestamp when aggregation was computed
    """

    final_score: float  # 0-100
    confidence: float  # 0-1
    source_count: int
    sources: List[ScoreSource] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Validate aggregated score ranges."""
        if not 0 <= self.final_score <= 100:
            raise ValueError(f"final_score must be 0-100, got {self.final_score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")
        if self.source_count < 0:
            raise ValueError(f"source_count must be >= 0, got {self.source_count}")


class ScoreAggregator:
    """Aggregates scores from multiple sources using weighted Bayesian averaging.

    This aggregator combines scores from different sources (user ratings, GitHub stars,
    registry data, etc.) using a Bayesian approach that handles cold-start scenarios
    through configurable priors.

    The aggregation formula is:
        final_score = (prior_mean * prior_strength + sum(score_i * weight_i * n_i)) /
                      (prior_strength + sum(weight_i * n_i))

    Where:
        - prior_mean: Expected score for unknown artifacts (default: 50.0)
        - prior_strength: Strength of prior belief (default: 10, like 10 pseudo-ratings)
        - score_i: Score from source i
        - weight_i: Weight of source i
        - n_i: Sample size for source i (defaults to 1 if not specified)

    Attributes:
        prior_mean: Bayesian prior mean (0-100)
        prior_strength: Bayesian prior strength (pseudo-sample size)
    """

    # Default prior settings for cold-start
    DEFAULT_PRIOR_MEAN = 50.0  # Neutral score
    DEFAULT_PRIOR_STRENGTH = 10  # Equivalent to 10 pseudo-ratings

    def __init__(
        self,
        prior_mean: float = DEFAULT_PRIOR_MEAN,
        prior_strength: int = DEFAULT_PRIOR_STRENGTH,
    ):
        """Initialize aggregator with Bayesian prior settings.

        Args:
            prior_mean: Bayesian prior mean score (0-100, default: 50.0)
            prior_strength: Bayesian prior strength (default: 10)

        Raises:
            ValueError: If prior_mean not in [0, 100] or prior_strength <= 0

        Example:
            >>> # More conservative prior (favors prior longer)
            >>> aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=20)
            >>>
            >>> # More aggressive prior (favors data sooner)
            >>> aggregator = ScoreAggregator(prior_mean=50.0, prior_strength=5)
        """
        if not 0 <= prior_mean <= 100:
            raise ValueError(f"prior_mean must be 0-100, got {prior_mean}")
        if prior_strength <= 0:
            raise ValueError(f"prior_strength must be > 0, got {prior_strength}")

        self.prior_mean = prior_mean
        self.prior_strength = prior_strength

    def aggregate(self, sources: List[ScoreSource]) -> AggregatedScore:
        """Aggregate scores from multiple sources using weighted Bayesian averaging.

        Handles edge cases:
        - Empty sources: Returns prior mean with low confidence
        - Single source: Returns source score with moderate confidence
        - Multiple sources: Returns weighted average with high confidence

        Args:
            sources: List of ScoreSource objects to aggregate

        Returns:
            AggregatedScore with final score, confidence, and metadata

        Example:
            >>> aggregator = ScoreAggregator()
            >>> sources = [
            ...     ScoreSource("user_rating", 90.0, 0.4, datetime.now(timezone.utc), 5),
            ...     ScoreSource("github_stars", 75.0, 0.25, datetime.now(timezone.utc), 100),
            ... ]
            >>> result = aggregator.aggregate(sources)
            >>> assert 0 <= result.final_score <= 100
            >>> assert 0 <= result.confidence <= 1
        """
        # Handle empty sources: return prior
        if not sources:
            logger.debug("No sources provided, returning prior mean")
            return AggregatedScore(
                final_score=self.prior_mean,
                confidence=0.1,  # Low confidence with no data
                source_count=0,
                sources=[],
                computed_at=datetime.now(timezone.utc),
            )

        # Calculate weighted Bayesian average
        numerator = self.prior_mean * self.prior_strength
        denominator = self.prior_strength

        for source in sources:
            # Use sample_size if available, otherwise default to 1
            n = source.sample_size if source.sample_size is not None else 1

            # Weighted contribution: score * weight * sample_size
            numerator += source.score * source.weight * n
            denominator += source.weight * n

        final_score = numerator / denominator

        # Clamp to valid range (should not be needed, but safety check)
        final_score = min(100.0, max(0.0, final_score))

        # Compute confidence
        confidence = self.compute_confidence(sources)

        logger.debug(
            f"Aggregated {len(sources)} sources: "
            f"score={final_score:.1f}, confidence={confidence:.2f}"
        )

        return AggregatedScore(
            final_score=final_score,
            confidence=confidence,
            source_count=len(sources),
            sources=sources,
            computed_at=datetime.now(timezone.utc),
        )

    def compute_confidence(self, sources: List[ScoreSource]) -> float:
        """Compute confidence in the aggregated score (0-1).

        Confidence is based on four factors:
        1. Number of sources (more sources = higher confidence)
        2. Total sample size (more ratings = higher confidence)
        3. Source diversity (different source types = higher confidence)
        4. Recency of scores (newer scores = higher confidence)

        The confidence calculation uses a multiplicative model where each factor
        contributes to the overall confidence, but no single factor can push
        confidence to 1.0 without support from other factors.

        Args:
            sources: List of ScoreSource objects

        Returns:
            Confidence score between 0 and 1

        Example:
            >>> # High confidence: multiple sources, large sample, recent, diverse
            >>> sources = [
            ...     ScoreSource("user_rating", 90.0, 0.4, datetime.now(timezone.utc), 50),
            ...     ScoreSource("github_stars", 85.0, 0.25, datetime.now(timezone.utc), 200),
            ...     ScoreSource("registry", 80.0, 0.2, datetime.now(timezone.utc), 30),
            ... ]
            >>> confidence = aggregator.compute_confidence(sources)
            >>> assert confidence > 0.7  # High confidence
            >>>
            >>> # Low confidence: single source, small sample, old
            >>> old_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
            >>> sources = [ScoreSource("user_rating", 90.0, 0.4, old_date, 1)]
            >>> confidence = aggregator.compute_confidence(sources)
            >>> assert confidence < 0.5  # Low confidence
        """
        if not sources:
            return 0.1  # Very low confidence with no data

        # Factor 1: Source count (diminishing returns after 3 sources)
        # 1 source = 0.33, 2 sources = 0.67, 3+ sources = 1.0
        source_count_factor = min(1.0, len(sources) / 3.0)

        # Factor 2: Total sample size (diminishing returns after 100 samples)
        # Using log scale: 1 sample = 0.1, 10 samples = 0.5, 100+ samples = 1.0
        total_samples = sum(
            s.sample_size if s.sample_size is not None else 1 for s in sources
        )
        if total_samples <= 1:
            sample_size_factor = 0.1
        elif total_samples >= 100:
            sample_size_factor = 1.0
        else:
            # Log scale between 0.1 and 1.0
            import math

            sample_size_factor = 0.1 + (math.log10(total_samples) / 2.0) * 0.9

        # Factor 3: Source diversity (unique source types)
        # All same type = 0.5, 2 types = 0.75, 3+ types = 1.0
        unique_sources = len(set(s.source_name for s in sources))
        diversity_factor = min(1.0, 0.5 + (unique_sources - 1) * 0.25)

        # Factor 4: Recency (average age of scores)
        # < 1 month = 1.0, 3 months = 0.8, 6 months = 0.6, 1+ year = 0.4
        now = datetime.now(timezone.utc)
        avg_age_days = sum(
            (now - s.last_updated).total_seconds() / 86400 for s in sources
        ) / len(sources)

        if avg_age_days <= 30:  # < 1 month
            recency_factor = 1.0
        elif avg_age_days <= 90:  # 1-3 months
            recency_factor = 0.8
        elif avg_age_days <= 180:  # 3-6 months
            recency_factor = 0.6
        else:  # 6+ months
            recency_factor = 0.4

        # Combine factors using geometric mean (prevents any single factor from dominating)
        import math

        confidence = (
            source_count_factor * sample_size_factor * diversity_factor * recency_factor
        ) ** 0.25

        # Clamp to valid range
        confidence = min(1.0, max(0.0, confidence))

        logger.debug(
            f"Confidence factors: sources={source_count_factor:.2f}, "
            f"samples={sample_size_factor:.2f}, diversity={diversity_factor:.2f}, "
            f"recency={recency_factor:.2f} → confidence={confidence:.2f}"
        )

        return confidence

    def aggregate_with_decay(
        self,
        sources: List[ScoreSource],
        decay_calculator: Optional["ScoreDecay"] = None,
    ) -> AggregatedScore:
        """Aggregate scores with decay applied to older sources.

        This method applies time-based decay to community scores before aggregation,
        ensuring that stale data is appropriately downweighted. User ratings and
        maintenance signals are not decayed.

        Args:
            sources: List of ScoreSource objects to aggregate
            decay_calculator: Optional ScoreDecay instance (uses default if None)

        Returns:
            AggregatedScore with decay-adjusted scores

        Example:
            >>> from skillmeat.core.scoring.score_decay import ScoreDecay
            >>> aggregator = ScoreAggregator()
            >>> decay = ScoreDecay()
            >>> sources = [
            ...     ScoreSource("github_stars", 80.0, 0.25, old_date, 150),
            ...     ScoreSource("user_rating", 90.0, 0.4, datetime.now(timezone.utc), 5),
            ... ]
            >>> result = aggregator.aggregate_with_decay(sources, decay)
            >>> # github_stars will be decayed, user_rating unchanged
        """
        # Import here to avoid circular dependency
        from skillmeat.core.scoring.score_decay import (
            ScoreDecay,
            DECAYING_SOURCES,
        )

        # Use default decay calculator if not provided
        if decay_calculator is None:
            decay_calculator = ScoreDecay()

        # Apply decay to eligible sources
        processed_sources = []
        for source in sources:
            # Check if this source type should receive decay
            if source.source_name in DECAYING_SOURCES:
                # Apply decay to community scores
                decayed = decay_calculator.apply_decay(
                    source.score,
                    source.last_updated,
                )

                logger.debug(
                    f"Applied decay to {source.source_name}: "
                    f"{source.score:.1f} → {decayed.decayed_score:.1f} "
                    f"(factor={decayed.decay_factor:.3f})"
                )

                # Create new source with decayed score
                processed_sources.append(
                    ScoreSource(
                        source_name=source.source_name,
                        score=decayed.decayed_score,
                        weight=source.weight,
                        last_updated=source.last_updated,
                        sample_size=source.sample_size,
                    )
                )
            else:
                # No decay for user ratings or maintenance signals
                logger.debug(
                    f"Skipping decay for {source.source_name} "
                    f"(not in DECAYING_SOURCES)"
                )
                processed_sources.append(source)

        # Aggregate with processed (potentially decayed) scores
        return self.aggregate(processed_sources)
