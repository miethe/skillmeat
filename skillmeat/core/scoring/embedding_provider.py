"""Abstract interface for embedding generation.

This module defines the EmbeddingProvider interface for generating vector
embeddings from text. Implementations can use various backends (Anthropic API,
local models, etc.) while providing a consistent interface.

The provider pattern allows graceful degradation when embeddings are unavailable,
enabling the scoring system to fall back to keyword-based matching.

Example:
    >>> provider = SomeEmbeddingProvider()
    >>> if provider.is_available():
    ...     embedding = await provider.get_embedding("process PDF files")
    ...     print(f"Embedding dimension: {len(embedding)}")
    ... else:
    ...     print("Provider unavailable, using fallback")
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation.

    Implementations should handle API errors gracefully and return None
    when embeddings cannot be generated, allowing callers to implement
    fallback strategies.

    All embeddings from a single provider should have the same dimensionality
    to enable vector similarity calculations.
    """

    @abstractmethod
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed (query or artifact description)

        Returns:
            List of float values representing the embedding vector,
            or None if embedding generation fails or is unavailable.

        Example:
            >>> provider = SomeEmbeddingProvider()
            >>> embedding = await provider.get_embedding("process PDF")
            >>> if embedding:
            ...     print(f"Generated {len(embedding)}-dimensional vector")
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured.

        Returns:
            True if provider can generate embeddings, False otherwise.

        Example:
            >>> provider = SomeEmbeddingProvider()
            >>> if not provider.is_available():
            ...     print("API key missing or service unavailable")
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings from this provider.

        Returns:
            Number of dimensions in embedding vectors.

        Example:
            >>> provider = SomeEmbeddingProvider()
            >>> dim = provider.get_embedding_dimension()
            >>> print(f"Embeddings are {dim}-dimensional")
        """
        pass
