"""Tests for DeploymentStatsCache.

This module validates the thread-safe, TTL-based cache for deployment statistics.

Test Coverage:
    - Cache miss (returns None when nothing cached)
    - Cache hit (returns cached value within TTL)
    - TTL expiry (returns None after TTL expires)
    - Invalidation - single artifact and all
    - Thread safety (concurrent access doesn't corrupt data)
"""

import threading
import time
from pathlib import Path

import pytest

from skillmeat.cache.deployment_stats_cache import (
    DeploymentStatsCache,
    get_deployment_stats_cache,
)


class TestDeploymentStatsCache:
    """Test suite for DeploymentStatsCache."""

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None for stats."""
        cache = DeploymentStatsCache()
        result = cache.get_stats("nonexistent", "skill")
        assert result is None

    def test_cache_hit_returns_cached_value(self):
        """Test that cache hit returns the cached value."""
        cache = DeploymentStatsCache()
        stats_obj = {"count": 5, "projects": ["proj1", "proj2"]}

        cache.set_stats("my-skill", "skill", stats_obj)
        result = cache.get_stats("my-skill", "skill")

        assert result == stats_obj
        assert result["count"] == 5

    def test_projects_cache_miss_returns_none(self):
        """Test that projects cache miss returns None."""
        cache = DeploymentStatsCache()
        result = cache.get_discovered_projects()
        assert result is None

    def test_projects_cache_hit_returns_cached_value(self):
        """Test that projects cache hit returns the cached paths."""
        cache = DeploymentStatsCache()
        paths = [Path("/project1"), Path("/project2")]

        cache.set_discovered_projects(paths)
        result = cache.get_discovered_projects()

        assert result == paths
        assert len(result) == 2

    def test_ttl_expiry_stats(self):
        """Test that stats cache expires after TTL."""
        cache = DeploymentStatsCache(ttl=1)  # 1 second TTL
        stats_obj = {"count": 3}

        cache.set_stats("test-artifact", "skill", stats_obj)
        assert cache.get_stats("test-artifact", "skill") == stats_obj

        time.sleep(1.1)  # Wait for TTL to expire
        assert cache.get_stats("test-artifact", "skill") is None

    def test_ttl_expiry_projects(self):
        """Test that projects cache expires after TTL."""
        cache = DeploymentStatsCache(ttl=1)  # 1 second TTL
        paths = [Path("/project")]

        cache.set_discovered_projects(paths)
        assert cache.get_discovered_projects() == paths

        time.sleep(1.1)  # Wait for TTL to expire
        assert cache.get_discovered_projects() is None

    def test_invalidate_artifact(self):
        """Test invalidating a single artifact."""
        cache = DeploymentStatsCache()

        cache.set_stats("artifact-a", "skill", {"a": 1})
        cache.set_stats("artifact-b", "skill", {"b": 2})

        cache.invalidate_artifact("artifact-a", "skill")

        assert cache.get_stats("artifact-a", "skill") is None
        assert cache.get_stats("artifact-b", "skill") == {"b": 2}

    def test_invalidate_all(self):
        """Test invalidating all cached data."""
        cache = DeploymentStatsCache()

        cache.set_discovered_projects([Path("/proj")])
        cache.set_stats("artifact-x", "command", {"x": 1})
        cache.set_stats("artifact-y", "skill", {"y": 2})

        cache.invalidate_all()

        assert cache.get_discovered_projects() is None
        assert cache.get_stats("artifact-x", "command") is None
        assert cache.get_stats("artifact-y", "skill") is None

    def test_thread_safety(self):
        """Test concurrent access doesn't corrupt cache."""
        cache = DeploymentStatsCache()
        errors = []
        iterations = 100

        def writer():
            for i in range(iterations):
                cache.set_stats(f"artifact-{i}", "skill", {"val": i})

        def reader():
            for i in range(iterations):
                result = cache.get_stats(f"artifact-{i}", "skill")
                if result is not None and result.get("val") != i:
                    errors.append(f"Corruption: expected {i}, got {result}")

        def invalidator():
            for i in range(0, iterations, 10):
                cache.invalidate_artifact(f"artifact-{i}", "skill")

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=invalidator),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"

    def test_get_cache_stats(self):
        """Test cache statistics reporting."""
        cache = DeploymentStatsCache(ttl=60)

        stats = cache.get_cache_stats()
        assert stats["projects_cached"] is False
        assert stats["stats_entries"] == 0
        assert stats["ttl"] == 60

        cache.set_discovered_projects([Path("/p")])
        cache.set_stats("a", "skill", {})

        stats = cache.get_cache_stats()
        assert stats["projects_cached"] is True
        assert stats["stats_entries"] == 1


class TestGetDeploymentStatsCache:
    """Test the singleton factory function."""

    def test_returns_same_instance(self):
        """Test that factory returns the same instance."""
        instance1 = get_deployment_stats_cache()
        instance2 = get_deployment_stats_cache()
        assert instance1 is instance2

    def test_instance_is_deployment_stats_cache(self):
        """Test that factory returns correct type."""
        instance = get_deployment_stats_cache()
        assert isinstance(instance, DeploymentStatsCache)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
