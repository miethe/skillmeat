"""Compatibility tests for HaikuEmbedder storage format."""

import json
import sqlite3
import tempfile
from datetime import datetime
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


def test_legacy_json_compatibility(temp_cache_db):
    """Test that the embedder can still read legacy JSON embeddings."""
    # 1. Manually insert a legacy JSON embedding directly into SQLite
    conn = sqlite3.connect(str(temp_cache_db))
    cursor = conn.cursor()

    # Create table manually
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            text_hash TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            accessed_at TEXT NOT NULL
        )
    """
    )

    model = "claude-haiku-4.5-20250929"
    text = "legacy text"
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

    embedder_temp = HaikuEmbedder(cache_db=temp_cache_db)
    text_hash = embedder_temp._hash_text(text)

    embedding_json = json.dumps(embedding)
    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        INSERT INTO embeddings
        (text_hash, text, embedding, model, created_at, accessed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (text_hash, text, embedding_json, model, now, now),
    )
    conn.commit()
    conn.close()

    # 2. Use HaikuEmbedder to retrieve it
    embedder = HaikuEmbedder(cache_db=temp_cache_db)
    cached = embedder._get_cached_embedding(text)

    assert cached is not None
    assert cached == embedding
    assert isinstance(cached, list)
    assert len(cached) == 5

def test_new_binary_storage(temp_cache_db):
    """Test that new embeddings are stored as binary."""
    embedder = HaikuEmbedder(cache_db=temp_cache_db)

    text = "new binary text"
    embedding = [0.5, 0.4, 0.3, 0.2, 0.1]

    # Cache it (should use new binary format)
    embedder._cache_embedding(text, embedding)

    # Retrieve it (should work via standard API)
    cached = embedder._get_cached_embedding(text)
    # Check with tolerance for float32 precision
    assert cached == pytest.approx(embedding, abs=1e-6)

    # Verify underlying storage is bytes
    conn = sqlite3.connect(str(temp_cache_db))
    cursor = conn.cursor()

    text_hash = embedder._hash_text(text)
    cursor.execute("SELECT embedding FROM embeddings WHERE text_hash = ?", (text_hash,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    stored_data = row[0]

    assert isinstance(stored_data, bytes)
    # Check length: 5 floats * 4 bytes = 20 bytes
    assert len(stored_data) == 20
