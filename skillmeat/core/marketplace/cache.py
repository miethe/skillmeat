"""Caching layer for marketplace listings with ETag support.

This module provides thread-safe caching of marketplace listings with
ETag-based conditional requests for efficient bandwidth usage.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional

from .models import ListingPage

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry for marketplace listings.

    Attributes:
        data: Cached listing page data
        etag: ETag hash for conditional requests
        timestamp: Unix timestamp when entry was cached
        ttl: Time-to-live in seconds
    """

    data: ListingPage
    etag: str
    timestamp: float
    ttl: int = 300  # Default: 5 minutes

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if entry is older than TTL
        """
        return (time.time() - self.timestamp) > self.ttl

    def age_seconds(self) -> int:
        """Get age of cache entry in seconds.

        Returns:
            Age in seconds
        """
        return int(time.time() - self.timestamp)


class MarketplaceCache:
    """Thread-safe cache for marketplace listings.

    Implements ETag-based caching with configurable TTL. Cache keys are
    generated from query parameters to enable per-query caching.

    Thread Safety:
        All operations are protected by a thread lock for concurrent access.

    Attributes:
        ttl: Default time-to-live for cache entries (seconds)
        max_size: Maximum number of cached entries (LRU eviction)
        _cache: Internal cache storage
        _lock: Thread lock for concurrent access
    """

    def __init__(self, ttl: int = 300, max_size: int = 100):
        """Initialize marketplace cache.

        Args:
            ttl: Default TTL for cache entries in seconds (default: 300)
            max_size: Maximum cache entries before LRU eviction (default: 100)
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()

        logger.info(f"Initialized marketplace cache (ttl={ttl}s, max_size={max_size})")

    def get(
        self, cache_key: str, if_none_match: Optional[str] = None
    ) -> tuple[Optional[ListingPage], Optional[str], bool]:
        """Get cached listing page.

        Args:
            cache_key: Cache key (generated from query params)
            if_none_match: ETag from client's If-None-Match header

        Returns:
            Tuple of (data, etag, not_modified):
            - data: ListingPage if cache miss or modified, None if not modified
            - etag: Current ETag for the cache key
            - not_modified: True if client's ETag matches (304 response)
        """
        with self._lock:
            entry = self._cache.get(cache_key)

            # Cache miss
            if entry is None:
                logger.debug(f"Cache miss for key: {cache_key}")
                return None, None, False

            # Cache expired
            if entry.is_expired():
                logger.debug(
                    f"Cache expired for key: {cache_key} (age: {entry.age_seconds()}s)"
                )
                del self._cache[cache_key]
                return None, None, False

            # Check ETag match (304 Not Modified)
            if if_none_match and if_none_match == entry.etag:
                logger.debug(f"ETag match for key: {cache_key} (304 Not Modified)")
                return None, entry.etag, True

            # Cache hit
            logger.debug(
                f"Cache hit for key: {cache_key} (age: {entry.age_seconds()}s)"
            )
            return entry.data, entry.etag, False

    def set(self, cache_key: str, data: ListingPage, ttl: Optional[int] = None) -> str:
        """Store listing page in cache.

        Args:
            cache_key: Cache key (generated from query params)
            data: ListingPage to cache
            ttl: Optional TTL override (uses default if None)

        Returns:
            ETag for the cached data
        """
        with self._lock:
            # Generate ETag from data
            etag = self._generate_etag(data)

            # Create cache entry
            entry = CacheEntry(
                data=data,
                etag=etag,
                timestamp=time.time(),
                ttl=ttl or self.ttl,
            )

            # Evict oldest entry if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            # Store in cache
            self._cache[cache_key] = entry

            logger.debug(
                f"Cached data for key: {cache_key} (etag: {etag[:8]}..., "
                f"ttl: {entry.ttl}s)"
            )

            return etag

    def invalidate(self, cache_key: Optional[str] = None) -> None:
        """Invalidate cache entries.

        Args:
            cache_key: Specific key to invalidate (None = clear all)
        """
        with self._lock:
            if cache_key is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cleared all cache entries ({count} items)")
            elif cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Invalidated cache entry: {cache_key}")
            else:
                logger.debug(f"Cache key not found for invalidation: {cache_key}")

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_entries = len(self._cache)
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())

            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
            }

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

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
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def _generate_etag(self, data: ListingPage) -> str:
        """Generate ETag hash for listing page data.

        Args:
            data: ListingPage to hash

        Returns:
            ETag string (SHA-256 hash)
        """
        # Convert to JSON and hash
        json_str = data.model_dump_json(exclude_none=True)
        hash_obj = hashlib.sha256(json_str.encode())
        etag = hash_obj.hexdigest()

        return etag

    def _evict_lru(self) -> None:
        """Evict least recently used cache entry (oldest by timestamp)."""
        if not self._cache:
            return

        # Find oldest entry
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)

        # Remove oldest
        del self._cache[oldest_key]
        logger.debug(f"Evicted LRU cache entry: {oldest_key}")

    @staticmethod
    def generate_cache_key(**params) -> str:
        """Generate cache key from query parameters.

        Args:
            **params: Query parameters (e.g., page, tags, category)

        Returns:
            Cache key string
        """
        # Sort params for consistent keys
        sorted_params = sorted(params.items())

        # Convert to JSON string
        json_str = json.dumps(sorted_params, sort_keys=True)

        # Hash to create compact key
        hash_obj = hashlib.sha256(json_str.encode())
        cache_key = hash_obj.hexdigest()[:16]  # First 16 chars

        return cache_key
