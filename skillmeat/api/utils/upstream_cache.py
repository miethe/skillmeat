"""Short-lived in-memory cache for upstream fetch results.

Prevents redundant GitHub API calls and file downloads when the sync modal
requests diff data for the same artifact multiple times within a short window.

Cache Key Format:
    "{artifact_id}:{collection_name}"

Where artifact_id is the "type:name" format and collection_name is the
collection identifier (or 'default' when not specified).

Default TTL:
    60 seconds — long enough to cover modal interaction sequences
    (upstream-diff + source-project-diff for the same artifact).

Thread Safety:
    Uses threading.Lock (not asyncio.Lock) because the cache is shared
    across sync/async contexts and FastAPI may use threadpool for sync
    endpoint operations.

Example:
    >>> cache = get_upstream_cache()
    >>> key = f"{artifact_id}:{collection or 'default'}"
    >>> result = cache.get(key)
    >>> if result is None:
    ...     result = artifact_mgr.fetch_update(...)
    ...     if not result.error:
    ...         cache.put(key, result)
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from skillmeat.core.artifact import UpdateFetchResult

logger = logging.getLogger(__name__)


@dataclass
class UpstreamCacheEntry:
    """A single cached upstream fetch result.

    Attributes:
        result: The full fetch result from ArtifactManager.fetch_update().
        created_at: Monotonic timestamp when this entry was cached.
    """

    result: UpdateFetchResult
    created_at: float

    def is_expired(self, ttl_seconds: float) -> bool:
        """Return True if the entry has exceeded its TTL.

        Args:
            ttl_seconds: Time-to-live in seconds.

        Returns:
            True if the entry is expired and should be evicted.
        """
        return (time.monotonic() - self.created_at) > ttl_seconds

    def age(self) -> float:
        """Return the age of the entry in seconds.

        Returns:
            Elapsed seconds since the entry was created.
        """
        return time.monotonic() - self.created_at


class UpstreamFetchCache:
    """Short-lived in-memory cache for upstream fetch results.

    Prevents redundant GitHub API calls when the sync modal requests
    diff data for the same artifact multiple times within a short window
    (e.g., upstream-diff and source-project-diff called back-to-back).

    Only successful fetch results (where result.error is None/empty) are
    cached. Failed fetches are never stored so they are always retried.

    Attributes:
        DEFAULT_TTL: Default time-to-live in seconds (60s).

    Example:
        >>> cache = UpstreamFetchCache(ttl_seconds=60)
        >>> cache.put("skill:canvas:default", fetch_result)
        >>> cached = cache.get("skill:canvas:default")
        >>> if cached:
        ...     print("Cache hit — skipping GitHub API call")
    """

    DEFAULT_TTL: float = 60.0  # 60 seconds

    def __init__(self, ttl_seconds: float = DEFAULT_TTL) -> None:
        """Initialize the upstream fetch cache.

        Args:
            ttl_seconds: How long to keep entries before they expire.
                Default is 60 seconds, which comfortably covers modal
                interaction patterns.
        """
        self._cache: Dict[str, UpstreamCacheEntry] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

        logger.debug(f"UpstreamFetchCache initialized (ttl={ttl_seconds}s)")

    def get(self, key: str) -> Optional[UpdateFetchResult]:
        """Return a cached fetch result if present and not expired.

        Expired entries are evicted on access (lazy eviction).

        Args:
            key: Cache key in format "{artifact_id}:{collection_name}".

        Returns:
            The cached UpdateFetchResult, or None on cache miss or expiry.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                logger.debug(f"Upstream cache miss: {key}")
                return None
            if entry.is_expired(self._ttl):
                logger.debug(
                    f"Upstream cache expired: {key} (age={entry.age():.1f}s)"
                )
                del self._cache[key]
                return None
            logger.info(
                f"Upstream cache hit: {key} (age={entry.age():.1f}s)"
            )
            return entry.result

    def put(self, key: str, result: UpdateFetchResult) -> None:
        """Store a fetch result in the cache.

        Only call this for successful results (result.error is falsy).
        Failed results are never cached; callers must enforce this.

        Args:
            key: Cache key in format "{artifact_id}:{collection_name}".
            result: The UpdateFetchResult to cache.
        """
        with self._lock:
            self._cache[key] = UpstreamCacheEntry(
                result=result,
                created_at=time.monotonic(),
            )
            logger.debug(f"Upstream cache stored: {key} (ttl={self._ttl}s)")

    def invalidate(self, key: str) -> None:
        """Remove a specific cache entry.

        Args:
            key: Cache key to remove.
        """
        with self._lock:
            removed = self._cache.pop(key, None)
            if removed is not None:
                logger.debug(f"Upstream cache invalidated: {key}")

    def invalidate_artifact(self, artifact_id: str) -> None:
        """Remove all cache entries for a given artifact across all collections.

        Useful when an artifact is updated or deleted — ensures that all
        collection variants of the cached result are evicted.

        Args:
            artifact_id: The artifact identifier (type:name format).
                All keys starting with "{artifact_id}:" are removed.
        """
        prefix = f"{artifact_id}:"
        with self._lock:
            to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in to_remove:
                del self._cache[k]
            if to_remove:
                logger.debug(
                    f"Upstream cache: evicted {len(to_remove)} entries "
                    f"for artifact '{artifact_id}'"
                )

    def clear(self) -> None:
        """Remove all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Upstream cache cleared ({count} entries)")

    def evict_expired(self) -> int:
        """Remove all expired entries.

        Can be called periodically to bound memory usage. Under normal
        load the cache stays small (one entry per active artifact), so
        explicit eviction is rarely necessary.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            now = time.monotonic()
            to_remove = [
                k
                for k, v in self._cache.items()
                if (now - v.created_at) > self._ttl
            ]
            for k in to_remove:
                del self._cache[k]
            if to_remove:
                logger.debug(
                    f"Upstream cache: evicted {len(to_remove)} expired entries"
                )
            return len(to_remove)

    def size(self) -> int:
        """Return the current number of entries (including expired ones).

        Returns:
            Number of entries in the cache dict.
        """
        with self._lock:
            return len(self._cache)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_upstream_cache = UpstreamFetchCache()


def get_upstream_cache() -> UpstreamFetchCache:
    """Return the process-level upstream fetch cache singleton.

    The singleton is shared across all requests within the same server
    process, which is the intended behaviour — it is the cross-request
    deduplication that provides the performance benefit.

    Returns:
        The global UpstreamFetchCache instance.
    """
    return _upstream_cache


def reset_upstream_cache() -> None:
    """Replace the singleton with a fresh cache instance.

    Intended for use in tests that need a clean cache state between runs.
    """
    global _upstream_cache
    _upstream_cache = UpstreamFetchCache()
