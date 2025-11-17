"""Tests for caching utilities.

Tests cache manager with TTL, ETag generation, and LRU eviction.
"""

import time

import pytest

from skillmeat.api.utils.cache import CacheManager, generate_etag


class TestGenerateETag:
    """Tests for ETag generation."""

    def test_generate_etag_dict(self):
        """Test ETag generation from dictionary."""
        data = {"key": "value", "number": 42}
        etag = generate_etag(data)

        assert etag.startswith('"')
        assert etag.endswith('"')
        assert len(etag) == 18  # Quotes + 16 hex chars

    def test_generate_etag_consistent(self):
        """Test that same data produces same ETag."""
        data = {"key": "value"}
        etag1 = generate_etag(data)
        etag2 = generate_etag(data)

        assert etag1 == etag2

    def test_generate_etag_different_data(self):
        """Test that different data produces different ETags."""
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}

        etag1 = generate_etag(data1)
        etag2 = generate_etag(data2)

        assert etag1 != etag2

    def test_generate_etag_string(self):
        """Test ETag generation from string."""
        data = "test string"
        etag = generate_etag(data)

        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_generate_etag_list(self):
        """Test ETag generation from list."""
        data = [1, 2, 3, "test"]
        etag = generate_etag(data)

        assert etag.startswith('"')
        assert etag.endswith('"')


class TestCacheManager:
    """Tests for CacheManager."""

    def test_cache_manager_init(self):
        """Test cache manager initialization."""
        cache = CacheManager(default_ttl=60, max_entries=100)

        assert cache.default_ttl == 60
        assert cache.max_entries == 100
        assert len(cache._cache) == 0

    def test_set_and_get(self):
        """Test setting and getting cache entries."""
        cache = CacheManager()

        # Set data
        etag = cache.set("key1", {"data": "value"})
        assert etag is not None

        # Get data
        result = cache.get("key1")
        assert result is not None

        data, retrieved_etag = result
        assert data == {"data": "value"}
        assert retrieved_etag == etag

    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns None."""
        cache = CacheManager()

        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = CacheManager(default_ttl=1)  # 1 second TTL

        # Set data
        cache.set("key1", {"data": "value"})

        # Immediately get - should work
        result = cache.get("key1")
        assert result is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get("key1")
        assert result is None

    def test_custom_ttl(self):
        """Test setting custom TTL for entry."""
        cache = CacheManager(default_ttl=60)

        # Set with custom TTL
        cache.set("key1", {"data": "value"}, ttl=1)

        # Immediately get - should work
        result = cache.get("key1")
        assert result is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get("key1")
        assert result is None

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = CacheManager()

        # Set data
        cache.set("key1", {"data": "value"})
        assert cache.get("key1") is not None

        # Invalidate
        result = cache.invalidate("key1")
        assert result is True

        # Should be gone
        assert cache.get("key1") is None

    def test_invalidate_nonexistent(self):
        """Test invalidating non-existent key."""
        cache = CacheManager()

        result = cache.invalidate("nonexistent")
        assert result is False

    def test_invalidate_pattern(self):
        """Test pattern-based invalidation."""
        cache = CacheManager()

        # Set multiple entries
        cache.set("listings:all", {"data": "1"})
        cache.set("listings:skillmeat", {"data": "2"})
        cache.set("listing_detail:123", {"data": "3"})

        # Invalidate pattern
        count = cache.invalidate_pattern("listings:*")
        assert count == 2

        # Check what's left
        assert cache.get("listings:all") is None
        assert cache.get("listings:skillmeat") is None
        assert cache.get("listing_detail:123") is not None

    def test_clear(self):
        """Test clearing all cache entries."""
        cache = CacheManager()

        # Set multiple entries
        cache.set("key1", {"data": "1"})
        cache.set("key2", {"data": "2"})
        cache.set("key3", {"data": "3"})

        # Clear
        cache.clear()

        # All should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_lru_eviction(self):
        """Test LRU eviction when max entries reached."""
        cache = CacheManager(max_entries=3)

        # Fill cache
        cache.set("key1", {"data": "1"})
        cache.set("key2", {"data": "2"})
        cache.set("key3", {"data": "3"})

        # Access key1 to make it more recent
        cache.get("key1")

        # Add fourth entry - should evict key2 (oldest)
        cache.set("key4", {"data": "4"})

        # key2 should be evicted
        assert cache.get("key1") is not None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = CacheManager(default_ttl=1)

        # Set entries
        cache.set("key1", {"data": "1"})
        cache.set("key2", {"data": "2"})

        # Wait for expiration
        time.sleep(1.1)

        # Cleanup
        count = cache.cleanup_expired()
        assert count == 2

        # Both should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats(self):
        """Test cache statistics."""
        cache = CacheManager(default_ttl=60, max_entries=100)

        # Set some entries
        cache.set("key1", {"data": "1"})
        cache.set("key2", {"data": "2"})

        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["max_entries"] == 100
        assert stats["default_ttl"] == 60
        assert stats["active_entries"] >= 0
        assert stats["expired_entries"] >= 0

    def test_etag_consistency(self):
        """Test that ETag is consistent for same data."""
        cache = CacheManager()

        data = {"key": "value", "number": 42}

        # Set twice
        etag1 = cache.set("key1", data)
        etag2 = cache.set("key2", data)

        # ETags should be the same for same data
        assert etag1 == etag2

    def test_access_order_tracking(self):
        """Test that access order is tracked for LRU."""
        cache = CacheManager(max_entries=2)

        # Add two entries
        cache.set("key1", {"data": "1"})
        cache.set("key2", {"data": "2"})

        # Access key1 (make it more recent)
        cache.get("key1")

        # Add third entry - should evict key2
        cache.set("key3", {"data": "3"})

        assert cache.get("key1") is not None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None
