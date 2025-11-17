"""Tests for marketplace cache layer."""

import time
from datetime import datetime

import pytest

from skillmeat.core.marketplace.cache import CacheEntry, MarketplaceCache
from skillmeat.core.marketplace.models import (
    ArtifactCategory,
    Listing,
    ListingPage,
    PublisherInfo,
)


@pytest.fixture
def sample_listing():
    """Create a sample listing for testing."""
    publisher = PublisherInfo(
        name="Test Publisher",
        email="test@example.com",
        verified=True,
    )

    return Listing(
        listing_id="test-123",
        name="Test Artifact",
        description="Test description",
        category=ArtifactCategory.SKILL,
        version="1.0.0",
        publisher=publisher,
        license="MIT",
        tags=["test", "example"],
        artifact_count=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        downloads=100,
        price=0.0,
        source_url="https://marketplace.example.com/test-123",
        bundle_url="https://marketplace.example.com/bundles/test-123.zip",
    )


@pytest.fixture
def sample_listing_page(sample_listing):
    """Create a sample listing page for testing."""
    return ListingPage(
        listings=[sample_listing],
        total_count=1,
        page=1,
        page_size=20,
        total_pages=1,
        has_next=False,
        has_prev=False,
    )


def test_cache_entry_expiration():
    """Test cache entry expiration logic."""
    # Create entry with 1-second TTL
    entry = CacheEntry(
        data=None,  # type: ignore
        etag="test-etag",
        timestamp=time.time(),
        ttl=1,
    )

    # Should not be expired immediately
    assert not entry.is_expired()

    # Sleep and check expiration
    time.sleep(1.1)
    assert entry.is_expired()


def test_cache_entry_age():
    """Test cache entry age calculation."""
    entry = CacheEntry(
        data=None,  # type: ignore
        etag="test-etag",
        timestamp=time.time() - 5.0,  # 5 seconds ago
        ttl=300,
    )

    age = entry.age_seconds()
    assert age >= 5
    assert age < 6


def test_cache_initialization():
    """Test cache initialization."""
    cache = MarketplaceCache(ttl=300, max_size=100)

    assert cache.ttl == 300
    assert cache.max_size == 100
    assert len(cache._cache) == 0


def test_cache_set_and_get(sample_listing_page):
    """Test basic cache set and get operations."""
    cache = MarketplaceCache(ttl=300)
    cache_key = "test-key"

    # Set data
    etag = cache.set(cache_key, sample_listing_page)
    assert etag is not None
    assert len(etag) == 64  # SHA-256 hash

    # Get data (no ETag match)
    data, returned_etag, not_modified = cache.get(cache_key, None)

    assert data is not None
    assert data.total_count == 1
    assert returned_etag == etag
    assert not not_modified


def test_cache_etag_match(sample_listing_page):
    """Test ETag matching (304 Not Modified)."""
    cache = MarketplaceCache(ttl=300)
    cache_key = "test-key"

    # Set data
    etag = cache.set(cache_key, sample_listing_page)

    # Get with matching ETag
    data, returned_etag, not_modified = cache.get(cache_key, etag)

    assert data is None  # No data on 304
    assert returned_etag == etag
    assert not_modified


def test_cache_miss():
    """Test cache miss behavior."""
    cache = MarketplaceCache(ttl=300)

    data, etag, not_modified = cache.get("nonexistent-key", None)

    assert data is None
    assert etag is None
    assert not not_modified


def test_cache_expiration(sample_listing_page):
    """Test cache expiration."""
    cache = MarketplaceCache(ttl=1)  # 1 second TTL
    cache_key = "test-key"

    # Set data
    cache.set(cache_key, sample_listing_page)

    # Wait for expiration
    time.sleep(1.1)

    # Should be cache miss
    data, etag, not_modified = cache.get(cache_key, None)

    assert data is None
    assert etag is None
    assert not not_modified


def test_cache_lru_eviction(sample_listing_page):
    """Test LRU eviction when cache is full."""
    cache = MarketplaceCache(ttl=300, max_size=3)

    # Fill cache
    etag1 = cache.set("key1", sample_listing_page)
    time.sleep(0.01)  # Ensure different timestamps
    etag2 = cache.set("key2", sample_listing_page)
    time.sleep(0.01)
    etag3 = cache.set("key3", sample_listing_page)

    # All should be in cache
    assert len(cache._cache) == 3

    # Add one more (should evict oldest)
    time.sleep(0.01)
    cache.set("key4", sample_listing_page)

    # Should have 3 entries
    assert len(cache._cache) == 3

    # key1 (oldest) should be evicted
    data, _, _ = cache.get("key1", None)
    assert data is None

    # Others should still be present
    data, _, _ = cache.get("key2", None)
    assert data is not None


def test_cache_invalidation(sample_listing_page):
    """Test cache invalidation."""
    cache = MarketplaceCache(ttl=300)

    # Set multiple entries
    cache.set("key1", sample_listing_page)
    cache.set("key2", sample_listing_page)
    cache.set("key3", sample_listing_page)

    assert len(cache._cache) == 3

    # Invalidate specific key
    cache.invalidate("key1")
    assert len(cache._cache) == 2

    # Invalidate all
    cache.invalidate()
    assert len(cache._cache) == 0


def test_cache_stats(sample_listing_page):
    """Test cache statistics."""
    cache = MarketplaceCache(ttl=1, max_size=100)

    # Set some entries
    cache.set("key1", sample_listing_page)
    cache.set("key2", sample_listing_page)

    stats = cache.get_stats()

    assert stats["total_entries"] == 2
    assert stats["expired_entries"] == 0
    assert stats["max_size"] == 100
    assert stats["ttl_seconds"] == 1

    # Wait for expiration
    time.sleep(1.1)

    stats = cache.get_stats()
    assert stats["expired_entries"] == 2


def test_cache_cleanup_expired(sample_listing_page):
    """Test cleanup of expired entries."""
    cache = MarketplaceCache(ttl=1)

    # Set entries
    cache.set("key1", sample_listing_page)
    cache.set("key2", sample_listing_page)

    assert len(cache._cache) == 2

    # Wait for expiration
    time.sleep(1.1)

    # Cleanup
    removed = cache.cleanup_expired()

    assert removed == 2
    assert len(cache._cache) == 0


def test_generate_cache_key():
    """Test cache key generation."""
    # Same params should generate same key
    key1 = MarketplaceCache.generate_cache_key(page=1, tags="python,ml")
    key2 = MarketplaceCache.generate_cache_key(page=1, tags="python,ml")
    assert key1 == key2

    # Different params should generate different keys
    key3 = MarketplaceCache.generate_cache_key(page=2, tags="python,ml")
    assert key1 != key3

    # Order should not matter (sorted internally)
    key4 = MarketplaceCache.generate_cache_key(tags="python,ml", page=1)
    assert key1 == key4


def test_cache_custom_ttl(sample_listing_page):
    """Test custom TTL per entry."""
    cache = MarketplaceCache(ttl=300)  # Default 300s

    # Set with custom TTL
    cache.set("key1", sample_listing_page, ttl=1)

    # Should not be expired immediately
    data, _, _ = cache.get("key1", None)
    assert data is not None

    # Wait for custom TTL expiration
    time.sleep(1.1)

    # Should be expired
    data, _, _ = cache.get("key1", None)
    assert data is None


def test_cache_thread_safety(sample_listing_page):
    """Test thread safety of cache operations."""
    import threading

    cache = MarketplaceCache(ttl=300, max_size=100)
    errors = []

    def set_operation(key):
        try:
            cache.set(f"key-{key}", sample_listing_page)
        except Exception as e:
            errors.append(e)

    def get_operation(key):
        try:
            cache.get(f"key-{key}", None)
        except Exception as e:
            errors.append(e)

    # Create threads for concurrent access
    threads = []
    for i in range(10):
        t1 = threading.Thread(target=set_operation, args=(i,))
        t2 = threading.Thread(target=get_operation, args=(i,))
        threads.extend([t1, t2])

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Should have no errors
    assert len(errors) == 0
