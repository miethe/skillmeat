"""Haiku-based embedding provider using Anthropic API.

This module implements the EmbeddingProvider interface using Claude Haiku 4.5
for generating text embeddings. It uses the Anthropic SDK to call the API and
includes caching, error handling, and graceful degradation.

Usage:
    >>> import asyncio
    >>> from skillmeat.core.scoring.haiku_embedder import HaikuEmbedder
    >>>
    >>> embedder = HaikuEmbedder()
    >>> if embedder.is_available():
    ...     embedding = asyncio.run(embedder.get_embedding("process PDF"))
    ...     print(f"Generated {len(embedding)}-dimensional embedding")
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from skillmeat.core.scoring.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class HaikuEmbedder(EmbeddingProvider):
    """Embedding provider using Claude Haiku 4.5 via Anthropic API.

    This provider generates embeddings by calling the Anthropic API with Haiku.
    It includes SQLite caching to reduce API calls and costs.

    Attributes:
        api_key: Anthropic API key (from ANTHROPIC_API_KEY env var)
        model: Model name to use (default: claude-haiku-4.5-20250929)
        cache_db: Path to SQLite cache database
        cache_ttl: Time-to-live for cached embeddings (default: 7 days)

    Example:
        >>> embedder = HaikuEmbedder(cache_db="~/.skillmeat/embeddings.db")
        >>> if embedder.is_available():
        ...     embedding = await embedder.get_embedding("search PDFs")
        ... else:
        ...     print("API key not configured")
    """

    # Embedding dimension for Haiku text embeddings
    # Note: This is a placeholder - actual dimension depends on implementation
    EMBEDDING_DIMENSION = 768

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-haiku-4.5-20250929",
        cache_db: Optional[Path] = None,
        cache_ttl_days: int = 7,
    ):
        """Initialize Haiku embedder.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name to use for embeddings
            cache_db: Path to SQLite cache database (defaults to ~/.skillmeat/embeddings.db)
            cache_ttl_days: Number of days to cache embeddings (default: 7)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.cache_ttl = timedelta(days=cache_ttl_days)

        # Set up cache database
        if cache_db is None:
            cache_dir = Path.home() / ".skillmeat"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_db = cache_dir / "embeddings.db"
        else:
            self.cache_db = Path(cache_db).expanduser()
            self.cache_db.parent.mkdir(parents=True, exist_ok=True)

        # Initialize cache table
        self._init_cache()

        # Lazy-load Anthropic client
        self._client = None

    def _init_cache(self):
        """Initialize SQLite cache table for embeddings."""
        import sqlite3

        conn = sqlite3.connect(str(self.cache_db))
        cursor = conn.cursor()

        # Create embeddings cache table
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

        # Create index on created_at for TTL cleanup
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_embeddings_created_at
            ON embeddings(created_at)
        """
        )

        conn.commit()
        conn.close()

    def _get_client(self):
        """Get or create Anthropic client (lazy initialization)."""
        if self._client is None and self.api_key:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning(
                    "anthropic package not installed. Install with: pip install anthropic"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                return None

        return self._client

    def is_available(self) -> bool:
        """Check if Haiku embedder is available.

        Returns:
            True if API key is configured and client can be initialized.
        """
        return self.api_key is not None and self._get_client() is not None

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for Haiku.

        Returns:
            Embedding dimension (768 for Haiku text embeddings)
        """
        return self.EMBEDDING_DIMENSION

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using Haiku.

        This method first checks the cache for a valid embedding. If not found
        or expired, it calls the Anthropic API to generate a new embedding.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the embedding, or None if
            generation fails or provider is unavailable.

        Example:
            >>> embedder = HaikuEmbedder()
            >>> embedding = await embedder.get_embedding("process PDF files")
            >>> if embedding:
            ...     print(f"Dimension: {len(embedding)}")
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        if not self.is_available():
            logger.warning("Haiku embedder not available (missing API key)")
            return None

        # Normalize text
        text = text.strip()

        # Check cache first
        cached = self._get_cached_embedding(text)
        if cached is not None:
            logger.debug(f"Using cached embedding for: {text[:50]}...")
            return cached

        # Generate new embedding via API
        try:
            embedding = await self._generate_embedding(text)
            if embedding is not None:
                # Cache the result
                self._cache_embedding(text, embedding)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieve cached embedding if valid.

        Args:
            text: Text to look up

        Returns:
            Cached embedding if found and not expired, None otherwise
        """
        import json
        import sqlite3
        import struct

        text_hash = self._hash_text(text)
        cutoff_time = (datetime.utcnow() - self.cache_ttl).isoformat()

        conn = sqlite3.connect(str(self.cache_db))
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT embedding FROM embeddings
                WHERE text_hash = ? AND model = ? AND created_at > ?
            """,
                (text_hash, self.model, cutoff_time),
            )

            row = cursor.fetchone()
            if row:
                # Update access time
                cursor.execute(
                    """
                    UPDATE embeddings SET accessed_at = ?
                    WHERE text_hash = ? AND model = ?
                """,
                    (datetime.utcnow().isoformat(), text_hash, self.model),
                )
                conn.commit()

                # Deserialize embedding
                data = row[0]
                if isinstance(data, (bytes, bytearray, memoryview)):
                    # Optimized binary format (little-endian float32)
                    data_bytes = bytes(data)
                    if len(data_bytes) % 4 != 0:
                        return None
                    count = len(data_bytes) // 4  # float is 4 bytes
                    return list(struct.unpack(f"<{count}f", data_bytes))
                else:
                    # Legacy JSON string format
                    return json.loads(data)

            return None
        finally:
            conn.close()

    def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding for text.

        Args:
            text: Original text
            embedding: Embedding vector to cache
        """
        import sqlite3
        import struct

        text_hash = self._hash_text(text)
        # Store as binary blob (more efficient)
        embedding_blob = struct.pack(f"<{len(embedding)}f", *embedding)
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(str(self.cache_db))
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO embeddings
                (text_hash, text, embedding, model, created_at, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (text_hash, text, embedding_blob, self.model, now, now),
            )
            conn.commit()
        finally:
            conn.close()

    def _hash_text(self, text: str) -> str:
        """Generate hash for text to use as cache key.

        Args:
            text: Text to hash

        Returns:
            SHA256 hash of text + model name
        """
        # Include model in hash so different models don't collide
        content = f"{self.model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding via Anthropic API.

        This is a placeholder implementation. The actual implementation would
        use the Anthropic SDK to call the embedding API endpoint.

        Note: As of the knowledge cutoff, Anthropic does not have a dedicated
        embedding API. This implementation uses a prompt-based approach to
        generate embeddings from Haiku's text understanding.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if generation fails
        """
        client = self._get_client()
        if client is None:
            return None

        try:
            # Placeholder: In production, this would use actual embedding API
            # For now, we'll simulate by using a semantic encoding approach
            # via message completion and extracting features.

            # NOTE: This is a simplified placeholder. A real implementation would:
            # 1. Use a dedicated embedding endpoint if available
            # 2. Or use a prompt engineering approach to extract semantic features
            # 3. Or integrate with a local embedding model

            logger.warning(
                "Haiku embedding generation is a placeholder - implement actual API call"
            )

            # Return None to indicate embeddings are not yet implemented
            # This allows the system to gracefully fall back to keyword matching
            return None

        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None

    def cleanup_expired_cache(self):
        """Remove expired cache entries to save disk space.

        Example:
            >>> embedder = HaikuEmbedder()
            >>> embedder.cleanup_expired_cache()  # Remove entries older than TTL
        """
        import sqlite3

        cutoff_time = (datetime.utcnow() - self.cache_ttl).isoformat()

        conn = sqlite3.connect(str(self.cache_db))
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM embeddings WHERE created_at < ?
            """,
                (cutoff_time,),
            )
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} expired cache entries")
        finally:
            conn.close()
