"""High-level scoring service with graceful degradation.

This module provides the ScoringService class that orchestrates semantic
and keyword-based scoring with automatic fallback and error handling.

Example:
    >>> from skillmeat.core.scoring.service import ScoringService
    >>> from skillmeat.core.scoring.haiku_embedder import HaikuEmbedder
    >>>
    >>> # Initialize service
    >>> embedder = HaikuEmbedder()
    >>> service = ScoringService(embedder=embedder)
    >>>
    >>> # Score artifacts with automatic fallback
    >>> result = await service.score_artifacts("pdf tool", artifacts)
    >>> if result.degraded:
    ...     print(f"Warning: {result.degradation_reason}")
    >>> for score in result.scores[:5]:
    ...     print(f"{score.artifact_id}: {score.confidence:.1f}")
"""

import asyncio
import logging
import time
from typing import List, Tuple

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.exceptions import (
    EmbeddingServiceUnavailable,
    ScoringTimeout,
)
from skillmeat.core.scoring.haiku_embedder import HaikuEmbedder
from skillmeat.core.scoring.match_analyzer import MatchAnalyzer
from skillmeat.core.scoring.models import ArtifactScore, ScoringResult
from skillmeat.core.scoring.semantic_scorer import SemanticScorer
from skillmeat.core.scoring.utils import with_timeout

logger = logging.getLogger(__name__)


class ScoringService:
    """High-level scoring service with graceful degradation.

    This service provides a unified interface for scoring artifacts that
    automatically handles:
    - Semantic scoring when embeddings are available
    - Graceful degradation to keyword-only when embeddings fail
    - Timeout handling with configurable thresholds
    - Detailed metadata about degradation for UI feedback

    The service prefers semantic scoring but will transparently fall back
    to keyword-based scoring if:
    - Embedding service is unavailable (missing API key, network error)
    - Semantic scoring times out
    - Embedding generation fails for any reason

    Attributes:
        semantic_scorer: SemanticScorer instance for semantic matching
        keyword_scorer: MatchAnalyzer instance for keyword matching
        enable_semantic: Whether to attempt semantic scoring (default: True)
        semantic_timeout: Timeout for semantic scoring in seconds (default: 5.0)
        fallback_to_keyword: Whether to fall back to keyword on failure (default: True)

    Example:
        >>> # With semantic scoring enabled
        >>> service = ScoringService(
        ...     embedder=HaikuEmbedder(),
        ...     enable_semantic=True,
        ...     fallback_to_keyword=True,
        ... )
        >>>
        >>> result = await service.score_artifacts("pdf", artifacts)
        >>> if result.used_semantic:
        ...     print("Using high-quality semantic matching")
        ... else:
        ...     print(f"Degraded to keyword matching: {result.degradation_reason}")
        >>>
        >>> # Keyword-only mode (no API key needed)
        >>> service = ScoringService(enable_semantic=False)
        >>> result = await service.score_artifacts("pdf", artifacts)
        >>> assert not result.used_semantic
    """

    def __init__(
        self,
        embedder: HaikuEmbedder | None = None,
        enable_semantic: bool = True,
        semantic_timeout: float = 5.0,
        fallback_to_keyword: bool = True,
    ):
        """Initialize scoring service.

        Args:
            embedder: Embedding provider (defaults to HaikuEmbedder)
            enable_semantic: Whether to attempt semantic scoring (default: True)
            semantic_timeout: Timeout for semantic scoring in seconds (default: 5.0)
            fallback_to_keyword: Whether to fall back to keyword on failure (default: True)

        Example:
            >>> # With custom embedder
            >>> embedder = HaikuEmbedder(cache_db="~/.cache/embeddings.db")
            >>> service = ScoringService(embedder=embedder)
            >>>
            >>> # Keyword-only (no embedder needed)
            >>> service = ScoringService(enable_semantic=False)
            >>>
            >>> # Strict mode (no fallback, raises on timeout)
            >>> service = ScoringService(fallback_to_keyword=False)
        """
        # Initialize embedder if not provided
        if embedder is None and enable_semantic:
            embedder = HaikuEmbedder()

        # Initialize scorers
        self.semantic_scorer = (
            SemanticScorer(embedder) if embedder and enable_semantic else None
        )
        self.keyword_scorer = MatchAnalyzer()

        self.enable_semantic = enable_semantic
        self.semantic_timeout = semantic_timeout
        self.fallback_to_keyword = fallback_to_keyword

    @property
    def semantic_available(self) -> bool:
        """Check if semantic scoring is currently available.

        Returns:
            True if semantic scorer is initialized and embedding service is available

        Example:
            >>> service = ScoringService()
            >>> if service.semantic_available:
            ...     print("✓ Semantic scoring enabled")
            ... else:
            ...     print("⚠ Using keyword-only scoring")
        """
        if not self.enable_semantic or self.semantic_scorer is None:
            return False
        return self.semantic_scorer.is_available()

    async def score_artifacts(
        self,
        query: str,
        artifacts: List[Tuple[str, ArtifactMetadata]],
        timeout: float | None = None,
    ) -> ScoringResult:
        """Score artifacts with automatic fallback on failure.

        This method attempts semantic scoring first (if enabled and available),
        then falls back to keyword scoring if semantic fails or times out.

        Args:
            query: Search query string
            artifacts: List of (name, ArtifactMetadata) tuples to score
            timeout: Override default semantic timeout (default: use service timeout)

        Returns:
            ScoringResult with scores, metadata, and degradation info

        Raises:
            ScoringTimeout: If scoring times out and fallback_to_keyword=False
            EmbeddingServiceUnavailable: If semantic unavailable and fallback_to_keyword=False

        Example:
            >>> artifacts = [
            ...     ("pdf-tool", ArtifactMetadata(title="PDF Tool", ...)),
            ...     ("image-tool", ArtifactMetadata(title="Image Tool", ...)),
            ... ]
            >>> result = await service.score_artifacts("pdf", artifacts)
            >>>
            >>> # Check for degradation
            >>> if result.degraded:
            ...     logger.warning(f"Degraded scoring: {result.degradation_reason}")
            >>>
            >>> # Display results
            >>> for score in result.scores:
            ...     print(f"{score.artifact_id}: {score.confidence:.1f}%")
        """
        start_time = time.perf_counter()
        timeout_seconds = timeout if timeout is not None else self.semantic_timeout

        # Default to keyword scoring
        used_semantic = False
        degraded = False
        degradation_reason = None

        # Try semantic scoring if enabled
        if self.enable_semantic and self.semantic_available:
            try:
                # Attempt semantic scoring with timeout
                semantic_scores = await with_timeout(
                    self._score_semantic(query, artifacts),
                    timeout_seconds=timeout_seconds,
                    fallback=None,
                    raise_on_timeout=not self.fallback_to_keyword,
                )

                if semantic_scores is not None:
                    # Semantic scoring succeeded
                    used_semantic = True
                    scores = semantic_scores
                else:
                    # Timeout occurred, use fallback
                    degraded = True
                    degradation_reason = (
                        f"Semantic scoring timed out after {timeout_seconds}s"
                    )
                    scores = self._score_keyword(query, artifacts)

            except EmbeddingServiceUnavailable as e:
                # Embedding service unavailable
                if not self.fallback_to_keyword:
                    raise

                degraded = True
                degradation_reason = f"Embedding service unavailable: {str(e)}"
                logger.warning(degradation_reason)
                scores = self._score_keyword(query, artifacts)

            except ScoringTimeout as e:
                # Timeout in strict mode
                if not self.fallback_to_keyword:
                    raise

                degraded = True
                degradation_reason = str(e)
                logger.warning(degradation_reason)
                scores = self._score_keyword(query, artifacts)

            except Exception as e:
                # Unexpected error
                logger.error(f"Semantic scoring failed unexpectedly: {e}")

                if not self.fallback_to_keyword:
                    raise

                degraded = True
                degradation_reason = f"Semantic scoring error: {str(e)}"
                scores = self._score_keyword(query, artifacts)

        elif self.enable_semantic and not self.semantic_available:
            # Semantic enabled but not available
            degraded = True
            degradation_reason = (
                "Embedding service not available (missing API key or configuration)"
            )
            scores = self._score_keyword(query, artifacts)

        else:
            # Semantic disabled, use keyword-only
            scores = self._score_keyword(query, artifacts)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        return ScoringResult(
            scores=scores,
            used_semantic=used_semantic,
            degraded=degraded,
            degradation_reason=degradation_reason,
            duration_ms=duration_ms,
            query=query,
        )

    async def _score_semantic(
        self, query: str, artifacts: List[Tuple[str, ArtifactMetadata]]
    ) -> List[ArtifactScore]:
        """Score artifacts using semantic similarity.

        Args:
            query: Search query
            artifacts: List of (name, metadata) tuples

        Returns:
            List of ArtifactScore objects sorted by match score

        Raises:
            EmbeddingServiceUnavailable: If embedding service fails
        """
        if self.semantic_scorer is None:
            raise EmbeddingServiceUnavailable("Semantic scorer not initialized")

        results = []
        for name, metadata in artifacts:
            # Score artifact semantically
            match_score = await self.semantic_scorer.score_artifact(query, metadata)

            if match_score is None:
                # Semantic scoring failed for this artifact
                raise EmbeddingServiceUnavailable(
                    "Failed to generate embeddings for artifact"
                )

            # Create ArtifactScore
            # Note: For now, we're only using match_score. In full implementation,
            # trust_score and quality_score would come from other sources.
            artifact_score = ArtifactScore(
                artifact_id=f"skill:{name}",  # Temporary format
                trust_score=50.0,  # Placeholder
                quality_score=50.0,  # Placeholder
                match_score=match_score,
                confidence=0.0,  # Will be calculated in __post_init__
            )
            results.append(artifact_score)

        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def _score_keyword(
        self, query: str, artifacts: List[Tuple[str, ArtifactMetadata]]
    ) -> List[ArtifactScore]:
        """Score artifacts using keyword matching.

        Args:
            query: Search query
            artifacts: List of (name, metadata) tuples

        Returns:
            List of ArtifactScore objects sorted by match score
        """
        # Use MatchAnalyzer for keyword scoring
        scored = self.keyword_scorer.score_all(query, artifacts, filter_threshold=False)

        # Convert to ArtifactScore objects
        results = []
        for name, metadata, match_score in scored:
            artifact_score = ArtifactScore(
                artifact_id=f"skill:{name}",  # Temporary format
                trust_score=50.0,  # Placeholder
                quality_score=50.0,  # Placeholder
                match_score=match_score,
                confidence=0.0,  # Will be calculated in __post_init__
            )
            results.append(artifact_score)

        return results
