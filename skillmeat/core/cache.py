"""Metadata caching for SkillMeat.

Provides thread-safe in-memory caching of GitHub metadata with TTL support.
"""

import threading
import time
from typing import Any, Dict, Optional, Tuple


class MetadataCache:
    """Thread-safe in-memory cache for GitHub metadata with TTL expiration.

    Stores metadata entries with timestamps and automatically expires entries
    older than the configured TTL. Tracks cache hits and misses for monitoring.

    Attributes:
        ttl_seconds: Time-to-live in seconds for cache entries

    Example:
        >>> cache = MetadataCache(ttl_seconds=3600)
        >>> cache.set("anthropics/skills/canvas", {"title": "Canvas"})
        >>> metadata = cache.get("anthropics/skills/canvas")
        >>> if metadata:
        ...     print("Cache hit!")
        >>> print(cache.stats())
        {"hits": 1, "misses": 0, "size": 1}
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """Initialize the metadata cache.

        Args:
            ttl_seconds: Time-to-live in seconds for cache entries.
                Defaults to 3600 (1 hour).
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a value from the cache if it exists and is not expired.

        Args:
            key: The cache key to retrieve

        Returns:
            The cached value if it exists and is fresh, None otherwise.

        Note:
            Expired entries are automatically removed from the cache.
            Updates cache hit/miss statistics.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, timestamp = self._cache[key]
            age = time.time() - timestamp

            if age > self.ttl_seconds:
                # Entry expired, remove it
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return value

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Store a value in the cache with the current timestamp.

        Args:
            key: The cache key to store under
            value: The metadata dictionary to cache

        Note:
            Thread-safe operation. Overwrites existing entries.
        """
        with self._lock:
            self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        """Remove a specific entry from the cache.

        Args:
            key: The cache key to invalidate

        Note:
            No-op if the key doesn't exist.
        """
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from the cache and reset statistics.

        Note:
            Resets both the cache contents and hit/miss counters.
        """
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with keys:
                - hits: Number of cache hits
                - misses: Number of cache misses
                - size: Current number of entries in cache
        """
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
            }

    def cleanup(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            Number of entries removed

        Note:
            Useful for periodic cleanup to free memory.
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp > self.ttl_seconds
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def __len__(self) -> int:
        """Get the number of entries currently in the cache.

        Returns:
            Number of cached entries (including expired ones)
        """
        with self._lock:
            return len(self._cache)
