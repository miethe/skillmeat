#!/usr/bin/env python3
"""Demonstration of MetadataCache usage.

This script demonstrates the key features of the MetadataCache class:
- Basic set/get operations
- TTL expiration
- Cache statistics
- Cleanup operations
- Thread safety
"""

import time
from skillmeat.core.cache import MetadataCache


def demo_basic_usage():
    """Demonstrate basic cache operations."""
    print("=== Basic Cache Usage ===\n")

    cache = MetadataCache(ttl_seconds=5)

    # Store some GitHub metadata
    metadata = {
        "title": "Canvas Design Skill",
        "description": "Create beautiful visual art",
        "version": "2.1.0",
        "authors": ["Anthropic"],
    }

    cache.set("anthropics/skills/canvas-design", metadata)
    print("Stored metadata for 'anthropics/skills/canvas-design'")

    # Retrieve it
    result = cache.get("anthropics/skills/canvas-design")
    if result:
        print(f"Retrieved: {result['title']} v{result['version']}")

    print(f"Cache stats: {cache.stats()}\n")


def demo_ttl_expiration():
    """Demonstrate TTL expiration."""
    print("=== TTL Expiration ===\n")

    cache = MetadataCache(ttl_seconds=2)

    cache.set("test-key", {"value": "test"})
    print("Stored entry with 2-second TTL")

    # Immediate retrieval works
    result = cache.get("test-key")
    print(f"Immediate get: {'Hit' if result else 'Miss'}")

    # Wait for expiration
    print("Waiting 2.5 seconds for expiration...")
    time.sleep(2.5)

    # Now it should be expired
    result = cache.get("test-key")
    print(f"After expiration: {'Hit' if result else 'Miss'}")

    print(f"Cache stats: {cache.stats()}\n")


def demo_cache_statistics():
    """Demonstrate cache statistics tracking."""
    print("=== Cache Statistics ===\n")

    cache = MetadataCache()

    # Generate some cache activity
    for i in range(5):
        cache.set(f"key-{i}", {"value": i})

    # Mix of hits and misses
    cache.get("key-0")  # Hit
    cache.get("key-1")  # Hit
    cache.get("key-99")  # Miss
    cache.get("key-2")  # Hit
    cache.get("key-100")  # Miss

    stats = cache.stats()
    print(f"Total entries: {stats['size']}")
    print(f"Cache hits: {stats['hits']}")
    print(f"Cache misses: {stats['misses']}")
    hit_rate = stats["hits"] / (stats["hits"] + stats["misses"]) * 100
    print(f"Hit rate: {hit_rate:.1f}%\n")


def demo_cleanup():
    """Demonstrate cache cleanup."""
    print("=== Cache Cleanup ===\n")

    cache = MetadataCache(ttl_seconds=2)

    # Add several entries
    for i in range(5):
        cache.set(f"key-{i}", {"value": i})

    print(f"Added 5 entries, cache size: {len(cache)}")

    # Wait for expiration
    print("Waiting 2.5 seconds for entries to expire...")
    time.sleep(2.5)

    # Add fresh entries
    for i in range(5, 8):
        cache.set(f"key-{i}", {"value": i})

    print(f"Added 3 fresh entries, cache size: {len(cache)}")

    # Cleanup expired entries
    removed = cache.cleanup()
    print(f"Cleanup removed {removed} expired entries")
    print(f"Current cache size: {len(cache)}\n")


def demo_invalidation():
    """Demonstrate cache invalidation."""
    print("=== Cache Invalidation ===\n")

    cache = MetadataCache()

    # Add entries
    cache.set("key-1", {"value": 1})
    cache.set("key-2", {"value": 2})
    cache.set("key-3", {"value": 3})

    print(f"Added 3 entries, cache size: {len(cache)}")

    # Invalidate specific entry
    cache.invalidate("key-2")
    print("Invalidated 'key-2'")
    print(f"Cache size after invalidation: {len(cache)}")

    # Clear entire cache
    cache.clear()
    print("Cleared entire cache")
    print(f"Cache size after clear: {len(cache)}")
    print(f"Stats after clear: {cache.stats()}\n")


if __name__ == "__main__":
    print("MetadataCache Demonstration\n")
    print("=" * 50)
    print()

    demo_basic_usage()
    demo_ttl_expiration()
    demo_cache_statistics()
    demo_cleanup()
    demo_invalidation()

    print("=" * 50)
    print("\nDemonstration complete!")
