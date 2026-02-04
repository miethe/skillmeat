"""TTL-based cache for deployment statistics.

This module provides a thread-safe, in-memory cache for deployment statistics
with a 2-minute TTL. The cache operates at two levels:

1. **Level 1 - Project Discovery**: Caches the list of discovered project paths.
   Project discovery scans the filesystem for .claude directories, which is
   expensive. This level caches those results.

2. **Level 2 - Per-Artifact Stats**: Caches deployment statistics for each
   artifact (keyed by name + type). Once projects are known, computing stats
   per artifact is cheaper but still benefits from caching.

Example:
    >>> from skillmeat.cache.deployment_stats_cache import get_deployment_stats_cache
    >>> cache = get_deployment_stats_cache()
    >>> cache.set_discovered_projects([Path("/project1"), Path("/project2")])
    >>> paths = cache.get_discovered_projects()  # Returns paths if not expired
    >>> cache.set_stats("my-skill", "skill", stats_obj)
    >>> cached = cache.get_stats("my-skill", "skill")  # Returns stats or None
"""

import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple


class DeploymentStatsCache:
    """
    Thread-safe TTL-based cache for deployment statistics.

    Two-level cache with 2-minute staleness window:
    - Level 1: Discovered project paths (single entry)
    - Level 2: Per-artifact deployment statistics (keyed by name + type)

    Attributes:
        DEFAULT_TTL: Default time-to-live in seconds (120 = 2 minutes).
    """

    DEFAULT_TTL: int = 120  # 2 minutes

    def __init__(self, ttl: int = DEFAULT_TTL) -> None:
        """
        Initialize the cache with a configurable TTL.

        Args:
            ttl: Time-to-live in seconds for cache entries.
                 Defaults to DEFAULT_TTL (120 seconds / 2 minutes).
        """
        # Level 1: Project discovery cache (paths, timestamp)
        self._projects_cache: Optional[Tuple[List[Path], float]] = None

        # Level 2: Per-artifact stats cache (name, type) -> (stats, timestamp)
        self._stats_cache: Dict[Tuple[str, str], Tuple[Any, float]] = {}

        self._ttl = ttl
        self._lock = Lock()

    def get_discovered_projects(self) -> Optional[List[Path]]:
        """
        Get cached discovered project paths.

        Returns:
            List of project paths if cached and not expired, None otherwise.
        """
        with self._lock:
            if self._projects_cache is None:
                return None
            paths, ts = self._projects_cache
            if time.time() - ts < self._ttl:
                return paths
            # Expired - clear cache
            self._projects_cache = None
            return None

    def set_discovered_projects(self, paths: List[Path]) -> None:
        """
        Cache discovered project paths.

        Args:
            paths: List of project paths to cache.
        """
        with self._lock:
            self._projects_cache = (paths, time.time())

    def get_stats(self, name: str, artifact_type: str) -> Optional[Any]:
        """
        Get cached deployment statistics for an artifact.

        Args:
            name: Artifact name.
            artifact_type: Artifact type (e.g., "skill", "command").

        Returns:
            DeploymentStatistics object if cached and not expired, None otherwise.
        """
        key = (name, artifact_type)
        with self._lock:
            if key not in self._stats_cache:
                return None
            stats, ts = self._stats_cache[key]
            if time.time() - ts < self._ttl:
                return stats
            # Expired - remove from cache
            del self._stats_cache[key]
            return None

    def set_stats(self, name: str, artifact_type: str, stats: Any) -> None:
        """
        Cache deployment statistics for an artifact.

        Args:
            name: Artifact name.
            artifact_type: Artifact type (e.g., "skill", "command").
            stats: DeploymentStatistics object to cache.
        """
        key = (name, artifact_type)
        with self._lock:
            self._stats_cache[key] = (stats, time.time())

    def invalidate_artifact(self, name: str, artifact_type: str) -> None:
        """
        Invalidate cache for a specific artifact.

        Args:
            name: Artifact name.
            artifact_type: Artifact type.
        """
        key = (name, artifact_type)
        with self._lock:
            self._stats_cache.pop(key, None)

    def invalidate_all(self) -> None:
        """
        Clear entire cache (both levels).

        Removes all cached entries including discovered projects and
        per-artifact statistics.
        """
        with self._lock:
            self._projects_cache = None
            self._stats_cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dict with cache statistics:
            - projects_cached: Whether project discovery is cached
            - stats_entries: Number of per-artifact stats entries
            - ttl: Configured TTL in seconds
        """
        with self._lock:
            return {
                "projects_cached": self._projects_cache is not None,
                "stats_entries": len(self._stats_cache),
                "ttl": self._ttl,
            }


# Singleton instance
_cache_instance: Optional[DeploymentStatsCache] = None


def get_deployment_stats_cache() -> DeploymentStatsCache:
    """
    Get singleton cache instance.

    Returns the global DeploymentStatsCache instance, creating it on
    first access with default TTL.

    Returns:
        The singleton DeploymentStatsCache instance.
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DeploymentStatsCache()
    return _cache_instance
