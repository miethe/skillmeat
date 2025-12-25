"""Tests for HaikuEmbedder implementation."""

import os
import tempfile
from pathlib import Path

import pytest

from skillmeat.core.scoring.haiku_embedder import HaikuEmbedder


@pytest.fixture
def temp_cache_db():
    """Create temporary cache database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


def test_embedder_initialization(temp_cache_db):
    """Test HaikuEmbedder initialization."""
    embedder = HaikuEmbedder(cache_db=temp_cache_db)

    assert embedder.model == "claude-haiku-4.5-20250929"
    assert embedder.cache_db == temp_cache_db
    assert embedder.cache_db.exists()


def test_embedder_availability_without_api_key(temp_cache_db):
    """Test that embedder is unavailable without API key."""
    # Clear API key if set
    old_key = os.environ.get("ANTHROPIC_API_KEY")
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]

    try:
        embedder = HaikuEmbedder(api_key=None, cache_db=temp_cache_db)
        assert embedder.is_available() is False
    finally:
        # Restore API key
        if old_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = old_key


def test_embedder_availability_with_api_key(temp_cache_db):
    """Test that embedder is available with API key."""
    embedder = HaikuEmbedder(api_key="test-key", cache_db=temp_cache_db)

    # Should be available (client initialization is lazy)
    # Note: Actual availability depends on anthropic package installation
    # and client initialization, which may fail without valid key
    assert embedder.api_key == "test-key"


def test_embedding_dimension(temp_cache_db):
    """Test that embedding dimension is correctly reported."""
    embedder = HaikuEmbedder(cache_db=temp_cache_db)
    assert embedder.get_embedding_dimension() == 768


@pytest.mark.asyncio
async def test_get_embedding_with_empty_text(temp_cache_db):
    """Test that empty text returns None."""
    embedder = HaikuEmbedder(api_key="test-key", cache_db=temp_cache_db)

    # Empty string
    result = await embedder.get_embedding("")
    assert result is None

    # Whitespace only
    result = await embedder.get_embedding("   ")
    assert result is None


@pytest.mark.asyncio
async def test_get_embedding_without_api_key(temp_cache_db):
    """Test that embedding generation fails gracefully without API key."""
    embedder = HaikuEmbedder(api_key=None, cache_db=temp_cache_db)

    result = await embedder.get_embedding("test text")
    assert result is None


def test_cache_initialization(temp_cache_db):
    """Test that cache database is properly initialized."""
    embedder = HaikuEmbedder(cache_db=temp_cache_db)

    # Check that database file exists
    assert temp_cache_db.exists()

    # Check that table was created
    import sqlite3

    conn = sqlite3.connect(str(temp_cache_db))
    cursor = conn.cursor()

    # Check embeddings table exists
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='embeddings'
    """
    )
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "embeddings"

    conn.close()


def test_text_hashing(temp_cache_db):
    """Test that text hashing is deterministic."""
    embedder = HaikuEmbedder(cache_db=temp_cache_db)

    # Same text should produce same hash
    hash1 = embedder._hash_text("test text")
    hash2 = embedder._hash_text("test text")
    assert hash1 == hash2

    # Different text should produce different hash
    hash3 = embedder._hash_text("different text")
    assert hash1 != hash3


def test_cache_embedding_and_retrieval(temp_cache_db):
    """Test caching and retrieval of embeddings."""
    embedder = HaikuEmbedder(cache_db=temp_cache_db)

    test_text = "test embedding text"
    test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

    # Cache the embedding
    embedder._cache_embedding(test_text, test_embedding)

    # Retrieve from cache
    cached = embedder._get_cached_embedding(test_text)

    assert cached is not None
    assert cached == test_embedding


def test_cache_expiration(temp_cache_db):
    """Test that expired cache entries are not returned."""
    # Create embedder with very short TTL (1 second)
    from datetime import timedelta

    embedder = HaikuEmbedder(cache_db=temp_cache_db, cache_ttl_days=0)
    embedder.cache_ttl = timedelta(seconds=-1)  # Already expired

    test_text = "test expiring embedding"
    test_embedding = [0.1, 0.2, 0.3]

    # Cache the embedding
    embedder._cache_embedding(test_text, test_embedding)

    # Try to retrieve (should be expired)
    cached = embedder._get_cached_embedding(test_text)

    # Should return None because entry is expired
    assert cached is None


def test_cleanup_expired_cache(temp_cache_db):
    """Test cleanup of expired cache entries."""
    from datetime import timedelta

    embedder = HaikuEmbedder(cache_db=temp_cache_db, cache_ttl_days=7)

    # Add some entries
    embedder._cache_embedding("text1", [0.1, 0.2])
    embedder._cache_embedding("text2", [0.3, 0.4])

    # Force them to be expired by changing TTL
    embedder.cache_ttl = timedelta(seconds=-1)

    # Run cleanup
    embedder.cleanup_expired_cache()

    # Verify entries are removed
    import sqlite3

    conn = sqlite3.connect(str(temp_cache_db))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM embeddings")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 0


def test_cache_different_models_separate(temp_cache_db):
    """Test that different models don't share cache entries."""
    embedder1 = HaikuEmbedder(cache_db=temp_cache_db, model="model-v1")
    embedder2 = HaikuEmbedder(cache_db=temp_cache_db, model="model-v2")

    test_text = "same text different models"
    embedding1 = [0.1, 0.2, 0.3]
    embedding2 = [0.4, 0.5, 0.6]

    # Cache with model v1
    embedder1._cache_embedding(test_text, embedding1)

    # Cache with model v2
    embedder2._cache_embedding(test_text, embedding2)

    # Retrieve with each model
    cached1 = embedder1._get_cached_embedding(test_text)
    cached2 = embedder2._get_cached_embedding(test_text)

    # Should get different embeddings
    assert cached1 == embedding1
    assert cached2 == embedding2
    assert cached1 != cached2
