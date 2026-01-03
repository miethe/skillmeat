"""Tests for GitHub file cache utilities.

Tests the GitHubFileCache class including LRU eviction, TTL expiration,
thread safety, and key builder functions.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from skillmeat.api.utils.github_cache import (
    DEFAULT_CONTENT_TTL,
    DEFAULT_TREE_TTL,
    GitHubFileCache,
    build_content_key,
    build_tree_key,
    get_github_file_cache,
    reset_github_file_cache,
)


class TestGitHubFileCache:
    """Tests for GitHubFileCache class."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_github_file_cache()

    def test_basic_get_set(self) -> None:
        """Test basic get and set operations."""
        cache: GitHubFileCache[dict[str, Any]] = GitHubFileCache(max_entries=100)

        # Set a value
        cache.set("key1", {"data": "value1"}, ttl_seconds=300)

        # Get the value
        result = cache.get("key1")
        assert result is not None
        assert result["data"] == "value1"

    def test_get_missing_key(self) -> None:
        """Test get returns None for missing key."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiration(self) -> None:
        """Test that entries expire after TTL."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        # Set with very short TTL
        cache.set("key1", "value1", ttl_seconds=1)

        # Verify it's there
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("key1") is None

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        cache: GitHubFileCache[int] = GitHubFileCache(max_entries=3)

        # Fill the cache
        cache.set("key1", 1, ttl_seconds=300)
        cache.set("key2", 2, ttl_seconds=300)
        cache.set("key3", 3, ttl_seconds=300)

        # Access key1 to make it recently used
        cache.get("key1")

        # Add a new entry - should evict key2 (least recently used)
        cache.set("key4", 4, ttl_seconds=300)

        # key2 should be evicted
        assert cache.get("key2") is None
        # key1, key3, key4 should still be there
        assert cache.get("key1") == 1
        assert cache.get("key3") == 3
        assert cache.get("key4") == 4

    def test_delete(self) -> None:
        """Test delete operation."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        cache.set("key1", "value1", ttl_seconds=300)
        assert cache.get("key1") == "value1"

        # Delete the entry
        result = cache.delete("key1")
        assert result is True

        # Should be gone
        assert cache.get("key1") is None

        # Delete non-existent key
        result = cache.delete("nonexistent")
        assert result is False

    def test_clear(self) -> None:
        """Test clear operation."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        cache.set("key1", "value1", ttl_seconds=300)
        cache.set("key2", "value2", ttl_seconds=300)

        assert len(cache) == 2

        cache.clear()

        assert len(cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self) -> None:
        """Test cleanup_expired removes only expired entries."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        # Set entries with different TTLs
        cache.set("short", "value1", ttl_seconds=1)
        cache.set("long", "value2", ttl_seconds=300)

        # Wait for short TTL to expire
        time.sleep(1.1)

        # Cleanup expired entries
        removed = cache.cleanup_expired()
        assert removed == 1

        # Short should be gone, long should remain
        assert cache.get("short") is None
        assert cache.get("long") == "value2"

    def test_stats(self) -> None:
        """Test statistics tracking."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        cache.set("key1", "value1", ttl_seconds=300)

        # Cache hit
        cache.get("key1")
        # Cache miss
        cache.get("nonexistent")

        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["max_entries"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_overwrite_existing_key(self) -> None:
        """Test that setting an existing key overwrites it."""
        cache: GitHubFileCache[str] = GitHubFileCache(max_entries=100)

        cache.set("key1", "value1", ttl_seconds=300)
        cache.set("key1", "value2", ttl_seconds=600)

        assert cache.get("key1") == "value2"
        assert len(cache) == 1

    def test_thread_safety(self) -> None:
        """Test thread-safe concurrent access."""
        cache: GitHubFileCache[int] = GitHubFileCache(max_entries=1000)
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                for i in range(100):
                    key = f"thread-{thread_id}-key-{i}"
                    cache.set(key, i, ttl_seconds=300)
                    result = cache.get(key)
                    assert result == i
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in futures:
                future.result()

        assert len(errors) == 0
        assert len(cache) <= 1000  # Should not exceed max entries


class TestCacheKeyBuilders:
    """Tests for cache key builder functions."""

    def test_build_tree_key(self) -> None:
        """Test tree key format."""
        key = build_tree_key("src-123", "skills/canvas", "abc123")
        assert key == "tree:src-123:skills/canvas:abc123"

    def test_build_tree_key_with_nested_path(self) -> None:
        """Test tree key with deeply nested path."""
        key = build_tree_key("src-1", "path/to/deep/artifact", "sha456")
        assert key == "tree:src-1:path/to/deep/artifact:sha456"

    def test_build_content_key(self) -> None:
        """Test content key format."""
        key = build_content_key("src-123", "skills/canvas", "SKILL.md", "def456")
        assert key == "content:src-123:skills/canvas:SKILL.md:def456"

    def test_build_content_key_with_nested_file(self) -> None:
        """Test content key with nested file path."""
        key = build_content_key("src-1", "skills/tool", "src/lib/utils.py", "sha789")
        assert key == "content:src-1:skills/tool:src/lib/utils.py:sha789"


class TestDefaultTTLConstants:
    """Tests for default TTL constants."""

    def test_default_tree_ttl(self) -> None:
        """Test default tree TTL is 1 hour."""
        assert DEFAULT_TREE_TTL == 3600  # 1 hour

    def test_default_content_ttl(self) -> None:
        """Test default content TTL is 2 hours."""
        assert DEFAULT_CONTENT_TTL == 7200  # 2 hours


class TestGlobalCacheInstance:
    """Tests for global cache singleton."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_github_file_cache()

    def test_get_github_file_cache_singleton(self) -> None:
        """Test that get_github_file_cache returns the same instance."""
        cache1 = get_github_file_cache()
        cache2 = get_github_file_cache()

        assert cache1 is cache2

    def test_get_github_file_cache_custom_max_entries(self) -> None:
        """Test that max_entries is used on first call."""
        cache = get_github_file_cache(max_entries=500)
        assert cache.max_entries == 500

        # Subsequent calls should return same instance, ignoring param
        cache2 = get_github_file_cache(max_entries=2000)
        assert cache2 is cache
        assert cache2.max_entries == 500

    def test_reset_github_file_cache(self) -> None:
        """Test that reset creates a new instance."""
        cache1 = get_github_file_cache(max_entries=100)
        cache1.set("key1", "value1", ttl_seconds=300)

        reset_github_file_cache()

        cache2 = get_github_file_cache(max_entries=200)
        assert cache2 is not cache1
        assert cache2.max_entries == 200
        assert cache2.get("key1") is None  # Old data should be gone

    def test_thread_safe_singleton_initialization(self) -> None:
        """Test thread-safe singleton initialization."""
        results: list[GitHubFileCache[Any]] = []
        errors: list[Exception] = []

        def get_cache() -> None:
            try:
                cache = get_github_file_cache()
                results.append(cache)
            except Exception as e:
                errors.append(e)

        # Try to initialize from multiple threads simultaneously
        threads = [threading.Thread(target=get_cache) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All results should be the same instance
        assert all(r is results[0] for r in results)
