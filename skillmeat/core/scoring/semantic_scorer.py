"""Semantic similarity scoring using embeddings.

This module provides the SemanticScorer class for computing semantic similarity
between user queries and artifact descriptions using vector embeddings.

The scorer uses cosine similarity between embedding vectors to measure semantic
relatedness, providing more nuanced matching than keyword-based approaches.

Usage:
    >>> import asyncio
    >>> from skillmeat.core.scoring.semantic_scorer import SemanticScorer
    >>> from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder
    >>> from skillmeat.core.artifact import ArtifactMetadata
    >>>
    >>> embedder = SentenceTransformerEmbedder()
    >>> scorer = SemanticScorer(embedder)
    >>>
    >>> artifact = ArtifactMetadata(
    ...     title="PDF Processor",
    ...     description="Process and extract text from PDF files"
    ... )
    >>>
    >>> if scorer.is_available():
    ...     score = asyncio.run(scorer.score_artifact("process PDFs", artifact))
    ...     if score:
    ...         print(f"Semantic similarity: {score:.1f}%")
"""

import logging
import math
from pathlib import Path
from typing import List, Optional, Tuple

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class SemanticScorer:
    """Semantic similarity scoring using embeddings.

    This scorer computes semantic similarity between user queries and artifact
    descriptions by comparing their embedding vectors using cosine similarity.

    The scorer provides graceful degradation: if embeddings are unavailable
    (missing API key, network error, etc.), it returns None and allows the
    caller to fall back to keyword-based matching.

    Attributes:
        provider: EmbeddingProvider instance for generating embeddings
        min_score: Minimum similarity threshold (0-100, default: 0)
        max_score: Maximum similarity score (0-100, default: 100)

    Example:
        >>> from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder
        >>> provider = SentenceTransformerEmbedder()
        >>> scorer = SemanticScorer(provider)
        >>>
        >>> if scorer.is_available():
        ...     score = await scorer.score_artifact(query, artifact)
        ...     print(f"Match: {score:.1f}%")
        ... else:
        ...     # Fall back to keyword matching
        ...     score = keyword_score(query, artifact)
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        min_score: float = 0.0,
        max_score: float = 100.0,
    ):
        """Initialize semantic scorer.

        Args:
            provider: EmbeddingProvider instance for generating embeddings
            min_score: Minimum similarity threshold (default: 0)
            max_score: Maximum similarity score (default: 100)

        Example:
            >>> from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder
            >>> embedder = SentenceTransformerEmbedder()
            >>> scorer = SemanticScorer(embedder, min_score=20)
        """
        self.provider = provider
        self.min_score = min_score
        self.max_score = max_score

    def is_available(self) -> bool:
        """Check if semantic scoring is available.

        Returns:
            True if provider is available and can generate embeddings.

        Example:
            >>> scorer = SemanticScorer(embedder)
            >>> if scorer.is_available():
            ...     # Use semantic scoring
            ... else:
            ...     # Fall back to keyword matching
        """
        return self.provider.is_available()

    async def score_artifact(
        self, query: str, artifact: ArtifactMetadata
    ) -> Optional[float]:
        """Compute semantic similarity between query and artifact.

        This method generates embeddings for both the query and the artifact
        description, then computes cosine similarity between them.

        Args:
            query: User search query
            artifact: Artifact metadata with description

        Returns:
            Similarity score from 0-100, or None if embeddings are unavailable.

        Example:
            >>> artifact = ArtifactMetadata(
            ...     title="PDF Tool",
            ...     description="Extract text from PDF documents"
            ... )
            >>> score = await scorer.score_artifact("process PDFs", artifact)
            >>> if score and score > 90:
            ...     print("High semantic similarity!")
        """
        if not self.is_available():
            logger.debug("Semantic scorer unavailable, returning None")
            return None

        if not query or not query.strip():
            logger.warning("Empty query provided")
            return None

        # Get artifact text to embed
        artifact_text = self._get_artifact_text(artifact)
        if not artifact_text:
            logger.warning(f"No description for artifact: {artifact.title}")
            return self.min_score

        # Generate embeddings
        query_embedding = await self.provider.get_embedding(query.strip())
        if query_embedding is None:
            logger.debug("Failed to generate query embedding")
            return None

        artifact_embedding = await self.provider.get_embedding(artifact_text)
        if artifact_embedding is None:
            logger.debug("Failed to generate artifact embedding")
            return None

        # Compute cosine similarity
        similarity = self._cosine_similarity(query_embedding, artifact_embedding)

        # Scale to 0-100 range
        score = similarity * 100.0

        # Clamp to min/max range
        score = max(self.min_score, min(self.max_score, score))

        return round(score, 2)

    async def score_all(
        self, query: str, artifacts: List[ArtifactMetadata]
    ) -> List[Tuple[ArtifactMetadata, Optional[float]]]:
        """Score all artifacts semantically.

        Args:
            query: User search query
            artifacts: List of artifact metadata objects

        Returns:
            List of (artifact, score) tuples, where score is None if unavailable.

        Example:
            >>> results = await scorer.score_all("PDF processing", artifacts)
            >>> for artifact, score in results:
            ...     if score is not None:
            ...         print(f"{artifact.title}: {score:.1f}%")
        """
        results = []
        for artifact in artifacts:
            score = await self.score_artifact(query, artifact)
            results.append((artifact, score))

        return results

    def _get_artifact_text(self, artifact: ArtifactMetadata) -> str:
        """Extract text from artifact for embedding.

        Combines title, description, and tags into a single text string.

        Args:
            artifact: Artifact metadata

        Returns:
            Combined text string for embedding
        """
        parts = []

        if artifact.title:
            parts.append(artifact.title)

        if artifact.description:
            parts.append(artifact.description)

        if artifact.tags:
            # Add tags as keywords
            parts.append(" ".join(artifact.tags))

        return " ".join(parts).strip()

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Cosine similarity = dot(v1, v2) / (||v1|| * ||v2||)

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Similarity score from 0.0 (orthogonal) to 1.0 (identical)

        Raises:
            ValueError: If vectors have different dimensions

        Example:
            >>> v1 = [1.0, 0.0, 0.0]
            >>> v2 = [1.0, 0.0, 0.0]
            >>> similarity = SemanticScorer._cosine_similarity(v1, v2)
            >>> assert similarity == 1.0  # Identical vectors
            >>>
            >>> v3 = [0.0, 1.0, 0.0]
            >>> similarity = SemanticScorer._cosine_similarity(v1, v3)
            >>> assert similarity == 0.0  # Orthogonal vectors
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimension mismatch: {len(vec1)} != {len(vec2)}")

        if not vec1 or not vec2:
            return 0.0

        # Compute dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Compute magnitudes
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        # Avoid division by zero
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (mag1 * mag2)

        # Clamp to [-1, 1] to handle floating-point errors
        similarity = max(-1.0, min(1.0, similarity))

        # For semantic similarity, we typically care about positive similarity
        # Negative values (opposite directions) are treated as 0
        return max(0.0, similarity)
