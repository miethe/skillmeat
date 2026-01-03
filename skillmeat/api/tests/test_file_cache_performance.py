"""Performance tests for file content caching.

Validates that the caching strategy achieves the performance targets:
- Cache hit rate >70%
- File tree load <3s
- Content load <2s (cached)

These tests mock the GitHub API to avoid external dependencies and focus
on testing the cache layer behavior.
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

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


# =============================================================================
# Performance Thresholds
# =============================================================================

# Cache performance targets
CACHE_HIT_RATE_TARGET = 0.70  # 70% minimum hit rate
FILE_TREE_LOAD_THRESHOLD = 3.0  # 3 seconds max for file tree
CONTENT_LOAD_CACHED_THRESHOLD = 2.0  # 2 seconds max for cached content
CONTENT_LOAD_UNCACHED_THRESHOLD = 5.0  # 5 seconds max for uncached content


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset global cache before each test."""
    reset_github_file_cache()
    yield
    reset_github_file_cache()


@pytest.fixture
def mock_tree_data() -> list[dict[str, Any]]:
    """Create mock file tree data for testing."""
    return [
        {"path": "skills/canvas/SKILL.md", "type": "blob", "size": 1234, "sha": "abc123"},
        {"path": "skills/canvas/src/index.ts", "type": "blob", "size": 5678, "sha": "def456"},
        {"path": "skills/canvas/src/utils.ts", "type": "blob", "size": 2345, "sha": "ghi789"},
        {"path": "skills/canvas/README.md", "type": "blob", "size": 890, "sha": "jkl012"},
        {"path": "skills/canvas/package.json", "type": "blob", "size": 456, "sha": "mno345"},
    ]


@pytest.fixture
def mock_content_data() -> dict[str, Any]:
    """Create mock file content data for testing."""
    return {
        "content": "# Test Skill\n\nThis is a test skill for performance testing.",
        "encoding": "base64",
        "size": 56,
        "sha": "abc123",
        "name": "SKILL.md",
        "path": "skills/canvas/SKILL.md",
        "is_binary": False,
    }


@pytest.fixture
def populated_cache(mock_tree_data: list[dict], mock_content_data: dict) -> GitHubFileCache:
    """Create a cache pre-populated with test data."""
    cache = get_github_file_cache()

    # Add tree data
    tree_key = build_tree_key("test-source", "skills/canvas", "abc123")
    cache.set(tree_key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)

    # Add content data
    content_key = build_content_key("test-source", "skills/canvas", "SKILL.md", "abc123")
    cache.set(content_key, mock_content_data, ttl_seconds=DEFAULT_CONTENT_TTL)

    return cache


# =============================================================================
# Cache Hit Rate Tests
# =============================================================================


class TestCacheHitRate:
    """Tests for cache hit rate performance."""

    def test_cache_hit_rate_exceeds_70_percent_for_tree_requests(
        self,
        mock_tree_data: list[dict],
    ) -> None:
        """Verify cache hit rate exceeds 70% for repeated file tree requests.

        First request is a cache miss, remaining 99 should be cache hits.
        Expected hit rate: 99/100 = 99%
        """
        cache = get_github_file_cache()
        tree_key = build_tree_key("perf-test-source", "skills/canvas", "sha123")

        # Prime the cache (first request - cache miss)
        cache.set(tree_key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)

        # Make 100 requests for the same resource
        for _ in range(100):
            result = cache.get(tree_key)
            assert result is not None, "Expected cache hit"

        # Get statistics
        stats = cache.stats()
        hit_rate = stats["hit_rate"] / 100  # Convert percentage to decimal

        assert hit_rate >= CACHE_HIT_RATE_TARGET, (
            f"Cache hit rate {hit_rate:.2%} below {CACHE_HIT_RATE_TARGET:.0%} target"
        )

    def test_cache_hit_rate_exceeds_70_percent_for_content_requests(
        self,
        mock_content_data: dict,
    ) -> None:
        """Verify cache hit rate exceeds 70% for repeated content requests.

        First request is a cache miss, remaining 99 should be cache hits.
        Expected hit rate: 99/100 = 99%
        """
        cache = get_github_file_cache()
        content_key = build_content_key(
            "perf-test-source", "skills/canvas", "SKILL.md", "sha123"
        )

        # Prime the cache (first request - cache miss)
        cache.set(content_key, mock_content_data, ttl_seconds=DEFAULT_CONTENT_TTL)

        # Make 100 requests for the same resource
        for _ in range(100):
            result = cache.get(content_key)
            assert result is not None, "Expected cache hit"

        # Get statistics
        stats = cache.stats()
        hit_rate = stats["hit_rate"] / 100  # Convert percentage to decimal

        assert hit_rate >= CACHE_HIT_RATE_TARGET, (
            f"Cache hit rate {hit_rate:.2%} below {CACHE_HIT_RATE_TARGET:.0%} target"
        )

    def test_mixed_request_pattern_maintains_hit_rate(
        self,
        mock_tree_data: list[dict],
        mock_content_data: dict,
    ) -> None:
        """Verify hit rate is maintained with mixed tree and content requests.

        Simulates realistic usage pattern where users browse file trees
        and view file contents in an interleaved pattern.
        """
        cache = get_github_file_cache()

        # Set up multiple cached resources
        resources = []
        for i in range(5):
            tree_key = build_tree_key(f"source-{i}", f"skills/skill-{i}", f"sha{i}")
            content_key = build_content_key(
                f"source-{i}", f"skills/skill-{i}", "SKILL.md", f"sha{i}"
            )

            cache.set(tree_key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)
            cache.set(content_key, mock_content_data, ttl_seconds=DEFAULT_CONTENT_TTL)

            resources.append((tree_key, content_key))

        # Simulate mixed access pattern (100 total requests)
        import random

        random.seed(42)  # Reproducible randomness
        for _ in range(100):
            tree_key, content_key = random.choice(resources)
            # Alternate between tree and content requests
            if random.random() < 0.5:
                cache.get(tree_key)
            else:
                cache.get(content_key)

        stats = cache.stats()
        hit_rate = stats["hit_rate"] / 100

        assert hit_rate >= CACHE_HIT_RATE_TARGET, (
            f"Mixed request hit rate {hit_rate:.2%} below {CACHE_HIT_RATE_TARGET:.0%}"
        )

    def test_cache_eviction_impact_on_hit_rate(self, mock_tree_data: list[dict]) -> None:
        """Test cache hit rate when LRU eviction occurs.

        With a small cache size, verify that frequently accessed items
        maintain a good hit rate while infrequently accessed items are evicted.
        """
        # Use a small cache to force evictions
        reset_github_file_cache()
        cache = GitHubFileCache(max_entries=10)

        # Add 10 items (fills cache)
        for i in range(10):
            key = build_tree_key(f"source-{i}", "path", "sha")
            cache.set(key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)

        # Access first 5 items frequently (10 times each)
        frequent_keys = [build_tree_key(f"source-{i}", "path", "sha") for i in range(5)]
        for _ in range(10):
            for key in frequent_keys:
                result = cache.get(key)
                assert result is not None

        # Add 5 new items (should evict least recently used)
        for i in range(10, 15):
            key = build_tree_key(f"source-{i}", "path", "sha")
            cache.set(key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)

        # Verify frequently accessed items are still cached
        for key in frequent_keys:
            result = cache.get(key)
            assert result is not None, f"Expected frequently accessed key to be cached: {key}"

        stats = cache.stats()
        hit_rate = stats["hit_rate"] / 100

        # With frequent access pattern, hit rate should remain high
        assert hit_rate >= CACHE_HIT_RATE_TARGET, (
            f"Hit rate after eviction {hit_rate:.2%} below {CACHE_HIT_RATE_TARGET:.0%}"
        )


# =============================================================================
# Load Time Tests
# =============================================================================


class TestFileTreeLoadTime:
    """Tests for file tree load time performance."""

    def test_cached_file_tree_load_under_threshold(
        self,
        populated_cache: GitHubFileCache,
    ) -> None:
        """Verify cached file tree loads in under 3 seconds.

        With cache already populated, retrieval should be nearly instant.
        """
        cache = populated_cache
        tree_key = build_tree_key("test-source", "skills/canvas", "abc123")

        # Measure cached request time
        start = time.perf_counter()
        result = cache.get(tree_key)
        duration = time.perf_counter() - start

        assert result is not None, "Expected cache hit"
        assert duration < FILE_TREE_LOAD_THRESHOLD, (
            f"Cached file tree load took {duration:.4f}s, "
            f"exceeds {FILE_TREE_LOAD_THRESHOLD}s target"
        )

        # In practice, cached loads should be <1ms
        assert duration < 0.01, f"Cached load unexpectedly slow: {duration:.4f}s"

    def test_cached_file_tree_load_consistency(
        self,
        populated_cache: GitHubFileCache,
    ) -> None:
        """Verify cached file tree load time is consistent across requests.

        Run multiple iterations and verify no significant outliers.
        """
        cache = populated_cache
        tree_key = build_tree_key("test-source", "skills/canvas", "abc123")

        durations = []
        for _ in range(100):
            start = time.perf_counter()
            result = cache.get(tree_key)
            duration = time.perf_counter() - start
            durations.append(duration)

            assert result is not None

        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        # All requests should be under threshold
        assert max_duration < FILE_TREE_LOAD_THRESHOLD, (
            f"Max load time {max_duration:.4f}s exceeds threshold"
        )

        # Average should be well under threshold (cache is fast)
        assert avg_duration < 0.001, f"Avg load time {avg_duration:.6f}s unexpectedly high"

        # Verify consistency (no extreme outliers)
        variance = max_duration - min_duration
        assert variance < 0.01, f"Load time variance {variance:.6f}s too high"


class TestContentLoadTime:
    """Tests for file content load time performance."""

    def test_cached_content_load_under_2_seconds(
        self,
        populated_cache: GitHubFileCache,
    ) -> None:
        """Verify cached content loads in under 2 seconds.

        With cache already populated, retrieval should be nearly instant.
        """
        cache = populated_cache
        content_key = build_content_key(
            "test-source", "skills/canvas", "SKILL.md", "abc123"
        )

        # Measure cached request time
        start = time.perf_counter()
        result = cache.get(content_key)
        duration = time.perf_counter() - start

        assert result is not None, "Expected cache hit"
        assert duration < CONTENT_LOAD_CACHED_THRESHOLD, (
            f"Cached content load took {duration:.4f}s, "
            f"exceeds {CONTENT_LOAD_CACHED_THRESHOLD}s target"
        )

        # In practice, cached loads should be <1ms
        assert duration < 0.01, f"Cached load unexpectedly slow: {duration:.4f}s"

    def test_cached_vs_simulated_uncached_performance_ratio(
        self,
        populated_cache: GitHubFileCache,
        mock_content_data: dict,
    ) -> None:
        """Verify cached content is significantly faster than simulated uncached.

        Simulates the performance difference between cache hit and miss by
        measuring cache access time vs. simulated API latency.
        """
        cache = populated_cache
        content_key = build_content_key(
            "test-source", "skills/canvas", "SKILL.md", "abc123"
        )

        # Measure cached request time
        cached_durations = []
        for _ in range(10):
            start = time.perf_counter()
            result = cache.get(content_key)
            duration = time.perf_counter() - start
            cached_durations.append(duration)
            assert result is not None

        avg_cached = sum(cached_durations) / len(cached_durations)

        # Simulate uncached latency (GitHub API typically 100-500ms)
        simulated_api_latency = 0.2  # 200ms simulated

        # Cached should be at least 100x faster than API call
        speedup = simulated_api_latency / avg_cached
        assert speedup > 100, (
            f"Cache speedup {speedup:.1f}x below expected (>100x). "
            f"Cached avg: {avg_cached:.6f}s, API latency: {simulated_api_latency}s"
        )

    def test_large_content_cached_load_performance(self) -> None:
        """Verify large file content still loads quickly from cache.

        Tests with content up to 1MB (the truncation limit).
        """
        cache = get_github_file_cache()

        # Create large content (approaching 1MB limit)
        large_content = "x" * (1024 * 1024)  # 1MB
        large_content_data = {
            "content": large_content,
            "encoding": "utf-8",
            "size": len(large_content),
            "sha": "large123",
            "name": "large-file.txt",
            "path": "skills/test/large-file.txt",
            "is_binary": False,
        }

        content_key = build_content_key(
            "test-source", "skills/test", "large-file.txt", "large123"
        )

        # Cache the large content
        cache.set(content_key, large_content_data, ttl_seconds=DEFAULT_CONTENT_TTL)

        # Measure retrieval time
        start = time.perf_counter()
        result = cache.get(content_key)
        duration = time.perf_counter() - start

        assert result is not None
        assert duration < CONTENT_LOAD_CACHED_THRESHOLD, (
            f"Large content load took {duration:.4f}s, "
            f"exceeds {CONTENT_LOAD_CACHED_THRESHOLD}s target"
        )


# =============================================================================
# End-to-End Cache Performance Tests
# =============================================================================


class TestEndToEndCachePerformance:
    """End-to-end tests simulating real usage patterns."""

    def test_realistic_browsing_session_performance(
        self,
        mock_tree_data: list[dict],
        mock_content_data: dict,
    ) -> None:
        """Simulate a realistic browsing session and verify performance.

        Pattern (simulating typical user behavior where cached content is
        accessed multiple times during a session):
        1. User loads file tree (cold cache - miss)
        2. User views several files (cold cache - miss for each)
        3. User navigates back to file tree multiple times (warm cache - hits)
        4. User reviews previously viewed files multiple times (warm cache - hits)
        5. User does additional browsing iterations (warm cache - hits)

        With 6 initial misses and 20+ subsequent hits, hit rate should exceed 70%.
        """
        cache = get_github_file_cache()
        source_id = "browse-session-source"
        artifact_path = "skills/my-skill"
        sha = "session123"

        tree_key = build_tree_key(source_id, artifact_path, sha)
        file_keys = [
            build_content_key(source_id, artifact_path, f"file{i}.md", sha)
            for i in range(5)
        ]

        total_requests = 0
        cache_hits = 0

        # Phase 1: Initial load (all misses - simulating first visit)
        assert cache.get(tree_key) is None  # Miss
        total_requests += 1
        cache.set(tree_key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)

        for key in file_keys:
            assert cache.get(key) is None  # Miss
            total_requests += 1
            cache.set(key, mock_content_data, ttl_seconds=DEFAULT_CONTENT_TTL)

        # Phase 2: Navigate back and review (hits) - simulating user browsing
        # Users typically access the same content multiple times during a session
        for _ in range(3):  # 3 browsing cycles
            # Navigate to tree
            result = cache.get(tree_key)
            total_requests += 1
            if result is not None:
                cache_hits += 1

            # Review some files
            for key in file_keys:
                result = cache.get(key)
                total_requests += 1
                if result is not None:
                    cache_hits += 1

        # Phase 3: Additional tree access (common as users navigate)
        for _ in range(5):
            result = cache.get(tree_key)
            total_requests += 1
            if result is not None:
                cache_hits += 1

        # Calculate hit rate
        # Expected: 6 misses, 3*(1+5) + 5 = 23 hits = 23/29 = 79.3%
        hit_rate = cache_hits / total_requests

        # With this pattern (6 misses, 23 hits), hit rate should exceed target
        assert hit_rate >= CACHE_HIT_RATE_TARGET, (
            f"Browsing session hit rate {hit_rate:.2%} below "
            f"{CACHE_HIT_RATE_TARGET:.0%} target"
        )

    def test_concurrent_access_performance(
        self,
        mock_tree_data: list[dict],
        mock_content_data: dict,
    ) -> None:
        """Test cache performance under concurrent access.

        Simulates multiple users browsing different artifacts simultaneously.
        """
        from concurrent.futures import ThreadPoolExecutor

        cache = get_github_file_cache()
        errors: list[Exception] = []
        request_times: list[float] = []

        def worker(worker_id: int) -> None:
            """Simulate a user browsing artifacts."""
            try:
                source_id = f"concurrent-source-{worker_id}"
                artifact_path = f"skills/skill-{worker_id}"
                sha = f"sha{worker_id}"

                tree_key = build_tree_key(source_id, artifact_path, sha)
                content_key = build_content_key(
                    source_id, artifact_path, "SKILL.md", sha
                )

                # Initial load (cold cache)
                cache.set(tree_key, mock_tree_data, ttl_seconds=DEFAULT_TREE_TTL)
                cache.set(content_key, mock_content_data, ttl_seconds=DEFAULT_CONTENT_TTL)

                # Repeated access (warm cache)
                for _ in range(20):
                    start = time.perf_counter()
                    cache.get(tree_key)
                    cache.get(content_key)
                    duration = time.perf_counter() - start
                    request_times.append(duration)

            except Exception as e:
                errors.append(e)

        # Run 10 concurrent workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in futures:
                future.result()

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

        # Verify all requests completed within threshold
        avg_time = sum(request_times) / len(request_times)
        max_time = max(request_times)

        assert max_time < FILE_TREE_LOAD_THRESHOLD, (
            f"Max concurrent request time {max_time:.4f}s exceeds threshold"
        )
        assert avg_time < 0.01, f"Avg concurrent request time {avg_time:.6f}s unexpectedly high"


# =============================================================================
# Cache Statistics Tests
# =============================================================================


class TestCacheStatistics:
    """Tests for cache statistics tracking accuracy."""

    def test_hit_rate_calculation_accuracy(self) -> None:
        """Verify hit rate is calculated correctly."""
        cache = get_github_file_cache()
        key = build_tree_key("stats-test", "path", "sha")

        # 1 miss (before set)
        cache.get(key)

        # Set value
        cache.set(key, {"test": "data"}, ttl_seconds=300)

        # 9 hits
        for _ in range(9):
            cache.get(key)

        stats = cache.stats()

        # Expected: 9 hits, 1 miss = 90% hit rate
        assert stats["hits"] == 9, f"Expected 9 hits, got {stats['hits']}"
        assert stats["misses"] == 1, f"Expected 1 miss, got {stats['misses']}"
        assert stats["hit_rate"] == 90.0, f"Expected 90% hit rate, got {stats['hit_rate']}%"

    def test_statistics_after_clear(self) -> None:
        """Verify statistics are reset after cache clear."""
        cache = get_github_file_cache()
        key = build_tree_key("clear-test", "path", "sha")

        # Generate some activity
        cache.set(key, {"test": "data"}, ttl_seconds=300)
        for _ in range(5):
            cache.get(key)

        # Clear cache
        cache.clear()

        stats = cache.stats()

        assert stats["hits"] == 0, "Hits should be reset after clear"
        assert stats["misses"] == 0, "Misses should be reset after clear"
        assert stats["entries"] == 0, "Entries should be 0 after clear"
