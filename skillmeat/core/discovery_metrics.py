"""Discovery-specific metrics collection.

This module extends the base metrics system with discovery-specific metrics
for monitoring smart import and discovery features.
"""

import functools
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# =============================================================================
# Discovery Prometheus Metrics
# =============================================================================

discovery_scans_total = Counter(
    'skillmeat_discovery_scans_total',
    'Total artifact discovery scans',
    ['status']
)

discovery_artifacts_found = Gauge(
    'skillmeat_discovery_artifacts_found',
    'Number of artifacts found in last scan'
)

discovery_scan_duration = Histogram(
    'skillmeat_discovery_scan_duration_seconds',
    'Discovery scan duration in seconds',
    buckets=[.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

discovery_errors_total = Counter(
    'skillmeat_discovery_errors_total',
    'Total discovery errors',
    ['error_type']
)

# Bulk import metrics
bulk_import_requests_total = Counter(
    'skillmeat_bulk_import_requests_total',
    'Total bulk import requests',
    ['status']
)

bulk_import_artifacts_total = Counter(
    'skillmeat_bulk_import_artifacts_total',
    'Total artifacts processed in bulk imports',
    ['result']  # 'success' or 'failed'
)

bulk_import_duration = Histogram(
    'skillmeat_bulk_import_duration_seconds',
    'Bulk import operation duration in seconds',
    ['batch_size_range'],  # '1-10', '11-50', '51+'
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# GitHub metadata metrics
github_metadata_requests_total = Counter(
    'skillmeat_github_metadata_requests_total',
    'Total GitHub metadata fetch requests',
    ['cache_hit']  # 'true' or 'false'
)

github_metadata_fetch_duration = Histogram(
    'skillmeat_github_metadata_fetch_duration_seconds',
    'GitHub metadata fetch duration in seconds',
    buckets=[.1, .5, 1.0, 2.0, 5.0, 10.0]
)

# Cache metrics
discovery_cache_hits = Counter(
    'skillmeat_discovery_cache_hits_total',
    'Total cache hits for discovery operations',
    ['cache_type']  # 'metadata' or 'discovery'
)

discovery_cache_misses = Counter(
    'skillmeat_discovery_cache_misses_total',
    'Total cache misses for discovery operations',
    ['cache_type']
)

# =============================================================================
# Simple Thread-Safe Metrics Dataclass
# =============================================================================

@dataclass
class DiscoveryMetrics:
    """Thread-safe discovery metrics for API endpoints.

    This provides a simple metrics collection that can be queried via API
    without requiring Prometheus infrastructure.

    Attributes:
        total_scans: Total number of discovery scans
        total_artifacts_discovered: Total artifacts found across all scans
        total_imports: Total bulk import operations
        total_metadata_fetches: Total GitHub metadata fetches
        cache_hits: Total cache hits
        cache_misses: Total cache misses
        errors: Total errors encountered
        last_scan_at: Timestamp of last scan
        last_scan_duration_ms: Duration of last scan in milliseconds
        last_scan_artifact_count: Number of artifacts in last scan
    """

    total_scans: int = 0
    total_artifacts_discovered: int = 0
    total_imports: int = 0
    total_metadata_fetches: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    last_scan_at: Optional[datetime] = None
    last_scan_duration_ms: Optional[float] = None
    last_scan_artifact_count: int = 0

    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_scan(self, artifact_count: int, duration_ms: float) -> None:
        """Record a discovery scan completion.

        Args:
            artifact_count: Number of artifacts discovered
            duration_ms: Scan duration in milliseconds
        """
        with self._lock:
            self.total_scans += 1
            self.total_artifacts_discovered += artifact_count
            self.last_scan_at = datetime.utcnow()
            self.last_scan_duration_ms = duration_ms
            self.last_scan_artifact_count = artifact_count

    def record_import(self, success_count: int, failed_count: int) -> None:
        """Record a bulk import operation.

        Args:
            success_count: Number of successfully imported artifacts
            failed_count: Number of failed imports
        """
        with self._lock:
            self.total_imports += 1

    def record_metadata_fetch(self, cache_hit: bool) -> None:
        """Record a GitHub metadata fetch.

        Args:
            cache_hit: Whether the fetch was served from cache
        """
        with self._lock:
            self.total_metadata_fetches += 1
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

    def record_error(self) -> None:
        """Record an error occurrence."""
        with self._lock:
            self.errors += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics as a dictionary.

        Returns:
            Dictionary with all current metrics
        """
        with self._lock:
            cache_hit_rate = (
                self.cache_hits / max(1, self.total_metadata_fetches)
                if self.total_metadata_fetches > 0
                else 0.0
            )

            return {
                "total_scans": self.total_scans,
                "total_artifacts_discovered": self.total_artifacts_discovered,
                "total_imports": self.total_imports,
                "total_metadata_fetches": self.total_metadata_fetches,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": round(cache_hit_rate, 3),
                "errors": self.errors,
                "last_scan": {
                    "timestamp": self.last_scan_at.isoformat() if self.last_scan_at else None,
                    "duration_ms": self.last_scan_duration_ms,
                    "artifact_count": self.last_scan_artifact_count,
                } if self.last_scan_at else None,
            }


# Global metrics instance
discovery_metrics = DiscoveryMetrics()

# =============================================================================
# Performance Logging Decorator
# =============================================================================

def log_performance(operation: str):
    """Decorator to log operation timing and metrics.

    Logs operation start, duration, and status (success/error) with
    structured extra fields for log aggregation systems.

    Args:
        operation: Operation name for logging (e.g., "discovery_scan")

    Example:
        >>> @log_performance("discovery_scan")
        ... def scan_artifacts(self):
        ...     # Function code
        ...     return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            logger.info(
                f"{operation} started",
                extra={
                    "operation": operation,
                    "status": "started",
                }
            )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    f"{operation} completed",
                    extra={
                        "operation": operation,
                        "duration_ms": round(duration_ms, 2),
                        "status": "success",
                    }
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                logger.error(
                    f"{operation} failed: {str(e)}",
                    extra={
                        "operation": operation,
                        "duration_ms": round(duration_ms, 2),
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

                # Record error in metrics
                discovery_metrics.record_error()

                raise

        return wrapper
    return decorator


def log_async_performance(operation: str):
    """Decorator to log async operation timing and metrics.

    Async variant of log_performance decorator for async functions.

    Args:
        operation: Operation name for logging

    Example:
        >>> @log_async_performance("async_metadata_fetch")
        ... async def fetch_metadata(self, source: str):
        ...     # Async function code
        ...     return metadata
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            logger.info(
                f"{operation} started",
                extra={
                    "operation": operation,
                    "status": "started",
                }
            )

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    f"{operation} completed",
                    extra={
                        "operation": operation,
                        "duration_ms": round(duration_ms, 2),
                        "status": "success",
                    }
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                logger.error(
                    f"{operation} failed: {str(e)}",
                    extra={
                        "operation": operation,
                        "duration_ms": round(duration_ms, 2),
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

                # Record error in metrics
                discovery_metrics.record_error()

                raise

        return wrapper
    return decorator
