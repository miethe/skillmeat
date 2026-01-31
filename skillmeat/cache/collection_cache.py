"""TTL-based cache for collection artifact counts.

This module provides a thread-safe, in-memory cache for collection artifact
counts with configurable TTL. The cache reduces database queries by storing
artifact counts that are eventually consistent with a 5-minute staleness window.

Example:
    >>> from skillmeat.cache.collection_cache import get_collection_count_cache
    >>> cache = get_collection_count_cache()
    >>> cache.set_counts({"col-1": 5, "col-2": 10})
    >>> cached, missing = cache.get_counts({"col-1", "col-2", "col-3"})
    >>> # cached = {"col-1": 5, "col-2": 10}, missing = {"col-3"}
"""

import time
from threading import Lock
from typing import Dict, Optional, Set, Tuple


class CollectionCountCache:
    """
    Thread-safe TTL-based cache for collection artifact counts.

    Counts are eventually consistent with 5-minute staleness window.
    The cache uses a simple Dict with (count, timestamp) tuples and
    a threading.Lock for thread safety.

    Attributes:
        DEFAULT_TTL: Default time-to-live in seconds (300 = 5 minutes).
    """

    DEFAULT_TTL: int = 300  # 5 minutes

    def __init__(self, ttl: int = DEFAULT_TTL) -> None:
        """
        Initialize the cache with a configurable TTL.

        Args:
            ttl: Time-to-live in seconds for cache entries.
                 Defaults to DEFAULT_TTL (300 seconds / 5 minutes).
        """
        self._cache: Dict[str, Tuple[int, float]] = {}  # id -> (count, timestamp)
        self._ttl = ttl
        self._lock = Lock()

    def get_counts(
        self, collection_ids: Set[str]
    ) -> Tuple[Dict[str, int], Set[str]]:
        """
        Get cached counts for collections.

        Looks up each collection ID in the cache and returns the count
        if it exists and has not expired. Expired entries are removed
        during lookup.

        Args:
            collection_ids: Set of collection IDs to lookup.

        Returns:
            A tuple of (cached_counts, missing_ids):
            - cached_counts: Dict of collection_id -> count for cache hits
            - missing_ids: Set of collection_ids not in cache or expired
        """
        now = time.time()
        cached: Dict[str, int] = {}
        missing: Set[str] = set()

        with self._lock:
            for cid in collection_ids:
                if cid in self._cache:
                    count, ts = self._cache[cid]
                    if now - ts < self._ttl:
                        cached[cid] = count
                    else:
                        # Expired - remove from cache
                        del self._cache[cid]
                        missing.add(cid)
                else:
                    missing.add(cid)

        return cached, missing

    def set_counts(self, counts: Dict[str, int]) -> None:
        """
        Set counts in cache.

        Stores artifact counts with the current timestamp. Existing entries
        for the same collection IDs are overwritten.

        Args:
            counts: Dict of collection_id -> artifact_count to cache.
        """
        now = time.time()
        with self._lock:
            for cid, count in counts.items():
                self._cache[cid] = (count, now)

    def invalidate(self, collection_id: str) -> None:
        """
        Invalidate cache for a specific collection.

        Removes the cache entry for the given collection ID if it exists.
        This should be called when artifacts are added to or removed from
        a collection.

        Args:
            collection_id: Collection ID to invalidate.
        """
        with self._lock:
            self._cache.pop(collection_id, None)

    def invalidate_all(self) -> None:
        """
        Clear entire cache.

        Removes all cached entries. Useful for testing or when a major
        data change occurs that affects multiple collections.
        """
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dict with cache statistics:
            - size: Number of entries currently in the cache
            - ttl: Configured TTL in seconds
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "ttl": self._ttl,
            }


# Singleton instance
_cache_instance: Optional[CollectionCountCache] = None


def get_collection_count_cache() -> CollectionCountCache:
    """
    Get singleton cache instance.

    Returns the global CollectionCountCache instance, creating it on
    first access with default TTL.

    Returns:
        The singleton CollectionCountCache instance.
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CollectionCountCache()
    return _cache_instance
