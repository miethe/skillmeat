"""Unit tests for CollectionCountCache.

Tests cover basic operations, TTL expiration, edge cases, singleton behavior,
and thread safety.
"""

import pytest
import time
import threading
from typing import Set
from skillmeat.cache.collection_cache import CollectionCountCache, get_collection_count_cache


class TestCollectionCountCache:
    """Test suite for CollectionCountCache."""

    # =========================================================================
    # Basic Operations
    # =========================================================================

    def test_get_counts_empty_cache(self) -> None:
        """Test get_counts on empty cache returns empty dict and all IDs as missing."""
        cache = CollectionCountCache()
        collection_ids = {"col-1", "col-2", "col-3"}

        cached, missing = cache.get_counts(collection_ids)

        assert cached == {}, "Empty cache should return empty cached dict"
        assert missing == collection_ids, "All IDs should be marked as missing"

    def test_set_and_get_counts(self) -> None:
        """Test setting counts and retrieving them."""
        cache = CollectionCountCache()
        counts_to_set = {"col-1": 5, "col-2": 10, "col-3": 0}

        cache.set_counts(counts_to_set)
        cached, missing = cache.get_counts({"col-1", "col-2", "col-3"})

        assert cached == counts_to_set, "Cached counts should match set counts"
        assert missing == set(), "No IDs should be missing"

    def test_invalidate_single(self) -> None:
        """Test invalidate removes specific entry."""
        cache = CollectionCountCache()
        cache.set_counts({"col-1": 5, "col-2": 10, "col-3": 15})

        cache.invalidate("col-2")
        cached, missing = cache.get_counts({"col-1", "col-2", "col-3"})

        assert cached == {"col-1": 5, "col-3": 15}, "col-2 should be removed"
        assert missing == {"col-2"}, "Only col-2 should be missing"

    def test_invalidate_all(self) -> None:
        """Test invalidate_all clears entire cache."""
        cache = CollectionCountCache()
        cache.set_counts({"col-1": 5, "col-2": 10, "col-3": 15})

        cache.invalidate_all()
        cached, missing = cache.get_counts({"col-1", "col-2", "col-3"})

        assert cached == {}, "Cache should be empty after invalidate_all"
        assert missing == {"col-1", "col-2", "col-3"}, "All IDs should be missing"

    # =========================================================================
    # TTL Expiration
    # =========================================================================

    def test_ttl_expiration(self) -> None:
        """Test entries expire after TTL."""
        cache = CollectionCountCache(ttl=0.1)  # 100ms TTL
        cache.set_counts({"col-1": 5, "col-2": 10})

        # Immediate read should hit cache
        cached, missing = cache.get_counts({"col-1", "col-2"})
        assert cached == {"col-1": 5, "col-2": 10}
        assert missing == set()

        # Wait for expiration
        time.sleep(0.15)

        # After expiration, should be missing
        cached, missing = cache.get_counts({"col-1", "col-2"})
        assert cached == {}, "Expired entries should not be in cache"
        assert missing == {"col-1", "col-2"}, "Expired entries should be missing"

    def test_partial_expiration(self) -> None:
        """Test scenario where some entries expired, some valid."""
        cache = CollectionCountCache(ttl=0.2)  # 200ms TTL

        # Set first batch
        cache.set_counts({"col-1": 5, "col-2": 10})

        # Wait 100ms
        time.sleep(0.1)

        # Set second batch (fresh timestamp)
        cache.set_counts({"col-3": 15, "col-4": 20})

        # Wait another 120ms (total 220ms from first batch, 120ms from second)
        time.sleep(0.12)

        # First batch should be expired, second batch still valid
        cached, missing = cache.get_counts({"col-1", "col-2", "col-3", "col-4"})

        assert "col-1" not in cached, "col-1 should be expired"
        assert "col-2" not in cached, "col-2 should be expired"
        assert cached.get("col-3") == 15, "col-3 should still be cached"
        assert cached.get("col-4") == 20, "col-4 should still be cached"
        assert missing == {"col-1", "col-2"}, "Only expired entries should be missing"

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_get_empty_set(self) -> None:
        """Test get_counts with empty input set."""
        cache = CollectionCountCache()
        cache.set_counts({"col-1": 5})

        cached, missing = cache.get_counts(set())

        assert cached == {}, "Empty input should return empty cached dict"
        assert missing == set(), "Empty input should return empty missing set"

    def test_invalidate_nonexistent(self) -> None:
        """Test invalidating a key that doesn't exist doesn't error."""
        cache = CollectionCountCache()
        cache.set_counts({"col-1": 5})

        # Should not raise exception
        cache.invalidate("col-nonexistent")

        # Existing entry should still be there
        cached, missing = cache.get_counts({"col-1"})
        assert cached == {"col-1": 5}

    def test_get_stats(self) -> None:
        """Test get_stats returns correct size and ttl."""
        ttl = 42
        cache = CollectionCountCache(ttl=ttl)

        # Empty cache
        stats = cache.get_stats()
        assert stats["size"] == 0, "Empty cache should have size 0"
        assert stats["ttl"] == ttl, f"TTL should be {ttl}"

        # Add entries
        cache.set_counts({"col-1": 5, "col-2": 10, "col-3": 15})
        stats = cache.get_stats()
        assert stats["size"] == 3, "Cache should have 3 entries"
        assert stats["ttl"] == ttl, f"TTL should still be {ttl}"

        # Invalidate one
        cache.invalidate("col-2")
        stats = cache.get_stats()
        assert stats["size"] == 2, "Cache should have 2 entries after invalidation"

    def test_overwrite_existing_entry(self) -> None:
        """Test that setting a count for existing ID overwrites it."""
        cache = CollectionCountCache()

        # Set initial value
        cache.set_counts({"col-1": 5})
        cached, _ = cache.get_counts({"col-1"})
        assert cached["col-1"] == 5

        # Overwrite with new value
        cache.set_counts({"col-1": 99})
        cached, _ = cache.get_counts({"col-1"})
        assert cached["col-1"] == 99, "New value should overwrite old value"

    # =========================================================================
    # Singleton Behavior
    # =========================================================================

    def test_singleton_returns_same_instance(self) -> None:
        """Test get_collection_count_cache returns same instance."""
        instance1 = get_collection_count_cache()
        instance2 = get_collection_count_cache()

        assert instance1 is instance2, "Singleton should return same instance"

        # Verify they share state
        instance1.set_counts({"singleton-test": 42})
        cached, _ = instance2.get_counts({"singleton-test"})
        assert cached["singleton-test"] == 42, "Instances should share state"

    # =========================================================================
    # Thread Safety
    # =========================================================================

    def test_concurrent_access(self) -> None:
        """Test multiple threads can read/write without errors."""
        cache = CollectionCountCache()
        num_threads = 10
        iterations_per_thread = 50
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            """Worker function that reads and writes to cache."""
            try:
                for i in range(iterations_per_thread):
                    col_id = f"col-{thread_id}-{i}"
                    # Set count
                    cache.set_counts({col_id: i})
                    # Read count
                    cached, missing = cache.get_counts({col_id})
                    # Should be in cache immediately
                    assert col_id in cached or col_id in missing
                    # Invalidate
                    cache.invalidate(col_id)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Check no errors occurred
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"

    def test_concurrent_stats_access(self) -> None:
        """Test get_stats is thread-safe during concurrent modifications."""
        cache = CollectionCountCache()
        num_threads = 5
        errors: list[Exception] = []

        def stats_reader() -> None:
            """Read stats repeatedly."""
            try:
                for _ in range(100):
                    stats = cache.get_stats()
                    assert "size" in stats
                    assert "ttl" in stats
            except Exception as e:
                errors.append(e)

        def cache_modifier(thread_id: int) -> None:
            """Modify cache repeatedly."""
            try:
                for i in range(50):
                    cache.set_counts({f"col-{thread_id}-{i}": i})
            except Exception as e:
                errors.append(e)

        # Mix of stat readers and cache modifiers
        threads = [
            threading.Thread(target=stats_reader)
            for _ in range(num_threads)
        ] + [
            threading.Thread(target=cache_modifier, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent stats access caused errors: {errors}"

    def test_zero_count_value(self) -> None:
        """Test that zero is a valid count value."""
        cache = CollectionCountCache()

        cache.set_counts({"col-empty": 0, "col-full": 100})
        cached, missing = cache.get_counts({"col-empty", "col-full"})

        assert cached["col-empty"] == 0, "Zero should be a valid cached value"
        assert cached["col-full"] == 100
        assert missing == set()
