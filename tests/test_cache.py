"""Tests for MetadataCache."""

import threading
import time
from unittest.mock import patch

import pytest

from skillmeat.core.cache import MetadataCache


class TestMetadataCache:
    """Test suite for MetadataCache class."""

    def test_init_default_ttl(self):
        """Test cache initialization with default TTL."""
        cache = MetadataCache()
        assert cache.ttl_seconds == 3600
        assert len(cache) == 0
        assert cache.stats() == {"hits": 0, "misses": 0, "size": 0}

    def test_init_custom_ttl(self):
        """Test cache initialization with custom TTL."""
        cache = MetadataCache(ttl_seconds=7200)
        assert cache.ttl_seconds == 7200

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = MetadataCache()
        test_data = {"title": "Canvas", "description": "A design skill"}

        cache.set("test-key", test_data)
        result = cache.get("test-key")

        assert result == test_data
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 0
        assert cache.stats()["size"] == 1

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = MetadataCache()
        result = cache.get("nonexistent")

        assert result is None
        assert cache.stats()["hits"] == 0
        assert cache.stats()["misses"] == 1

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = MetadataCache(ttl_seconds=1)
        test_data = {"title": "Test"}

        cache.set("test-key", test_data)

        # Should still be valid
        result = cache.get("test-key")
        assert result == test_data
        assert cache.stats()["hits"] == 1

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired and removed
        result = cache.get("test-key")
        assert result is None
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 1
        assert cache.stats()["size"] == 0

    def test_set_overwrites_existing(self):
        """Test that set overwrites existing entries."""
        cache = MetadataCache()

        cache.set("key", {"version": 1})
        cache.set("key", {"version": 2})

        result = cache.get("key")
        assert result == {"version": 2}
        assert len(cache) == 1

    def test_invalidate(self):
        """Test invalidating specific cache entries."""
        cache = MetadataCache()

        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})

        cache.invalidate("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == {"data": "test2"}
        assert len(cache) == 1

    def test_invalidate_nonexistent(self):
        """Test invalidating a key that doesn't exist (should be no-op)."""
        cache = MetadataCache()

        # Should not raise an error
        cache.invalidate("nonexistent")
        assert len(cache) == 0

    def test_clear(self):
        """Test clearing the entire cache."""
        cache = MetadataCache()

        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        cache.get("key1")  # Generate a hit
        cache.get("nonexistent")  # Generate a miss

        assert len(cache) == 2
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 1

        cache.clear()

        assert len(cache) == 0
        assert cache.stats() == {"hits": 0, "misses": 0, "size": 0}

    def test_cleanup_expired_entries(self):
        """Test cleanup removes only expired entries."""
        cache = MetadataCache(ttl_seconds=1)

        # Add entries at different times
        cache.set("stale", {"data": "stale"})
        time.sleep(1.1)  # Wait for first entry to expire
        cache.set("fresh", {"data": "fresh"})  # Add fresh entry

        removed = cache.cleanup()

        assert removed == 1  # Only the stale entry was removed
        assert cache.get("fresh") == {"data": "fresh"}  # Fresh entry still valid
        assert len(cache) == 1

    def test_cleanup_no_expired(self):
        """Test cleanup when no entries are expired."""
        cache = MetadataCache(ttl_seconds=3600)

        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})

        removed = cache.cleanup()

        assert removed == 0
        assert len(cache) == 2

    def test_thread_safety(self):
        """Test that cache is thread-safe."""
        cache = MetadataCache()
        errors = []

        def worker(thread_id: int):
            try:
                for i in range(100):
                    key = f"thread-{thread_id}-key-{i}"
                    cache.set(key, {"thread": thread_id, "iteration": i})
                    result = cache.get(key)
                    if result is None or result["thread"] != thread_id:
                        errors.append(f"Thread {thread_id} got wrong data")
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(cache) == 1000  # 10 threads * 100 iterations

    def test_len_operator(self):
        """Test __len__ operator."""
        cache = MetadataCache()

        assert len(cache) == 0

        cache.set("key1", {"data": 1})
        assert len(cache) == 1

        cache.set("key2", {"data": 2})
        assert len(cache) == 2

        cache.invalidate("key1")
        assert len(cache) == 1

    def test_stats_accuracy(self):
        """Test that stats are accurately tracked."""
        cache = MetadataCache()

        # Initial state
        stats = cache.stats()
        assert stats == {"hits": 0, "misses": 0, "size": 0}

        # Add and retrieve
        cache.set("key1", {"data": 1})
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        cache.get("key1")  # Hit

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cache_with_complex_data(self):
        """Test caching complex nested data structures."""
        cache = MetadataCache()

        complex_data = {
            "title": "Complex Skill",
            "description": "A complex skill with nested data",
            "metadata": {
                "version": "1.0.0",
                "authors": ["Alice", "Bob"],
                "tags": ["design", "canvas", "art"],
            },
            "files": [
                {"path": "SKILL.md", "size": 1024},
                {"path": "script.py", "size": 2048},
            ],
        }

        cache.set("complex-key", complex_data)
        result = cache.get("complex-key")

        assert result == complex_data
        assert result["metadata"]["authors"] == ["Alice", "Bob"]
        assert len(result["files"]) == 2

    def test_multiple_gets_same_key(self):
        """Test that multiple gets increment hits correctly."""
        cache = MetadataCache()

        cache.set("key", {"data": "test"})

        for _ in range(5):
            result = cache.get("key")
            assert result == {"data": "test"}

        assert cache.stats()["hits"] == 5
        assert cache.stats()["misses"] == 0

    def test_expired_entry_removed_on_get(self):
        """Test that expired entries are removed when accessed."""
        cache = MetadataCache(ttl_seconds=1)

        cache.set("key", {"data": "test"})
        assert len(cache) == 1

        time.sleep(1.1)

        # Accessing expired entry should remove it
        result = cache.get("key")
        assert result is None
        assert len(cache) == 0

    def test_cleanup_multiple_expired(self):
        """Test cleanup removes all expired entries."""
        cache = MetadataCache(ttl_seconds=1)

        for i in range(5):
            cache.set(f"key-{i}", {"data": i})

        time.sleep(1.1)

        removed = cache.cleanup()
        assert removed == 5
        assert len(cache) == 0
