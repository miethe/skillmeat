"""Tests for EmbeddingProvider abstract interface."""

import pytest

from skillmeat.core.scoring.embedding_provider import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock implementation for testing."""

    def __init__(self, available: bool = True, dimension: int = 768):
        self.available = available
        self.dimension = dimension

    async def get_embedding(self, text: str):
        if not self.available:
            return None
        # Return a simple mock embedding
        return [0.1] * self.dimension

    def is_available(self) -> bool:
        return self.available

    def get_embedding_dimension(self) -> int:
        return self.dimension


@pytest.mark.asyncio
async def test_provider_interface():
    """Test that EmbeddingProvider interface is correctly defined."""
    provider = MockEmbeddingProvider()

    # Should have required methods
    assert hasattr(provider, "get_embedding")
    assert hasattr(provider, "is_available")
    assert hasattr(provider, "get_embedding_dimension")

    # Should be callable
    embedding = await provider.get_embedding("test")
    assert embedding is not None
    assert len(embedding) == 768


@pytest.mark.asyncio
async def test_provider_availability():
    """Test availability checking."""
    # Available provider
    available_provider = MockEmbeddingProvider(available=True)
    assert available_provider.is_available() is True

    # Unavailable provider
    unavailable_provider = MockEmbeddingProvider(available=False)
    assert unavailable_provider.is_available() is False


@pytest.mark.asyncio
async def test_provider_dimension():
    """Test embedding dimension reporting."""
    provider = MockEmbeddingProvider(dimension=512)
    assert provider.get_embedding_dimension() == 512


@pytest.mark.asyncio
async def test_provider_returns_none_when_unavailable():
    """Test that unavailable provider returns None."""
    provider = MockEmbeddingProvider(available=False)
    embedding = await provider.get_embedding("test")
    assert embedding is None
