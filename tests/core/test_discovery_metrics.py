"""Tests for discovery metrics collection."""

import time
from datetime import datetime

import pytest

from skillmeat.core.discovery_metrics import (
    DiscoveryMetrics,
    discovery_metrics,
    log_performance,
)


def test_discovery_metrics_initialization():
    """Test that DiscoveryMetrics initializes with zero values."""
    metrics = DiscoveryMetrics()

    assert metrics.total_scans == 0
    assert metrics.total_artifacts_discovered == 0
    assert metrics.total_imports == 0
    assert metrics.total_metadata_fetches == 0
    assert metrics.cache_hits == 0
    assert metrics.cache_misses == 0
    assert metrics.errors == 0
    assert metrics.last_scan_at is None
    assert metrics.last_scan_duration_ms is None
    assert metrics.last_scan_artifact_count == 0


def test_record_scan():
    """Test recording a discovery scan."""
    metrics = DiscoveryMetrics()

    # Record a scan
    metrics.record_scan(artifact_count=10, duration_ms=500.5)

    assert metrics.total_scans == 1
    assert metrics.total_artifacts_discovered == 10
    assert metrics.last_scan_at is not None
    assert isinstance(metrics.last_scan_at, datetime)
    assert metrics.last_scan_duration_ms == 500.5
    assert metrics.last_scan_artifact_count == 10

    # Record another scan
    metrics.record_scan(artifact_count=5, duration_ms=300.0)

    assert metrics.total_scans == 2
    assert metrics.total_artifacts_discovered == 15  # Cumulative
    assert metrics.last_scan_duration_ms == 300.0
    assert metrics.last_scan_artifact_count == 5


def test_record_import():
    """Test recording a bulk import."""
    metrics = DiscoveryMetrics()

    # Record import
    metrics.record_import(success_count=8, failed_count=2)

    assert metrics.total_imports == 1

    # Record another import
    metrics.record_import(success_count=5, failed_count=0)

    assert metrics.total_imports == 2


def test_record_metadata_fetch():
    """Test recording GitHub metadata fetches."""
    metrics = DiscoveryMetrics()

    # Record cache miss
    metrics.record_metadata_fetch(cache_hit=False)
    assert metrics.total_metadata_fetches == 1
    assert metrics.cache_hits == 0
    assert metrics.cache_misses == 1

    # Record cache hit
    metrics.record_metadata_fetch(cache_hit=True)
    assert metrics.total_metadata_fetches == 2
    assert metrics.cache_hits == 1
    assert metrics.cache_misses == 1


def test_record_error():
    """Test recording errors."""
    metrics = DiscoveryMetrics()

    metrics.record_error()
    assert metrics.errors == 1

    metrics.record_error()
    assert metrics.errors == 2


def test_get_stats():
    """Test getting statistics dictionary."""
    metrics = DiscoveryMetrics()

    # Record some data
    metrics.record_scan(artifact_count=10, duration_ms=500.0)
    metrics.record_import(success_count=8, failed_count=2)
    metrics.record_metadata_fetch(cache_hit=False)
    metrics.record_metadata_fetch(cache_hit=True)
    metrics.record_error()

    stats = metrics.get_stats()

    # Verify stats structure
    assert isinstance(stats, dict)
    assert stats["total_scans"] == 1
    assert stats["total_artifacts_discovered"] == 10
    assert stats["total_imports"] == 1
    assert stats["total_metadata_fetches"] == 2
    assert stats["cache_hits"] == 1
    assert stats["cache_misses"] == 1
    assert stats["cache_hit_rate"] == 0.5
    assert stats["errors"] == 1

    # Verify last_scan data
    assert "last_scan" in stats
    assert stats["last_scan"] is not None
    assert "timestamp" in stats["last_scan"]
    assert stats["last_scan"]["duration_ms"] == 500.0
    assert stats["last_scan"]["artifact_count"] == 10


def test_cache_hit_rate_calculation():
    """Test cache hit rate calculation edge cases."""
    metrics = DiscoveryMetrics()

    # No fetches - should not divide by zero
    stats = metrics.get_stats()
    assert stats["cache_hit_rate"] == 0.0

    # All cache hits
    metrics.record_metadata_fetch(cache_hit=True)
    metrics.record_metadata_fetch(cache_hit=True)
    stats = metrics.get_stats()
    assert stats["cache_hit_rate"] == 1.0

    # Mixed hits and misses
    metrics.record_metadata_fetch(cache_hit=False)
    stats = metrics.get_stats()
    assert stats["cache_hit_rate"] == pytest.approx(0.667, rel=0.01)


def test_thread_safety():
    """Test that metrics collection is thread-safe."""
    import threading

    metrics = DiscoveryMetrics()

    def record_operations():
        for _ in range(100):
            metrics.record_scan(artifact_count=1, duration_ms=100.0)
            metrics.record_metadata_fetch(cache_hit=True)

    # Create multiple threads
    threads = [threading.Thread(target=record_operations) for _ in range(10)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify counts are accurate (no race conditions)
    assert metrics.total_scans == 1000  # 100 per thread × 10 threads
    assert metrics.cache_hits == 1000


def test_log_performance_decorator():
    """Test the performance logging decorator."""

    @log_performance("test_operation")
    def test_function():
        time.sleep(0.01)  # Simulate work
        return "success"

    # Should not raise and should return result
    result = test_function()
    assert result == "success"


def test_log_performance_decorator_with_exception():
    """Test the performance logging decorator with exceptions."""

    @log_performance("test_operation")
    def failing_function():
        raise ValueError("Test error")

    # Should propagate exception
    with pytest.raises(ValueError, match="Test error"):
        failing_function()

    # Should have recorded an error in global metrics
    assert discovery_metrics.errors >= 1


def test_global_metrics_instance():
    """Test that the global metrics instance is accessible."""
    from skillmeat.core.discovery_metrics import discovery_metrics

    # Should be a DiscoveryMetrics instance
    assert isinstance(discovery_metrics, DiscoveryMetrics)

    # Should be able to record data
    initial_scans = discovery_metrics.total_scans
    discovery_metrics.record_scan(artifact_count=5, duration_ms=100.0)
    assert discovery_metrics.total_scans == initial_scans + 1
