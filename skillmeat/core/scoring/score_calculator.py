"""Composite scoring calculator for artifacts.

This module combines trust scores, quality scores, and match scores into a single
confidence score using weighted averaging. Match scores are computed by blending
keyword-based and semantic similarity scores when available.

Example:
    >>> from skillmeat.core.scoring.score_calculator import ScoreCalculator
    >>> from skillmeat.core.scoring.match_analyzer import MatchAnalyzer
    >>> from skillmeat.core.scoring.semantic_scorer import SemanticScorer
    >>> from skillmeat.core.scoring.context_booster import ContextBooster
    >>>
    >>> calculator = ScoreCalculator(
    ...     match_analyzer=MatchAnalyzer(),
    ...     semantic_scorer=SemanticScorer(embedder),
    ...     context_booster=ContextBooster(),
    ... )
    >>>
    >>> score = await calculator.calculate_score(
    ...     query="pdf converter",
    ...     artifact=artifact,
    ...     artifact_name="pdf-tool",
    ...     trust_score=75.0,
    ...     quality_score=80.0,
    ... )
    >>> print(f"Confidence: {score.confidence:.1f}%")
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.context_booster import ContextBooster
from skillmeat.core.scoring.match_analyzer import MatchAnalyzer
from skillmeat.core.scoring.models import ArtifactScore
from skillmeat.core.scoring.semantic_scorer import SemanticScorer

logger = logging.getLogger(__name__)

# Default weights for composite scoring (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "trust": 0.25,  # Source reputation
    "quality": 0.25,  # Community ratings
    "match": 0.50,  # Query relevance
}

# Semantic/keyword blending weights
SEMANTIC_WEIGHT = 0.60  # When semantic available: 60% semantic + 40% keyword
KEYWORD_WEIGHT = 0.40


class ScoreCalculator:
    """Composite scoring calculator combining multiple scoring components.

    This class orchestrates the scoring pipeline by:
    1. Computing keyword-based match scores (always available)
    2. Computing semantic similarity scores (if embeddings available)
    3. Blending semantic and keyword scores with configurable weights
    4. Applying context boost based on project type (if enabled)
    5. Combining trust, quality, and match scores into final confidence score

    Attributes:
        match_analyzer: Keyword-based match scorer
        semantic_scorer: Optional semantic similarity scorer (embeddings)
        context_booster: Optional project context scorer
        weights: Dict of weights for trust/quality/match (must sum to 1.0)
    """

    def __init__(
        self,
        match_analyzer: MatchAnalyzer,
        semantic_scorer: Optional[SemanticScorer] = None,
        context_booster: Optional[ContextBooster] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """Initialize score calculator.

        Args:
            match_analyzer: Keyword-based match scorer (required)
            semantic_scorer: Optional semantic similarity scorer
            context_booster: Optional project context booster
            weights: Optional custom weights dict (must sum to 1.0)

        Raises:
            ValueError: If weights don't sum to approximately 1.0

        Example:
            >>> calculator = ScoreCalculator(
            ...     match_analyzer=MatchAnalyzer(),
            ...     weights={"trust": 0.3, "quality": 0.3, "match": 0.4},
            ... )
        """
        self.match_analyzer = match_analyzer
        self.semantic_scorer = semantic_scorer
        self.context_booster = context_booster
        self.weights = weights or DEFAULT_WEIGHTS.copy()

        # Validate weights sum to 1.0
        weight_sum = sum(self.weights.values())
        if not 0.99 <= weight_sum <= 1.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {weight_sum:.3f}. "
                f"Weights: {self.weights}"
            )

    async def calculate_score(
        self,
        query: str,
        artifact: ArtifactMetadata,
        artifact_name: str,
        artifact_type: str = "skill",
        trust_score: float = 50.0,
        quality_score: float = 50.0,
    ) -> ArtifactScore:
        """Calculate composite confidence score for an artifact.

        Computes match score by blending keyword and semantic similarity,
        applies context boost if configured, then combines with trust
        and quality scores using weighted average.

        Args:
            query: User search query
            artifact: Artifact metadata to score
            artifact_name: Artifact name (for keyword matching)
            artifact_type: Artifact type (skill/command/agent, default: skill)
            trust_score: Source trust score 0-100 (default: 50 for unknown sources)
            quality_score: Community quality score 0-100 (default: 50 for unrated)

        Returns:
            ArtifactScore with all component scores and final confidence

        Example:
            >>> score = await calculator.calculate_score(
            ...     query="pdf converter",
            ...     artifact=artifact,
            ...     artifact_name="pdf-tool",
            ...     trust_score=75.0,
            ...     quality_score=80.0,
            ... )
            >>> assert 0 <= score.confidence <= 100
        """
        # Validate input scores
        if not 0 <= trust_score <= 100:
            raise ValueError(f"trust_score must be 0-100, got {trust_score}")
        if not 0 <= quality_score <= 100:
            raise ValueError(f"quality_score must be 0-100, got {quality_score}")

        # 1. Compute keyword match score (always available)
        keyword_score = self.match_analyzer.score_artifact(
            query=query, artifact=artifact, artifact_name=artifact_name
        )

        # 2. Attempt semantic scoring if available
        semantic_score: Optional[float] = None
        if self.semantic_scorer and self.semantic_scorer.is_available():
            try:
                semantic_score = await self.semantic_scorer.score_artifact(
                    query=query, artifact=artifact
                )
            except Exception as e:
                logger.warning(f"Semantic scoring failed: {e}, using keyword only")
                semantic_score = None

        # 3. Blend semantic and keyword scores
        if semantic_score is not None:
            # Blend: 60% semantic + 40% keyword
            match_score = (semantic_score * SEMANTIC_WEIGHT) + (
                keyword_score * KEYWORD_WEIGHT
            )
            logger.debug(
                f"Blended match score: {match_score:.1f} "
                f"(semantic={semantic_score:.1f}, keyword={keyword_score:.1f})"
            )
        else:
            # Fallback to 100% keyword score
            match_score = keyword_score
            logger.debug(f"Using keyword-only match score: {match_score:.1f}")

        # 4. Apply context boost if configured
        if self.context_booster:
            match_score = self.context_booster.apply_boost(artifact, match_score)
            # Clamp to valid range after boost
            match_score = min(100.0, match_score)
            logger.debug(f"After context boost: {match_score:.1f}")

        # 5. Calculate composite confidence score
        confidence = (
            (trust_score * self.weights["trust"])
            + (quality_score * self.weights["quality"])
            + (match_score * self.weights["match"])
        )

        # Ensure confidence is in valid range
        confidence = min(100.0, max(0.0, confidence))

        # 6. Build ArtifactScore result
        artifact_id = f"{artifact_type}:{artifact_name}"

        return ArtifactScore(
            artifact_id=artifact_id,
            trust_score=trust_score,
            quality_score=quality_score,
            match_score=match_score,
            confidence=confidence,
            schema_version="1.0.0",
            last_updated=datetime.now(timezone.utc),
        )

    async def calculate_scores(
        self,
        query: str,
        artifacts: List[Tuple[str, ArtifactMetadata, str]],
        trust_scores: Optional[Dict[str, float]] = None,
        quality_scores: Optional[Dict[str, float]] = None,
    ) -> List[ArtifactScore]:
        """Calculate scores for multiple artifacts in batch.

        Args:
            query: User search query
            artifacts: List of (artifact_name, metadata, artifact_type) tuples
            trust_scores: Optional dict mapping artifact names to trust scores
            quality_scores: Optional dict mapping artifact names to quality scores

        Returns:
            List of ArtifactScore objects sorted by descending confidence

        Example:
            >>> artifacts = [
            ...     ("pdf-tool", pdf_metadata, "skill"),
            ...     ("image-tool", image_metadata, "skill"),
            ... ]
            >>> scores = await calculator.calculate_scores(
            ...     query="pdf converter",
            ...     artifacts=artifacts,
            ...     trust_scores={"pdf-tool": 75.0},
            ... )
            >>> assert scores[0].confidence >= scores[1].confidence
        """
        trust_scores = trust_scores or {}
        quality_scores = quality_scores or {}

        results = []
        for artifact_name, artifact, artifact_type in artifacts:
            # Get trust and quality scores with defaults
            trust = trust_scores.get(artifact_name, 50.0)
            quality = quality_scores.get(artifact_name, 50.0)

            # Calculate composite score
            score = await self.calculate_score(
                query=query,
                artifact=artifact,
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                trust_score=trust,
                quality_score=quality,
            )

            results.append(score)

        # Sort by confidence descending
        results.sort(key=lambda s: s.confidence, reverse=True)

        return results
