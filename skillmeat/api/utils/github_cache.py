"""GitHub file operation caching utilities.

Provides specialized in-memory caching for GitHub file trees and contents
with LRU eviction and time-based TTL support. Optimized for reducing
GitHub API calls when users browse artifact file structures repeatedly.

Cache Key Formats:
    - Trees: tree:{source_id}:{artifact_path}:{sha}
    - Contents: content:{source_id}:{artifact_path}:{file_path}:{sha}

Default TTLs:
    - File trees: 1 hour (3600 seconds)
    - File contents: 2 hours (7200 seconds)

Example:
    >>> cache = GitHubFileCache(max_entries=1000)
    >>> cache.set("tree:src-1:skills/canvas:abc123", tree_data, ttl_seconds=3600)
    >>> tree = cache.get("tree:src-1:skills/canvas:abc123")
    >>> if tree:
    ...     print("Cache hit!")
"""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

# Type variable for generic cache values
T = TypeVar("T")

# Default TTL values in seconds
DEFAULT_TREE_TTL = 3600  # 1 hour
DEFAULT_CONTENT_TTL = 7200  # 2 hours


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL support.

    Attributes:
        value: Cached data
        timestamp: Time when entry was cached (Unix timestamp)
        ttl_seconds: Time-to-live in seconds
    """

    value: T
    timestamp: float
    ttl_seconds: int

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if entry is expired based on TTL
        """
        return time.time() - self.timestamp > self.ttl_seconds

    def age(self) -> float:
        """Get age of cache entry in seconds.

        Returns:
            Age in seconds
        """
        return time.time() - self.timestamp

    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds.

        Returns:
            Remaining time before expiry (negative if expired)
        """
        return self.ttl_seconds - self.age()


class GitHubFileCache(Generic[T]):
    """Thread-safe LRU cache with TTL support for GitHub file operations.

    Provides in-memory caching optimized for file tree and content data
    from GitHub API operations. Supports configurable max entries with
    LRU eviction and per-entry TTL configuration.

    Attributes:
        max_entries: Maximum number of cache entries before LRU eviction

    Example:
        >>> cache = GitHubFileCache(max_entries=1000)
        >>>
        >>> # Cache a file tree (1 hour TTL)
        >>> tree_key = "tree:source-1:skills/canvas:abc123"
        >>> cache.set(tree_key, tree_data, ttl_seconds=3600)
        >>>
        >>> # Retrieve cached tree
        >>> cached_tree = cache.get(tree_key)
        >>> if cached_tree is not None:
        ...     print("Using cached tree data")
        >>>
        >>> # Cache file contents (2 hour TTL)
        >>> content_key = "content:source-1:skills/canvas:README.md:def456"
        >>> cache.set(content_key, file_content, ttl_seconds=7200)
    """

    def __init__(self, max_entries: int = 1000) -> None:
        """Initialize the GitHub file cache.

        Args:
            max_entries: Maximum number of cache entries. When exceeded,
                least recently used entries are evicted. Default: 1000
        """
        self.max_entries = max_entries
        # OrderedDict maintains insertion/access order for LRU
        self._cache: OrderedDict[str, CacheEntry[Any]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

        logger.info(f"GitHubFileCache initialized (max_entries={max_entries})")

    def get(self, key: str) -> Optional[T]:
        """Get cached value by key.

        Retrieves the cached value if it exists and hasn't expired.
        Updates LRU ordering on successful retrieval. Expired entries
        are automatically removed.

        Args:
            key: Cache key (e.g., "tree:source-1:path:sha")

        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss: {key}")
                return None

            entry = self._cache[key]

            # Check if expired
            if entry.is_expired():
                logger.debug(
                    f"Cache expired: {key} (age={entry.age():.1f}s, "
                    f"ttl={entry.ttl_seconds}s)"
                )
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end for LRU ordering (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1

            logger.debug(
                f"Cache hit: {key} (age={entry.age():.1f}s, "
                f"remaining={entry.remaining_ttl():.1f}s)"
            )
            return entry.value

    def set(self, key: str, value: T, ttl_seconds: int) -> None:
        """Cache a value with specified TTL.

        Stores the value with the given TTL. If cache is at capacity,
        least recently used entries are evicted first. Existing entries
        with the same key are overwritten.

        Args:
            key: Cache key (e.g., "tree:source-1:path:sha")
            value: Value to cache
            ttl_seconds: Time-to-live in seconds

        Example:
            >>> cache.set("tree:src:path:sha", tree_data, ttl_seconds=3600)
        """
        with self._lock:
            # If key exists, remove it first (will be re-added at end)
            if key in self._cache:
                del self._cache[key]
            # Evict LRU entries if at capacity
            elif len(self._cache) >= self.max_entries:
                self._evict_lru()

            # Create and store entry
            entry: CacheEntry[Any] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl_seconds=ttl_seconds,
            )
            self._cache[key] = entry

            logger.debug(f"Cached: {key} (ttl={ttl_seconds}s)")

    def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: Cache key to delete

        Returns:
            True if entry was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache entry: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info(f"Cleared GitHubFileCache ({count} entries)")

    def _evict_lru(self) -> None:
        """Evict the least recently used entry.

        Called internally when cache is at capacity before adding new entry.
        """
        if not self._cache:
            return

        # OrderedDict.popitem(last=False) removes oldest (least recently used)
        lru_key, _ = self._cache.popitem(last=False)
        logger.debug(f"Evicted LRU entry: {lru_key}")

    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Useful for periodic cleanup to free memory. Can be called
        from a background task or scheduler.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics:
                - entries: Current number of entries
                - max_entries: Maximum allowed entries
                - hits: Number of cache hits
                - misses: Number of cache misses
                - hit_rate: Hit rate percentage (0-100)
                - expired_count: Number of currently expired entries
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (
                (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            )
            expired_count = sum(
                1 for entry in self._cache.values() if entry.is_expired()
            )

            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "expired_count": expired_count,
            }

    def __len__(self) -> int:
        """Get the number of entries currently in the cache.

        Returns:
            Number of cached entries (including expired ones)
        """
        with self._lock:
            return len(self._cache)


# ============================================================================
# Cache Key Builders
# ============================================================================


def build_tree_key(source_id: str, artifact_path: str, sha: str) -> str:
    """Build cache key for a file tree.

    Args:
        source_id: Marketplace source identifier
        artifact_path: Path to artifact within repository
        sha: Git commit/tree SHA for cache invalidation

    Returns:
        Cache key string in format: tree:{source_id}:{artifact_path}:{sha}

    Example:
        >>> key = build_tree_key("src-123", "skills/canvas", "abc123")
        >>> print(key)
        tree:src-123:skills/canvas:abc123
    """
    return f"tree:{source_id}:{artifact_path}:{sha}"


def build_content_key(
    source_id: str, artifact_path: str, file_path: str, sha: str
) -> str:
    """Build cache key for file contents.

    Args:
        source_id: Marketplace source identifier
        artifact_path: Path to artifact within repository
        file_path: Path to file within artifact
        sha: Git commit/blob SHA for cache invalidation

    Returns:
        Cache key string in format:
        content:{source_id}:{artifact_path}:{file_path}:{sha}

    Example:
        >>> key = build_content_key("src-123", "skills/canvas", "SKILL.md", "def456")
        >>> print(key)
        content:src-123:skills/canvas:SKILL.md:def456
    """
    return f"content:{source_id}:{artifact_path}:{file_path}:{sha}"


# ============================================================================
# Global Instance
# ============================================================================

_global_github_cache: Optional[GitHubFileCache[Any]] = None
_global_cache_lock = threading.Lock()


def get_github_file_cache(max_entries: int = 1000) -> GitHubFileCache[Any]:
    """Get or create the global GitHub file cache instance.

    Returns a singleton instance of the GitHub file cache. The max_entries
    parameter is only used when creating the initial instance.

    Args:
        max_entries: Maximum cache entries (only used on first call)

    Returns:
        Global GitHubFileCache instance
    """
    global _global_github_cache

    if _global_github_cache is None:
        with _global_cache_lock:
            # Double-check after acquiring lock
            if _global_github_cache is None:
                _global_github_cache = GitHubFileCache(max_entries=max_entries)

    return _global_github_cache


def reset_github_file_cache() -> None:
    """Reset the global GitHub file cache instance.

    Primarily used for testing to ensure clean state between tests.
    """
    global _global_github_cache

    with _global_cache_lock:
        if _global_github_cache is not None:
            _global_github_cache.clear()
        _global_github_cache = None
