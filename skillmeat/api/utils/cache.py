"""Caching utilities for API responses.

Provides in-memory caching with TTL support, ETag generation, and conditional
GET support for efficient API responses.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL and ETag support.

    Attributes:
        data: Cached response data
        etag: ETag hash for conditional GET support
        timestamp: Timestamp when entry was cached
        ttl: Time-to-live in seconds
    """

    data: Any
    etag: str
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300  # 5 minutes default

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if entry is expired based on TTL
        """
        return time.time() - self.timestamp > self.ttl

    def age(self) -> float:
        """Get age of cache entry in seconds.

        Returns:
            Age in seconds
        """
        return time.time() - self.timestamp


def generate_etag(data: Any) -> str:
    """Generate ETag from response data.

    Creates a hash of the response data to use as an ETag for caching.
    Uses SHA-256 for strong consistency guarantees.

    Args:
        data: Response data (will be JSON serialized)

    Returns:
        ETag string (hex hash)
    """
    # Serialize data to JSON for consistent hashing
    if isinstance(data, (dict, list)):
        json_str = json.dumps(data, sort_keys=True, default=str)
    elif isinstance(data, str):
        json_str = data
    else:
        json_str = str(data)

    # Generate SHA-256 hash
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))
    etag = f'"{hash_obj.hexdigest()[:16]}"'  # Use first 16 chars, quoted

    return etag


class CacheManager:
    """In-memory cache manager with ETag support.

    Provides caching for API responses with automatic TTL expiration
    and ETag generation for conditional GET requests.

    Attributes:
        default_ttl: Default time-to-live for cache entries in seconds
        max_entries: Maximum number of cache entries (LRU eviction)
    """

    def __init__(self, default_ttl: int = 300, max_entries: int = 1000):
        """Initialize cache manager.

        Args:
            default_ttl: Default TTL in seconds (default: 5 minutes)
            max_entries: Maximum cache entries before LRU eviction
        """
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []  # Track access order for LRU

        logger.info(
            f"Cache manager initialized (ttl={default_ttl}s, max_entries={max_entries})"
        )

    def get(self, key: str) -> Optional[tuple[Any, str]]:
        """Get cached data and ETag.

        Args:
            key: Cache key

        Returns:
            Tuple of (data, etag) if found and not expired, None otherwise
        """
        if key not in self._cache:
            logger.debug(f"Cache miss: {key}")
            return None

        entry = self._cache[key]

        # Check if expired
        if entry.is_expired():
            logger.debug(f"Cache expired: {key} (age={entry.age():.1f}s)")
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None

        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        logger.debug(f"Cache hit: {key} (age={entry.age():.1f}s)")
        return (entry.data, entry.etag)

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> str:
        """Cache data with automatic ETag generation.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Optional TTL override (uses default if None)

        Returns:
            Generated ETag
        """
        # Generate ETag
        etag = generate_etag(data)

        # Use default TTL if not specified
        if ttl is None:
            ttl = self.default_ttl

        # Create cache entry
        entry = CacheEntry(data=data, etag=etag, ttl=ttl)

        # Check if we need to evict entries
        if len(self._cache) >= self.max_entries:
            self._evict_lru()

        # Store entry
        self._cache[key] = entry

        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        logger.debug(f"Cached: {key} (ttl={ttl}s, etag={etag})")
        return etag

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was invalidated, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            logger.debug(f"Invalidated cache: {key}")
            return True
        return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern.

        Args:
            pattern: Key pattern (supports wildcard with *)

        Returns:
            Number of entries invalidated
        """
        import fnmatch

        keys_to_remove = [
            key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)
        ]

        count = 0
        for key in keys_to_remove:
            if self.invalidate(key):
                count += 1

        if count > 0:
            logger.info(f"Invalidated {count} cache entries matching '{pattern}'")

        return count

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        logger.info(f"Cleared cache ({count} entries)")

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_order:
            return

        # Remove oldest entry
        lru_key = self._access_order.pop(0)
        if lru_key in self._cache:
            del self._cache[lru_key]
            logger.debug(f"Evicted LRU entry: {lru_key}")

    def cleanup_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self._cache)
        expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())

        return {
            "total_entries": total_entries,
            "expired_entries": expired_count,
            "active_entries": total_entries - expired_count,
            "max_entries": self.max_entries,
            "default_ttl": self.default_ttl,
        }


# Global cache instance
_global_cache: Optional[CacheManager] = None


def get_cache_manager(
    default_ttl: Optional[int] = None, max_entries: Optional[int] = None
) -> CacheManager:
    """Get or create global cache manager instance.

    Args:
        default_ttl: Override default TTL (only used on first call)
        max_entries: Override max entries (only used on first call)

    Returns:
        CacheManager instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = CacheManager(
            default_ttl=default_ttl or 300, max_entries=max_entries or 1000
        )

    return _global_cache
