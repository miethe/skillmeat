"""Prometheus metrics for SkillMeat.

Defines all metrics collected by SkillMeat for monitoring via Prometheus.
Metrics are organized by component: API, Marketplace, Bundles, MCP, etc.
"""

import sys
import functools
import time
from typing import Callable
from prometheus_client import Counter, Histogram, Gauge, Info

# =============================================================================
# API Metrics
# =============================================================================

api_requests_total = Counter(
    "skillmeat_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

api_request_duration = Histogram(
    "skillmeat_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ],
)

api_request_size = Histogram(
    "skillmeat_api_request_size_bytes",
    "API request body size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

api_response_size = Histogram(
    "skillmeat_api_response_size_bytes",
    "API response body size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

api_errors_total = Counter(
    "skillmeat_api_errors_total",
    "Total API errors",
    ["method", "endpoint", "error_type"],
)

# =============================================================================
# Marketplace Metrics
# =============================================================================

marketplace_listings_total = Gauge(
    "skillmeat_marketplace_listings_total",
    "Total marketplace listings",
    ["broker", "type"],
)

marketplace_installs_total = Counter(
    "skillmeat_marketplace_installs_total",
    "Total marketplace installs",
    ["broker", "listing_id", "status"],
)

marketplace_publishes_total = Counter(
    "skillmeat_marketplace_publishes_total",
    "Total marketplace publishes",
    ["broker", "status"],
)

marketplace_operation_duration = Histogram(
    "skillmeat_marketplace_operation_duration_seconds",
    "Marketplace operation duration in seconds",
    ["broker", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

marketplace_search_total = Counter(
    "skillmeat_marketplace_search_total", "Total marketplace searches", ["broker"]
)

marketplace_errors_total = Counter(
    "skillmeat_marketplace_errors_total",
    "Total marketplace errors",
    ["broker", "operation", "error_type"],
)

# GitHub source-specific metrics
marketplace_scan_duration_seconds = Histogram(
    "skillmeat_marketplace_scan_duration_seconds",
    "Duration of marketplace repository scans",
    ["source_id"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

marketplace_scan_artifacts_total = Counter(
    "skillmeat_marketplace_scan_artifacts_total",
    "Total artifacts detected during scans",
    ["source_id", "artifact_type"],
)

marketplace_import_total = Counter(
    "skillmeat_marketplace_import_total",
    "Total artifact imports from marketplace",
    ["source_id", "status"],
)

marketplace_scan_errors_total = Counter(
    "skillmeat_marketplace_scan_errors_total",
    "Total errors during marketplace scans",
    ["source_id", "error_type"],
)

# Clone operation timing
skillmeat_clone_duration_seconds = Histogram(
    "skillmeat_clone_duration_seconds",
    "Duration of git clone operations in seconds",
    ["strategy"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Manifest extraction timing
skillmeat_extraction_duration_seconds = Histogram(
    "skillmeat_extraction_duration_seconds",
    "Duration of manifest extraction operations in seconds",
    ["artifact_count_bucket"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# Total scan timing with strategy and status labels
skillmeat_scan_total_duration_seconds = Histogram(
    "skillmeat_scan_total_duration_seconds",
    "Total duration of marketplace source scan including all operations",
    ["strategy", "status"],
    buckets=[5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

# =============================================================================
# Bundle Metrics
# =============================================================================

bundle_exports_total = Counter(
    "skillmeat_bundle_exports_total", "Total bundle exports", ["status", "format"]
)

bundle_imports_total = Counter(
    "skillmeat_bundle_imports_total",
    "Total bundle imports",
    ["status", "strategy", "format"],
)

bundle_operation_duration = Histogram(
    "skillmeat_bundle_operation_duration_seconds",
    "Bundle operation duration in seconds",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

bundle_size = Histogram(
    "skillmeat_bundle_size_bytes",
    "Bundle file size in bytes",
    ["format"],
    buckets=[1000, 10000, 100000, 1000000, 10000000, 100000000],
)

bundle_artifacts_count = Histogram(
    "skillmeat_bundle_artifacts_count",
    "Number of artifacts in bundle",
    buckets=[1, 5, 10, 20, 50, 100, 200, 500],
)

# =============================================================================
# MCP Server Metrics
# =============================================================================

mcp_servers_total = Gauge(
    "skillmeat_mcp_servers_total", "Total MCP servers", ["status"]
)

mcp_health_checks_total = Counter(
    "skillmeat_mcp_health_checks_total", "Total MCP health checks", ["server", "status"]
)

mcp_deployments_total = Counter(
    "skillmeat_mcp_deployments_total", "Total MCP deployments", ["server", "status"]
)

mcp_operation_duration = Histogram(
    "skillmeat_mcp_operation_duration_seconds",
    "MCP operation duration in seconds",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

mcp_errors_total = Counter(
    "skillmeat_mcp_errors_total",
    "Total MCP errors",
    ["server", "operation", "error_type"],
)

# =============================================================================
# Collection Metrics
# =============================================================================

collections_total = Gauge("skillmeat_collections_total", "Total collections")

artifacts_total = Gauge(
    "skillmeat_artifacts_total", "Total artifacts", ["type", "scope"]
)

artifact_operations_total = Counter(
    "skillmeat_artifact_operations_total",
    "Total artifact operations",
    ["operation", "type", "status"],
)

artifact_operation_duration = Histogram(
    "skillmeat_artifact_operation_duration_seconds",
    "Artifact operation duration in seconds",
    ["operation", "type"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

# =============================================================================
# GitHub Source Metrics
# =============================================================================

github_requests_total = Counter(
    "skillmeat_github_requests_total",
    "Total GitHub API requests",
    ["operation", "status"],
)

github_rate_limit_remaining = Gauge(
    "skillmeat_github_rate_limit_remaining", "Remaining GitHub API rate limit"
)

github_clone_duration = Histogram(
    "skillmeat_github_clone_duration_seconds",
    "GitHub clone operation duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

github_errors_total = Counter(
    "skillmeat_github_errors_total", "Total GitHub errors", ["operation", "error_type"]
)

# =============================================================================
# Cache Metrics
# =============================================================================

cache_hits_total = Counter(
    "skillmeat_cache_hits_total", "Total cache hits", ["cache_name"]
)

cache_misses_total = Counter(
    "skillmeat_cache_misses_total", "Total cache misses", ["cache_name"]
)

cache_size_bytes = Gauge(
    "skillmeat_cache_size_bytes", "Cache size in bytes", ["cache_name"]
)

cache_entries_total = Gauge(
    "skillmeat_cache_entries_total", "Total cache entries", ["cache_name"]
)

# =============================================================================
# Memory & Context Intelligence Metrics
# =============================================================================

memory_items_total = Gauge(
    "skillmeat_memory_items_total",
    "Total memory items by status and type",
    ["status", "type"],
)

memory_operations_total = Counter(
    "skillmeat_memory_operations_total",
    "Total memory operations",
    ["operation", "status"],
)

memory_operation_duration = Histogram(
    "skillmeat_memory_operation_duration_seconds",
    "Memory operation duration in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

context_pack_generation_duration = Histogram(
    "skillmeat_context_pack_generation_duration_seconds",
    "Context pack generation duration in seconds",
    ["mode"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

context_pack_token_utilization = Histogram(
    "skillmeat_context_pack_token_utilization",
    "Context pack token budget utilization ratio (0-1)",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

context_pack_items_selected = Histogram(
    "skillmeat_context_pack_items_selected",
    "Number of items included in context packs",
    buckets=[1, 5, 10, 20, 50, 100, 200, 500],
)

memory_inbox_size = Gauge(
    "skillmeat_memory_inbox_size",
    "Number of candidate memory items awaiting review",
    ["project_id"],
)

# =============================================================================
# Application Info
# =============================================================================

app_info = Info("skillmeat_app", "Application information")

try:
    from skillmeat import __version__

    app_version = __version__
except ImportError:
    app_version = "unknown"

app_info.info(
    {
        "version": app_version,
        "python_version": sys.version.split()[0],
    }
)

# =============================================================================
# Decorator Helpers
# =============================================================================


def track_operation(metric_name: str, operation: str):
    """Decorator to track operation metrics.

    Args:
        metric_name: Name of the metric to track (e.g., "bundle", "mcp")
        operation: Operation name (e.g., "export", "import")

    Example:
        >>> @track_operation("bundle", "export")
        ... def export_bundle(bundle_id: str):
        ...     # Function code
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time

                # Record duration based on metric type
                if metric_name == "bundle":
                    bundle_operation_duration.labels(operation=operation).observe(
                        duration
                    )
                elif metric_name == "mcp":
                    mcp_operation_duration.labels(operation=operation).observe(duration)
                elif metric_name == "marketplace":
                    marketplace_operation_duration.labels(
                        broker="unknown", operation=operation
                    ).observe(duration)
                elif metric_name == "artifact":
                    artifact_operation_duration.labels(
                        operation=operation, type="unknown"
                    ).observe(duration)

                return result
            except Exception as e:
                duration = time.perf_counter() - start_time

                # Record duration even on error
                if metric_name == "bundle":
                    bundle_operation_duration.labels(operation=operation).observe(
                        duration
                    )
                elif metric_name == "mcp":
                    mcp_operation_duration.labels(operation=operation).observe(duration)

                raise

        return wrapper

    return decorator


def track_async_operation(metric_name: str, operation: str):
    """Decorator to track async operation metrics.

    Args:
        metric_name: Name of the metric to track
        operation: Operation name

    Example:
        >>> @track_async_operation("marketplace", "search")
        ... async def search_marketplace(query: str):
        ...     # Async function code
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start_time

                # Record duration
                if metric_name == "marketplace":
                    marketplace_operation_duration.labels(
                        broker="unknown", operation=operation
                    ).observe(duration)

                return result
            except Exception:
                duration = time.perf_counter() - start_time

                # Record duration even on error
                if metric_name == "marketplace":
                    marketplace_operation_duration.labels(
                        broker="unknown", operation=operation
                    ).observe(duration)

                raise

        return wrapper

    return decorator
