# Backend Logging & Metrics Quick Reference

**For Discovery and Import Operations**

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/core/discovery.py` | Discovery service with structured logging |
| `skillmeat/core/importer.py` | Import service with metrics |
| `skillmeat/core/discovery_metrics.py` | Prometheus metrics and thread-safe aggregation |
| `skillmeat/api/routers/artifacts.py` | API endpoints exposing metrics |

## Discovery Service Logging

### Start
```python
# Line 176-183
logger.info("Starting artifact discovery", extra={
    "path": str(self.base_path),
    "scan_mode": self.scan_mode,
    "artifacts_base": str(self.artifacts_base),
})
```

### Complete
```python
# Line 350-360
logger.info(f"Discovery scan completed: ...", extra={
    "discovered_count": len(discovered_artifacts),
    "importable_count": len(importable_artifacts),
    "skipped_count": len(skipped_artifacts),
    "error_count": len(errors),
    "duration_ms": round(scan_duration_ms, 2),
})
```

### Timing
```python
# Line 172 - Start
start_time = time.perf_counter()

# Line 340 - End
scan_duration_ms = (time.perf_counter() - start_time) * 1000
```

## Import Service Logging

### Start
```python
# Line 152-159
logger.info("Starting bulk import", extra={
    "artifact_count": len(artifacts),
    "collection": collection_name,
    "auto_resolve_conflicts": auto_resolve_conflicts,
})
```

### Complete
```python
# Line 282-290
logger.info(f"Bulk import completed: ...", extra={
    "imported_count": imported_count,
    "failed_count": failed_count,
    "duration_ms": round(duration_ms, 2),
    "status": status,
})
```

### Timing
```python
# Line 147 - Start
start_time = time.perf_counter()

# Line 262-263 - End
duration_sec = time.perf_counter() - start_time
duration_ms = duration_sec * 1000
```

## Prometheus Metrics

### Available Metrics
```
discovery_scans_total{status="..."} - Counter
discovery_artifacts_found - Gauge
discovery_scan_duration_seconds - Histogram
discovery_errors_total{error_type="..."} - Counter
bulk_import_requests_total{status="..."} - Counter
bulk_import_artifacts_total{result="..."} - Counter
bulk_import_duration_seconds{batch_size_range="..."} - Histogram
```

### Recording Metrics
```python
from skillmeat.core.discovery_metrics import discovery_metrics

# Record discovery scan
discovery_metrics.record_scan(artifact_count, duration_ms)

# Record import
discovery_metrics.record_import(success_count, failed_count)

# Get all stats
stats = discovery_metrics.get_stats()
```

## Log Levels

| Level | Use Case | Examples |
|-------|----------|----------|
| DEBUG | Detailed processing steps | Artifact processing, filtering details |
| INFO | Major operation milestones | Scan start/complete, import start/complete |
| WARNING | Recoverable errors | Permission denied, missing directory |
| ERROR | Unrecoverable errors | Failed scan, failed import (with exc_info) |

## Error Handling Examples

### Warning (Recoverable)
```python
# Line 191 - Artifacts directory not found
error_msg = "Artifacts directory not found"
logger.warning(error_msg)
# Scan returns early with empty result
```

### Error (With Context)
```python
# Line 228 - Error scanning directory
error_msg = "Error scanning type directory"
logger.error(error_msg, exc_info=True)  # Include full traceback
errors.append(error_msg)
# Scan continues with other types
```

## Structured Extra Dict Pattern

All logs use this pattern for machine-parseability:

```python
logger.info(
    "descriptive message",
    extra={
        "field1": value1,
        "field2": value2,
        "duration_ms": round(duration_ms, 2),
    }
)
```

### Benefits
- Queryable in log aggregation systems
- Parseable by log analyzers
- Structured for metrics extraction
- Compatible with ELK, Splunk, Datadog, CloudWatch

## API Integration

### Get Metrics
```python
# Called by GET /api/v1/artifacts/health/discovery
from skillmeat.core.discovery_metrics import discovery_metrics
stats = discovery_metrics.get_stats()
```

### Response Format
```json
{
    "total_scans": 42,
    "total_artifacts_discovered": 237,
    "total_imports": 15,
    "total_metadata_fetches": 128,
    "cache_hits": 95,
    "cache_misses": 33,
    "cache_hit_rate": 0.742,
    "errors": 2,
    "last_scan": {
        "timestamp": "2025-12-05T11:30:00Z",
        "duration_ms": 234.56,
        "artifact_count": 15
    }
}
```

## Log Query Examples

### Datadog
```
operation:discovery_scan status:success
| stats avg(@duration_ms) as avg_duration
```

### Elasticsearch
```json
{
    "query": {
        "bool": {
            "must": [
                {"match": {"operation": "discovery_scan"}},
                {"match": {"status": "success"}}
            ]
        }
    }
}
```

### CloudWatch Insights
```
fields @timestamp, operation, duration_ms, status
| filter operation = "discovery_scan"
| stats avg(duration_ms), max(duration_ms) by status
```

## Performance Tuning

### Metrics Recording
```python
# O(1) operation with minimal overhead
discovery_metrics.record_scan(count, duration_ms)

# Thread-safe via Lock
# No blocking I/O
# Pre-allocated Prometheus buckets
```

### Timing Precision
```python
# time.perf_counter() provides high resolution
start = time.perf_counter()  # Seconds with nanosecond precision
# ... operation ...
duration_ms = (time.perf_counter() - start) * 1000
```

## Adding New Logging

### Discovery Service
```python
# At start of operation
logger.info("Starting operation", extra={
    "operation_param": value,
})

# At end of operation
logger.info("Operation completed", extra={
    "result_count": count,
    "duration_ms": round(duration_ms, 2),
    "status": "success",
})

# On error
logger.error("Operation failed", extra={
    "error": str(e),
    "error_type": type(e).__name__,
}, exc_info=True)
```

### Import Service
```python
# Same pattern as discovery
logger.info("Starting bulk operation", extra={
    "item_count": len(items),
    "collection": name,
})

# Record results
logger.info("Bulk operation completed", extra={
    "success_count": imported,
    "failed_count": failed,
    "duration_ms": round(duration_ms, 2),
})
```

## Testing Metrics

```python
from skillmeat.core.discovery_metrics import discovery_metrics

# Clear metrics
discovery_metrics.total_scans = 0
discovery_metrics.total_artifacts_discovered = 0

# Record test data
discovery_metrics.record_scan(10, 123.45)

# Verify
stats = discovery_metrics.get_stats()
assert stats["total_scans"] == 1
assert stats["last_scan_artifact_count"] == 10
```

## Related Documentation

- Full verification: `.claude/docs/DIS-6.2-6.3-verification.md`
- API docs: `skillmeat/api/CLAUDE.md`
- Core architecture: Main `CLAUDE.md`
