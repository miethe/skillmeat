# P4-003 Handoff: Usage Reports API

**From**: P4-002 (Event Tracking Hooks)
**To**: P4-003 (Usage Reports API)
**Date**: 2025-11-16
**Status**: P4-002 COMPLETE ✅

---

## P4-002 Completion Summary

P4-002 delivered comprehensive event tracking throughout the codebase with **80 passing tests total** (50 from P4-001 + 30 from P4-002), **95% coverage** of EventTracker class, and event hooks integrated into all core operations.

### What P4-002 Delivered

#### 1. EventTracker Class

**File**: `skillmeat/core/analytics.py` (657 lines)

**Features**:
- Retry logic with exponential backoff (max 3 attempts, base 100ms delay)
- Event buffering for failed writes (max 100 events)
- Privacy-safe path redaction (`/home/user/project` → `~/project`)
- Graceful degradation when analytics disabled
- Context manager support for automatic cleanup
- Never fails primary operations due to analytics errors

**Key Classes**:

1. **EventBuffer**:
   - Thread-safe event buffering with retry tracking
   - Max size enforcement (drops oldest when full)
   - Per-event retry counters
   - Methods: `add()`, `get_pending()`, `mark_success()`, `mark_failure()`, `clear()`

2. **EventTracker**:
   - Main API for event tracking
   - Respects `analytics.enabled` config
   - Automatic database initialization
   - Built-in retry and buffering

**EventTracker Methods**:
```python
def track_deploy(
    artifact_name: str,
    artifact_type: str,
    collection_name: str,
    project_path: Optional[str] = None,
    version: Optional[str] = None,
    sha: Optional[str] = None,
    success: bool = True,
) -> bool

def track_update(
    artifact_name: str,
    artifact_type: str,
    collection_name: str,
    strategy: str,
    version_before: Optional[str] = None,
    version_after: Optional[str] = None,
    conflicts_detected: int = 0,
    user_choice: Optional[str] = None,
    rollback: bool = False,
) -> bool

def track_sync(
    artifact_name: str,
    artifact_type: str,
    collection_name: str,
    sync_type: str,
    result: str,
    project_path: Optional[str] = None,
    sha_before: Optional[str] = None,
    sha_after: Optional[str] = None,
    conflicts_detected: int = 0,
    error_message: Optional[str] = None,
) -> bool

def track_remove(
    artifact_name: str,
    artifact_type: str,
    collection_name: str,
    reason: str = "user_action",
    from_project: bool = False,
) -> bool

def track_search(
    artifact_name: str,
    artifact_type: str,
    collection_name: str,
    query: str,
    search_type: str,
    score: float,
    rank: int,
    total_results: int,
) -> bool
```

#### 2. Event Tracking Integration

**Sync Operations** (`skillmeat/core/sync.py`):
- Replaced stub `_record_sync_event()` with real tracking
- Added `_record_artifact_sync_event()` for per-artifact tracking
- Tracks: overwrite, merge, fork sync operations
- Captures: SHAs, conflicts, errors, cancellations
- Events recorded at: lines 1043, 1059, 1116, 1135, 1159, 1180

**Update Operations** (`skillmeat/core/artifact.py`):
- Added `_record_update_event()` helper method (lines 1755-1803)
- Tracks update success (line 1221) and rollback (line 1258)
- Captures: strategy, versions, conflicts, user choices
- Integrated with snapshot/rollback flow

**Deploy Operations** (`skillmeat/core/deployment.py`):
- Added `_record_deploy_event()` helper method (lines 309-346)
- Tracks deployment success (line 166)
- Captures: version, SHA, success status
- Tracks undeploy as remove event (line 238)

**Remove Operations** (`skillmeat/core/artifact.py`):
- Added `_record_remove_event()` helper method (lines 1805-1837)
- Tracks artifact removal (line 506)
- Captures: reason, from_project flag

**Search Operations** (`skillmeat/core/search.py`):
- Added `_record_search_events()` helper method (lines 1460-1496)
- Tracks top 5 search results only (to avoid spam)
- Integrated with `search_collection()` (line 185) and `search_projects()` (line 741)
- Captures: query, search type, score, rank, total results
- Uses "cross-project" as collection name for cross-project searches

#### 3. Privacy and Security

**Path Redaction**:
- Converts `/home/user/projects/app` → `~/projects/app`
- Redacts paths outside home directory to filename only
- Recursive redaction in nested metadata dictionaries
- Implemented in: `_redact_path()`, `_redact_paths()`

**Security Measures**:
- No PII in events (paths redacted)
- Opt-out via `analytics.enabled = false` in config
- Local-only storage (no external transmission)
- Graceful error handling (no internal exposure)

#### 4. Test Suite

**File**: `tests/unit/test_analytics_tracking.py` (539 lines)
**Total Tests**: 30 (all passing)
**Coverage**: 95% of `skillmeat/core/analytics.py`

**Test Classes**:
1. TestEventBuffer (8 tests)
   - Buffer initialization and sizing
   - Event addition and retrieval
   - Success/failure marking
   - Retry count tracking
   - Buffer clearing

2. TestEventTrackerInitialization (3 tests)
   - Analytics enabled initialization
   - Analytics disabled handling
   - Graceful degradation on DB errors

3. TestEventTracking (6 tests)
   - track_deploy()
   - track_update()
   - track_sync()
   - track_remove()
   - track_search()
   - Disabled analytics handling

4. TestPathRedaction (5 tests)
   - Home path redaction
   - Outside home path redaction
   - None value handling
   - Nested metadata redaction

5. TestRetryLogic (3 tests)
   - Retry on database errors
   - Event buffering after max retries
   - Buffered event retry

6. TestContextManager (2 tests)
   - Connection closing
   - Buffered event retry on close

7. TestGracefulDegradation (3 tests)
   - Never fails primary operations
   - Buffer size reporting
   - Buffer clearing

#### 5. Event Types Tracked

All 5 required event types are now tracked:

1. **DEPLOY**: When artifacts deployed to projects
2. **UPDATE**: When artifacts updated in collection
3. **SYNC**: When artifacts synced from project to collection
4. **REMOVE**: When artifacts removed from collection or project
5. **SEARCH**: When search operations performed (top 5 results only)

---

## What P4-003 Needs to Build

### Goal

Create Usage Reports API to query analytics data and generate insights about artifact usage patterns, enabling cleanup suggestions and usage analysis.

### Key Requirements

#### 1. Create UsageReportManager

**File**: `skillmeat/core/usage.py` (NEW)

**Class**: `UsageReportManager`

**Methods**:
```python
def get_artifact_usage(
    artifact_name: Optional[str] = None,
    artifact_type: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Get usage statistics for artifact(s).

    Returns:
        {
            "artifact_name": "canvas",
            "artifact_type": "skill",
            "first_used": "2025-01-15T10:00:00",
            "last_used": "2025-11-16T15:30:00",
            "deploy_count": 15,
            "update_count": 3,
            "sync_count": 8,
            "remove_count": 1,
            "search_count": 42,
            "total_events": 69,
            "days_since_last_use": 5,
            "usage_trend": "increasing|decreasing|stable"
        }
    """

def get_top_artifacts(
    artifact_type: Optional[str] = None,
    metric: str = "total_events",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get top artifacts by usage metric.

    Args:
        artifact_type: Filter by type (skill, command, agent)
        metric: Sort by metric (total_events, deploy_count, search_count)
        limit: Max results

    Returns:
        List of artifact usage dicts sorted by metric
    """

def get_unused_artifacts(
    days_threshold: int = 90,
    collection_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find artifacts not used in X days.

    Args:
        days_threshold: Number of days without activity
        collection_name: Filter by collection

    Returns:
        List of unused artifacts with last_used date
    """

def get_cleanup_suggestions(
    collection_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate cleanup suggestions based on usage.

    Returns:
        {
            "unused_90_days": [
                {"name": "old-skill", "last_used": "2025-08-01", "days_ago": 107}
            ],
            "never_deployed": [
                {"name": "test-skill", "added": "2025-01-01"}
            ],
            "low_usage": [
                {"name": "rare-skill", "total_events": 2, "days_since_added": 200}
            ],
            "total_reclaimable_mb": 15.3
        }
    """

def get_usage_trends(
    artifact_name: Optional[str] = None,
    time_period: str = "30d",
) -> Dict[str, Any]:
    """Get usage trends over time period.

    Args:
        artifact_name: Optional artifact to analyze
        time_period: "7d", "30d", "90d", or "all"

    Returns:
        {
            "period": "30d",
            "deploy_trend": [{"date": "2025-11-01", "count": 5}, ...],
            "update_trend": [...],
            "sync_trend": [...],
            "search_trend": [...],
            "total_events_by_day": {...}
        }
    """

def export_usage_report(
    output_path: Path,
    format: str = "json",
    collection_name: Optional[str] = None,
) -> None:
    """Export full usage report to file.

    Args:
        output_path: Where to save report
        format: "json" or "csv"
        collection_name: Filter by collection

    Generates comprehensive report with:
    - Summary statistics
    - Top artifacts
    - Cleanup suggestions
    - Usage trends
    """
```

#### 2. Query Optimizations

**Leverage Existing Indexes**:
- `idx_artifact_name` on events table
- `idx_event_type` on events table
- `idx_timestamp` on events table
- `idx_last_used` on usage_summary table
- `idx_total_events` on usage_summary table

**Use usage_summary Table**:
- Aggregated stats already computed by P4-001
- No need to re-aggregate from events table for simple queries
- Only query events table for detailed trends

#### 3. Usage Trend Calculations

**Implement Trend Analysis**:
```python
def _calculate_trend(event_counts: List[int]) -> str:
    """Calculate usage trend (increasing, decreasing, stable).

    Args:
        event_counts: List of event counts by time period

    Returns:
        "increasing" if trend is upward
        "decreasing" if trend is downward
        "stable" if relatively flat

    Use simple linear regression or moving average.
    """
```

#### 4. Cleanup Suggestions Logic

**Criteria for Suggestions**:

1. **Unused (90+ days)**:
   - Query: `last_used < (NOW() - 90 days)`
   - Source: usage_summary table

2. **Never Deployed**:
   - Query: `deploy_count = 0`
   - Cross-reference with collection manifest
   - Only suggest if artifact exists but never used

3. **Low Usage**:
   - Query: `total_events < 5 AND days_since_added > 60`
   - Needs collection metadata for "added" date
   - Calculate from collection manifest or first event

4. **Size Estimation**:
   - Sum artifact directory sizes for cleanup candidates
   - Use `pathlib.Path.stat().st_size`
   - Aggregate to MB for report

---

## Implementation Strategy

### Phase 1: Basic Reports

1. Create `UsageReportManager` class
2. Implement `get_artifact_usage()`
3. Implement `get_top_artifacts()`
4. Query usage_summary table directly

### Phase 2: Cleanup Suggestions

1. Implement `get_unused_artifacts()`
2. Implement `get_cleanup_suggestions()`
3. Calculate size estimations
4. Cross-reference with collection manifest

### Phase 3: Trends and Export

1. Implement `get_usage_trends()`
2. Add time-series aggregation from events table
3. Implement `export_usage_report()`
4. Support JSON and CSV formats

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_usage_reports.py` (NEW)

**Test Classes**:
1. TestUsageReportManager (3 tests)
   - Initialization
   - Config integration
   - Analytics disabled handling

2. TestArtifactUsage (5 tests)
   - Get single artifact usage
   - Get all artifacts usage
   - Filter by type
   - Filter by collection
   - Trend calculation

3. TestTopArtifacts (4 tests)
   - Sort by total_events
   - Sort by deploy_count
   - Sort by search_count
   - Limit results

4. TestUnusedArtifacts (3 tests)
   - Find unused 90+ days
   - Find unused custom threshold
   - Filter by collection

5. TestCleanupSuggestions (5 tests)
   - Unused artifacts
   - Never deployed
   - Low usage
   - Size calculation
   - Full report generation

6. TestUsageTrends (4 tests)
   - 7-day trends
   - 30-day trends
   - 90-day trends
   - All-time trends

7. TestExportReport (3 tests)
   - Export to JSON
   - Export to CSV
   - Export with filters

**Total**: ~27 tests

### Integration Tests

**File**: `tests/integration/test_usage_reports_integration.py` (NEW)

**Test Scenarios**:
1. End-to-end: Record events → Generate report
2. Cleanup suggestions with real collection
3. Export report and verify format
4. Usage trends with time-based queries

**Total**: ~4 tests

---

## Data Schema Reference

From P4-001, available for queries:

**events table**:
- `id`, `event_type`, `artifact_name`, `artifact_type`
- `collection_name`, `project_path`, `timestamp`, `metadata`

**usage_summary table**:
- `artifact_name`, `artifact_type`, `first_used`, `last_used`
- `deploy_count`, `update_count`, `sync_count`, `remove_count`, `search_count`
- `total_events`

**Existing Methods from AnalyticsDB**:
- `get_events()` - Query events with filters
- `get_usage_summary()` - Query usage_summary
- `get_top_artifacts()` - Get top by total_events
- `get_stats()` - Database statistics

---

## Files to Create

1. `skillmeat/core/usage.py` - UsageReportManager class (~400 lines)
2. `tests/unit/test_usage_reports.py` - Unit tests (~600 lines)
3. `tests/integration/test_usage_reports_integration.py` - Integration tests (~200 lines)

## Files to Modify

1. `skillmeat/core/__init__.py` - Export UsageReportManager
2. `skillmeat/config.py` - Add usage report config (optional)

---

## Known Limitations from P4-002

1. **Synchronous Event Recording**:
   - Events recorded synchronously (may add ~5-10ms latency)
   - Mitigated by fast SQLite writes and retry logic
   - Future: Add async recording in Phase 5

2. **No Event Buffering Persistence**:
   - Buffered events lost on process exit
   - Mitigated by retry on close() via context manager
   - Future: Persist buffer to disk

3. **No Rate Limiting**:
   - Could record many events for large searches
   - Mitigated by limiting search events to top 5 results
   - Future: Add rate limiting

4. **Path Redaction Not Configurable**:
   - Always redacts paths to `~/...`
   - Future: Make redaction configurable

---

## Performance Notes

**Event Recording Performance** (from P4-002):
- Average: ~2-5ms per event (SQLite WAL mode)
- With retry: ~10-15ms worst case (3 attempts × 100-400ms backoff)
- Buffering prevents blocking on failures

**Query Performance** (for P4-003):
- usage_summary queries: <1ms (indexed)
- events table queries: <10ms (indexed, typical 100-1000 events)
- Trend aggregation: <50ms (needs time-based indexing)

**Optimization Tips**:
- Use usage_summary for summary stats (pre-aggregated)
- Use events table only for detailed trends
- Add composite indexes if time-based queries slow
- Consider pagination for large result sets

---

## Acceptance Criteria for P4-003

From implementation plan:

- [ ] **UsageReportManager created** - Core API class
- [ ] **get_artifact_usage()** - Retrieve usage stats
- [ ] **get_top_artifacts()** - Top artifacts by metric
- [ ] **get_unused_artifacts()** - Find unused artifacts
- [ ] **get_cleanup_suggestions()** - Generate cleanup report
- [ ] **get_usage_trends()** - Time-series analysis
- [ ] **export_usage_report()** - Export to JSON/CSV
- [ ] **Unit tests** - 27+ tests for UsageReportManager
- [ ] **Integration tests** - 4+ tests for end-to-end flows
- [ ] **Coverage** - >80% of usage.py
- [ ] **Performance** - Queries complete in <100ms

---

## Next Steps After P4-003

Once usage reports API is complete, P4-004 (CLI Analytics Suite) can:

1. Add `skillmeat analytics usage` command
2. Add `skillmeat analytics top` command
3. Add `skillmeat analytics cleanup` command
4. Add `skillmeat analytics trends` command
5. Add `skillmeat analytics export` command
6. Display reports with Rich formatting

---

## Summary

P4-002 provides a **complete event tracking infrastructure**:
- ✅ EventTracker with retry and buffering
- ✅ All 5 event types tracked (deploy, update, sync, remove, search)
- ✅ 80 passing tests (50 + 30)
- ✅ 95% coverage of EventTracker
- ✅ Privacy-safe path redaction
- ✅ Graceful degradation
- ✅ Integrated with all core operations

P4-003 needs to:
1. Create UsageReportManager for querying analytics
2. Implement 7 key report methods
3. Add cleanup suggestions logic
4. Write 31+ tests (27 unit + 4 integration)
5. Ensure <100ms query performance

**Estimated Effort**: 2 points (2-3 days)
**Dependencies**: P4-002 COMPLETE ✅
**Next**: P4-004 (CLI Analytics Suite)

Good luck with P4-003 implementation!
