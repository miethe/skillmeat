"""Quality scoring engine using Bayesian averaging.

Calculates quality scores for artifacts using Bayesian averaging to handle
cold-start problems (artifacts with few or no ratings).

Formula: (prior * prior_weight + actual_mean * count) / (prior_weight + count)

Where:
- prior: Default assumed quality (50/100)
- prior_weight: Number of "virtual" prior ratings (default: 5)
- actual_mean: Mean of real user ratings (scaled to 0-100)
- count: Number of real ratings
"""

from skillmeat.storage.rating_store import RatingManager


# Default priors based on SPIKE research
DEFAULT_QUALITY_PRIOR = 50.0  # Neutral quality assumption
DEFAULT_PRIOR_WEIGHT = 5  # Weight of prior (virtual ratings count)

# Trust score priors by source type (from SPIKE research)
SOURCE_TRUST_PRIORS: dict[str, float] = {
    "official": 95.0,  # Anthropic official artifacts
    "verified": 80.0,  # Verified community sources
    "github": 60.0,  # GitHub sources (variable quality)
    "local": 50.0,  # Local/user-created artifacts
    "unknown": 40.0,  # Unknown/unverified sources
}


class QualityScorer:
    """Calculate quality scores for artifacts using Bayesian averaging.

    This scorer handles the cold-start problem by using Bayesian priors:
    - New artifacts start at prior quality (50)
    - As ratings accumulate, actual ratings dominate
    - After ~10 ratings, prior has minimal effect

    Example:
        >>> scorer = QualityScorer()
        >>> score = scorer.calculate_quality_score("skill:canvas-design")
        >>> print(f"Quality: {score:.1f}/100")
    """

    def __init__(
        self,
        rating_manager: RatingManager | None = None,
        prior: float = DEFAULT_QUALITY_PRIOR,
        prior_weight: int = DEFAULT_PRIOR_WEIGHT,
    ):
        """Initialize scorer with optional custom priors.

        Args:
            rating_manager: RatingManager instance (creates new if None)
            prior: Default quality prior (0-100)
            prior_weight: Weight of prior in Bayesian formula
        """
        self.rating_manager = rating_manager or RatingManager()
        self.prior = prior
        self.prior_weight = prior_weight

    def calculate_quality_score(self, artifact_id: str) -> float:
        """Calculate Bayesian quality score for an artifact.

        Uses Bayesian averaging: (prior * weight + mean * count) / (weight + count)

        Args:
            artifact_id: Artifact identifier (e.g., "skill:canvas-design")

        Returns:
            Quality score from 0-100

        Example:
            >>> scorer = QualityScorer()
            >>> # No ratings → returns prior (50)
            >>> score = scorer.calculate_quality_score("new:artifact")
            >>> assert score == 50.0
            >>>
            >>> # With ratings → weighted average
            >>> score = scorer.calculate_quality_score("rated:artifact")
        """
        ratings = self.rating_manager.get_ratings(artifact_id)

        if not ratings:
            # Cold start: return prior
            return self.prior

        # Calculate mean rating (1-5 scale)
        rating_sum = sum(r.rating for r in ratings)
        count = len(ratings)
        actual_mean = rating_sum / count

        # Scale from 1-5 to 0-100
        # Rating 1 → 0, Rating 5 → 100
        actual_mean_scaled = (actual_mean - 1) * 25

        # Bayesian average
        quality = ((self.prior * self.prior_weight) + (actual_mean_scaled * count)) / (
            self.prior_weight + count
        )

        return round(quality, 2)

    def get_trust_score(self, source_type: str = "unknown") -> float:
        """Get trust score based on artifact source type.

        Args:
            source_type: Source type key (official, verified, github, local, unknown)

        Returns:
            Trust score from 0-100

        Example:
            >>> scorer = QualityScorer()
            >>> scorer.get_trust_score("official")  # Returns 95.0
            >>> scorer.get_trust_score("github")    # Returns 60.0
        """
        return SOURCE_TRUST_PRIORS.get(source_type, SOURCE_TRUST_PRIORS["unknown"])

    def calculate_confidence_score(
        self,
        artifact_id: str,
        source_type: str = "unknown",
        match_score: float | None = None,
    ) -> dict:
        """Calculate full confidence score with all components.

        Confidence = (trust * 0.25) + (quality * 0.25) + (match * 0.50)
        If match_score is None, uses 50/50 split between trust and quality.

        Args:
            artifact_id: Artifact identifier
            source_type: Source type for trust scoring
            match_score: Optional query match score (0-100)

        Returns:
            Dict with trust_score, quality_score, match_score, confidence, schema_version

        Example:
            >>> scorer = QualityScorer()
            >>> result = scorer.calculate_confidence_score("skill:canvas", "github", 85.0)
            >>> print(f"Confidence: {result['confidence']:.1f}")
        """
        trust_score = self.get_trust_score(source_type)
        quality_score = self.calculate_quality_score(artifact_id)

        if match_score is not None:
            # Full weighting: 25/25/50
            confidence = (
                (trust_score * 0.25) + (quality_score * 0.25) + (match_score * 0.50)
            )
        else:
            # No match: 50/50 between trust and quality
            confidence = (trust_score * 0.5) + (quality_score * 0.5)

        return {
            "artifact_id": artifact_id,
            "trust_score": round(trust_score, 2),
            "quality_score": round(quality_score, 2),
            "match_score": round(match_score, 2) if match_score is not None else None,
            "confidence": round(confidence, 2),
            "schema_version": "1.0.0",
        }

    def get_rating_count(self, artifact_id: str) -> int:
        """Get number of ratings for an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Count of user ratings
        """
        ratings = self.rating_manager.get_ratings(artifact_id)
        return len(ratings)
