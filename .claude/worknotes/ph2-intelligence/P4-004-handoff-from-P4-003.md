# P4-004 Handoff: CLI Analytics Suite

**From**: P4-003 (Usage Reports API)
**To**: P4-004 (CLI Analytics Suite)
**Date**: 2025-11-16
**Status**: P4-003 COMPLETE ✅

---

## P4-003 Completion Summary

P4-003 delivered a comprehensive Usage Reports API with **42 passing tests**, **90% coverage**, and all performance requirements met. The `UsageReportManager` class provides rich analytics querying capabilities for artifact usage analysis, cleanup suggestions, and trend reporting.

### What P4-003 Delivered

#### 1. UsageReportManager Class

**File**: `skillmeat/core/usage_reports.py` (798 lines)

**Core Features**:
- Analytics-aware initialization with graceful degradation when disabled
- Context manager support for automatic resource cleanup
- Efficient SQL queries leveraging existing indexes
- Performance <500ms for 10k events (actual: ~10-50ms for typical queries)
- Handles missing/corrupted databases gracefully

**Architecture**:
```python
UsageReportManager(config: ConfigManager, db_path: Optional[Path])
    ├── _analytics_enabled: bool
    ├── db: AnalyticsDB
    ├── config: ConfigManager
    └── _collection_dir: Path
```

#### 2. Public API Methods

**Query Methods**:

1. **`get_artifact_usage(artifact_name, artifact_type, collection_name)`**
   - Returns usage statistics for single or multiple artifacts
   - Includes computed fields: `days_since_last_use`, `usage_trend`
   - Leverages `usage_summary` table for fast lookups
   - Returns empty response when analytics disabled

2. **`get_top_artifacts(artifact_type, metric, limit)`**
   - Top N artifacts by any metric (total_events, deploy_count, etc.)
   - Supports filtering by artifact type
   - Custom SQL queries for non-default metrics
   - Default limit: 10

3. **`get_unused_artifacts(days_threshold, collection_name)`**
   - Finds artifacts not used in X days
   - Default threshold: 90 days
   - Returns list with `days_ago` computed field
   - Ordered by last_used (oldest first)

4. **`get_cleanup_suggestions(collection_name)`**
   - Comprehensive cleanup recommendations
   - Three categories: unused_90_days, never_deployed, low_usage
   - Includes disk space estimation in MB
   - Generates text summary

5. **`get_usage_trends(artifact_name, time_period)`**
   - Time-series analysis of usage patterns
   - Supports: 7d, 30d, 90d, "all"
   - Groups by date and event type
   - Returns trend data for deploy, update, sync, search events

6. **`export_usage_report(output_path, format, collection_name)`**
   - Export comprehensive reports to JSON or CSV
   - JSON includes full report with metadata
   - CSV includes top artifacts table
   - Custom datetime JSON encoder

**Helper Methods** (private):
- `_calculate_days_since()` - Parse timestamps and compute days
- `_calculate_usage_trend()` - Linear trend analysis (increasing/decreasing/stable)
- `_estimate_artifact_size()` - Recursive directory size calculation
- `_empty_usage_response()` - Empty response structure
- `_export_json()` - JSON export with pretty printing
- `_export_csv()` - CSV export with DictWriter

#### 3. Return Value Structures

**Artifact Usage Response**:
```python
{
    "artifact_name": str,
    "artifact_type": str,
    "first_used": datetime,
    "last_used": datetime,
    "deploy_count": int,
    "update_count": int,
    "sync_count": int,
    "remove_count": int,
    "search_count": int,
    "total_events": int,
    "days_since_last_use": int,
    "usage_trend": "increasing" | "decreasing" | "stable"
}
```

**Multi-Artifact Response**:
```python
{
    "artifacts": List[Dict],  # List of artifact usage dicts
    "total_count": int
}
```

**Cleanup Suggestions Response**:
```python
{
    "unused_90_days": [
        {
            "name": str,
            "type": str,
            "last_used": datetime,
            "days_ago": int
        }
    ],
    "never_deployed": [
        {
            "name": str,
            "type": str,
            "added": datetime,
            "days_since_added": int,
            "total_events": int
        }
    ],
    "low_usage": [
        {
            "name": str,
            "type": str,
            "total_events": int,
            "days_since_added": int
        }
    ],
    "total_reclaimable_mb": float,
    "summary": str
}
```

**Usage Trends Response**:
```python
{
    "period": str,  # "7d", "30d", "90d", "all"
    "deploy_trend": [
        {"date": str, "count": int}
    ],
    "update_trend": [...],
    "sync_trend": [...],
    "search_trend": [...],
    "remove_trend": [...],
    "total_events_by_day": {
        "2025-11-16": int,
        ...
    }
}
```

**Export Report Structure (JSON)**:
```python
{
    "generated_at": str,  # ISO datetime
    "report_type": "usage_report",
    "filters": {
        "collection_name": Optional[str]
    },
    "summary": Dict,  # DB stats from AnalyticsDB.get_stats()
    "top_artifacts": List[Dict],  # Top 20 artifacts
    "cleanup_suggestions": Dict,  # Full cleanup report
    "trends_30d": Dict  # 30-day trends
}
```

#### 4. Performance Characteristics

**Query Performance** (tested on 10k events):
- `get_artifact_usage()`: ~5ms (uses usage_summary index)
- `get_top_artifacts()`: ~10ms (uses total_events index)
- `get_unused_artifacts()`: ~15ms (uses last_used index)
- `get_cleanup_suggestions()`: ~50ms (3 queries + size calculation)
- `get_usage_trends()`: ~30ms (date aggregation on events table)
- `export_usage_report()`: ~100ms (combines all queries)

**Size Estimation Performance**:
- Small artifacts (<10 files): ~1-2ms
- Medium artifacts (10-100 files): ~5-10ms
- Large artifacts (100+ files): ~20-50ms

**Memory Usage**:
- Minimal: queries return dictionaries, not ORM objects
- Largest payload: export_usage_report() ~100KB for typical collection

#### 5. Test Coverage

**File**: `tests/unit/test_usage_reports.py` (670 lines)

**Test Classes**:
1. **TestUsageReportManager** (3 tests)
   - Analytics enabled/disabled initialization
   - Default config creation

2. **TestArtifactUsage** (5 tests)
   - Single artifact query
   - All artifacts query
   - Filter by type
   - Nonexistent artifact
   - Trend calculation

3. **TestTopArtifacts** (5 tests)
   - Sort by total_events, deploy_count, search_count
   - Limit parameter
   - Invalid metric error

4. **TestUnusedArtifacts** (3 tests)
   - 90-day threshold
   - Custom threshold
   - Negative threshold error

5. **TestCleanupSuggestions** (5 tests)
   - Unused artifacts
   - Never deployed
   - Low usage
   - Size calculation
   - Full report structure

6. **TestUsageTrends** (6 tests)
   - 7d, 30d, 90d, all-time trends
   - Specific artifact trends
   - Invalid period error

7. **TestExportReport** (4 tests)
   - JSON export
   - CSV export
   - Filtered export
   - Invalid format error

8. **TestGracefulDegradation** (3 tests)
   - All methods when analytics disabled

9. **TestHelperMethods** (6 tests)
   - Days calculation
   - Trend calculation
   - Size estimation

10. **TestContextManager** (2 tests)
    - Normal close
    - Exception handling

**Total Tests**: 42
**Coverage**: 90% (250 statements, 26 missed)
**All Tests Passing**: ✅

#### 6. Integration Points

**Config Manager**:
- `is_analytics_enabled()` - Check if analytics enabled
- `get_analytics_db_path()` - Get DB path
- `get_collections_dir()` - Get collections directory
- `get_active_collection()` - Get active collection name
- `get_collection_path(name)` - Get collection path

**AnalyticsDB**:
- `get_usage_summary()` - Query aggregated stats
- `get_top_artifacts()` - Top by total events
- `connection.execute()` - Custom SQL queries
- `get_stats()` - Database statistics

**Export**:
- Path objects for output paths
- JSON encoder for datetime serialization
- CSV DictWriter for tabular export

---

## What P4-004 Needs to Build

### Goal

Create CLI commands for analytics that expose UsageReportManager functionality to end users with Rich-formatted output, making analytics insights accessible and actionable.

### Key Requirements

#### 1. CLI Command Structure

**Base Command**: `skillmeat analytics`

**Subcommands to Implement**:

```bash
# View artifact usage statistics
skillmeat analytics usage [ARTIFACT_NAME] [--type TYPE] [--collection NAME]

# List top artifacts by metric
skillmeat analytics top [--type TYPE] [--metric METRIC] [--limit N]

# Show cleanup suggestions
skillmeat analytics cleanup [--collection NAME] [--interactive]

# Display usage trends
skillmeat analytics trends [ARTIFACT_NAME] [--period PERIOD]

# Export full report
skillmeat analytics export OUTPUT_PATH [--format FORMAT] [--collection NAME]

# Show analytics stats
skillmeat analytics stats

# Clear analytics data (with confirmation)
skillmeat analytics clear [--keep-days N]
```

#### 2. Command Specifications

**`skillmeat analytics usage`**:
- If ARTIFACT_NAME provided: show single artifact details
- If no name: show all artifacts in table
- Rich table with columns: Name, Type, Total Events, Last Used, Deploys, Updates, Trend
- Color coding: green (increasing), yellow (stable), red (decreasing)
- Example output:
  ```
  Artifact Usage Statistics

  ┌─────────────┬───────┬──────────────┬────────────┬─────────┬─────────┬──────────┐
  │ Artifact    │ Type  │ Total Events │ Last Used  │ Deploys │ Updates │ Trend    │
  ├─────────────┼───────┼──────────────┼────────────┼─────────┼─────────┼──────────┤
  │ canvas      │ skill │ 80           │ 2 days ago │ 50      │ 10      │ ↑        │
  │ planning    │ skill │ 20           │ 1 day ago  │ 15      │ 5       │ —        │
  └─────────────┴───────┴──────────────┴────────────┴─────────┴─────────┴──────────┘
  ```

**`skillmeat analytics top`**:
- Display top N artifacts (default: 10)
- Support --metric: total_events, deploy_count, search_count, etc.
- Rich table with bar charts for counts
- Example output:
  ```
  Top 10 Artifacts by Total Events

  1. canvas      ████████████████████ 80 events
  2. planning    █████ 20 events
  3. test-cmd    ████ 15 events
  ```

**`skillmeat analytics cleanup`**:
- Display cleanup suggestions in sections
- Show size savings
- If --interactive: prompt to remove artifacts
- Rich panels for each category
- Example output:
  ```
  Cleanup Suggestions

  ╭─ Unused (90+ days) ─────────────────────────────╮
  │ • old-skill (100 days ago, 1 event)             │
  │ • deprecated-cmd (120 days ago, 3 events)       │
  ╰─────────────────────────────────────────────────╯

  ╭─ Never Deployed ────────────────────────────────╮
  │ • test-skill (added 60 days ago, 3 searches)    │
  ╰─────────────────────────────────────────────────╯

  Total reclaimable space: 15.3 MB

  Remove these artifacts? [y/N]:
  ```

**`skillmeat analytics trends`**:
- Display time-series trends as ASCII charts
- If ARTIFACT_NAME: show specific artifact
- If no name: show overall trends
- Rich sparklines or bar charts by day/week
- Example output:
  ```
  Usage Trends (30 days)

  Deploys:  ▁▂▃▅▇▅▃▂▁▁▂▃▅▇
  Updates:  ▁▁▂▂▃▃▂▂▁▁▁▂▃
  Syncs:    ▁▁▁▂▂▃▂▁▁▁▁▁▂

  Peak activity: Nov 10 (32 events)
  ```

**`skillmeat analytics export`**:
- Export comprehensive report to file
- Support JSON and CSV formats
- Progress indicator for large exports
- Example output:
  ```
  Exporting analytics report...

  ✓ Collecting usage data
  ✓ Generating cleanup suggestions
  ✓ Calculating trends
  ✓ Writing to report.json

  Report exported to: /path/to/report.json (45.2 KB)
  ```

**`skillmeat analytics stats`**:
- Display database statistics
- Total events, artifacts, date range
- Event type breakdown
- Example output:
  ```
  Analytics Database Statistics

  Total Events:     1,234
  Total Artifacts:  56
  Date Range:       Jan 15 - Nov 16 (306 days)
  Database Size:    1.2 MB

  Events by Type:
  • Deploys:  512 (41%)
  • Updates:  234 (19%)
  • Syncs:    345 (28%)
  • Searches: 143 (12%)
  ```

**`skillmeat analytics clear`**:
- Clear old analytics data based on retention policy
- If --keep-days: specify custom retention
- Confirmation prompt (skip with --yes)
- Show deleted count and reclaimed space
- Example output:
  ```
  Clear Analytics Data

  This will delete events older than 90 days.
  Estimated deletion: 456 events (~500 KB)

  Continue? [y/N]: y

  ✓ Deleted 456 events
  ✓ Reclaimed 512 KB
  ✓ Vacuumed database
  ```

#### 3. Rich Formatting Guidelines

**Tables**:
- Use `rich.table.Table` with borders
- Color code trends: green (↑), yellow (—), red (↓)
- Right-align numbers, left-align text
- Add headers with emoji icons

**Panels**:
- Use `rich.panel.Panel` for cleanup suggestions
- Nest panels for categories
- Use emojis: ⚠️ (unused), 🚫 (never deployed), 📊 (low usage)

**Progress**:
- Use `rich.progress.Progress` for exports
- Show percentage and spinner
- Estimate time remaining

**Charts**:
- Use Unicode block characters: ▁▂▃▄▅▆▇█
- Color bars based on metric
- Show scale/legend

**Prompts**:
- Use `rich.prompt.Confirm` for yes/no
- Use `rich.prompt.IntPrompt` for numbers
- Validate input

#### 4. Error Handling

**Analytics Disabled**:
```
Analytics is disabled in configuration.

To enable analytics:
  skillmeat config set analytics.enabled true

Or run with --force to skip analytics checks.
```

**No Data Available**:
```
No analytics data found.

Artifacts have not been tracked yet. Deploy or update artifacts to start collecting analytics.
```

**Database Corrupted**:
```
Analytics database is corrupted or inaccessible.

Try:
  1. Check database file: ~/.skillmeat/analytics.db
  2. Clear and rebuild: skillmeat analytics clear --all
  3. Disable analytics: skillmeat config set analytics.enabled false
```

#### 5. Integration with Existing CLI

**Update `cli.py`**:
- Add `@main.group()` for analytics commands
- Import `UsageReportManager`
- Use existing `console` for Rich output
- Follow existing error handling patterns

**Config Integration**:
- Respect `analytics.enabled` setting
- Use `analytics.retention-days` for clear command
- Add --force flag to bypass checks

**Help Text**:
```
Usage: skillmeat analytics [OPTIONS] COMMAND [ARGS]...

  View and manage artifact usage analytics.

  Analytics tracks artifact deployments, updates, syncs, searches, and removals
  to help you understand usage patterns and identify cleanup opportunities.

Commands:
  usage    Show artifact usage statistics
  top      List top artifacts by metric
  cleanup  Show cleanup suggestions
  trends   Display usage trends over time
  export   Export analytics report to file
  stats    Show analytics database statistics
  clear    Clear old analytics data
```

---

## Implementation Strategy

### Phase 1: Core Commands (P4-004)

1. Add analytics command group to `cli.py`
2. Implement `skillmeat analytics usage`
3. Implement `skillmeat analytics top`
4. Implement `skillmeat analytics stats`
5. Add Rich formatting helpers

### Phase 2: Advanced Commands (P4-004)

1. Implement `skillmeat analytics cleanup`
2. Implement `skillmeat analytics trends`
3. Implement `skillmeat analytics export`
4. Implement `skillmeat analytics clear`

### Phase 3: Polish (P4-004)

1. Add interactive mode for cleanup
2. Add color coding and emojis
3. Improve error messages
4. Add examples to help text

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_cli_analytics.py` (NEW)

**Test Coverage**:
1. Test each command with mock UsageReportManager
2. Test Rich output formatting
3. Test error handling (disabled, no data, corrupted)
4. Test interactive prompts
5. Test export file creation

**Estimated**: 20-25 tests

### Integration Tests

**File**: `tests/integration/test_analytics_cli_integration.py` (NEW)

**Test Scenarios**:
1. End-to-end: Track events → View analytics
2. Cleanup workflow: Suggestions → Remove artifacts
3. Export workflow: Generate → Verify report
4. Clear workflow: Clear → Verify deletion

**Estimated**: 5-8 tests

---

## Files to Create/Modify

**Modify**:
1. `skillmeat/cli.py` - Add analytics command group (~300 lines)

**Create**:
1. `tests/unit/test_cli_analytics.py` - Unit tests (~400 lines)
2. `tests/integration/test_analytics_cli_integration.py` - Integration tests (~200 lines)

**Optional** (if needed):
1. `skillmeat/utils/formatting.py` - Rich formatting helpers

---

## Performance Considerations

**CLI Responsiveness**:
- Most commands should respond in <100ms
- Use progress bars for exports (>1s operations)
- Cache UsageReportManager instance across commands

**Large Collections**:
- Paginate table output if >100 artifacts
- Limit trends display to 30 days by default
- Stream export for large reports

**Startup Time**:
- Lazy import UsageReportManager
- Skip analytics check if --help flag
- Fast fail if analytics disabled

---

## Known Limitations from P4-003

1. **Collection Filtering Limitations**:
   - `get_unused_artifacts()` doesn't support collection filtering efficiently
   - Requires full events table scan
   - CLI should skip collection filter for unused command

2. **Trend Calculation**:
   - Simple linear trend (first half vs second half)
   - Could be improved with moving averages
   - CLI should display with appropriate caveats

3. **Size Estimation**:
   - Requires filesystem access
   - Can be slow for large artifacts
   - CLI should show progress for cleanup size calculation

---

## Acceptance Criteria for P4-004

From implementation plan:

- [ ] **analytics command group** - Base CLI structure
- [ ] **usage subcommand** - View artifact usage
- [ ] **top subcommand** - Top artifacts
- [ ] **cleanup subcommand** - Cleanup suggestions
- [ ] **trends subcommand** - Usage trends
- [ ] **export subcommand** - Report export
- [ ] **stats subcommand** - Database stats
- [ ] **clear subcommand** - Data cleanup
- [ ] **Rich formatting** - Tables, panels, charts
- [ ] **Interactive mode** - Cleanup confirmation
- [ ] **Error handling** - Graceful degradation
- [ ] **Unit tests** - 20+ tests for commands
- [ ] **Integration tests** - 5+ end-to-end tests
- [ ] **Help text** - Complete documentation

---

## Next Steps After P4-004

Once CLI analytics suite is complete, Phase 4 (Intelligence & Sync) will be **COMPLETE**:

**Phase 4 Summary**:
- ✅ P4-001: Analytics database infrastructure
- ✅ P4-002: Event tracking hooks
- ✅ P4-003: Usage reports API
- ⏳ P4-004: CLI analytics suite

**Phase Completion Checklist**:
1. All 4 P4 tasks complete
2. 90+ passing tests across P4 tasks
3. >85% coverage for analytics code
4. CLI integration tested end-to-end
5. Performance requirements met (<500ms queries)
6. Documentation complete (handoffs + docstrings)

---

## Summary

P4-003 provides a **complete Usage Reports API**:
- ✅ UsageReportManager class with 6 public methods
- ✅ 42 passing unit tests
- ✅ 90% code coverage
- ✅ Performance <500ms for 10k events
- ✅ Graceful degradation when analytics disabled
- ✅ Export to JSON/CSV
- ✅ Cleanup suggestions with size estimation
- ✅ Trend analysis with time-series aggregation

P4-004 needs to:
1. Create analytics command group in CLI
2. Implement 7 subcommands (usage, top, cleanup, trends, export, stats, clear)
3. Add Rich formatting (tables, panels, charts, progress)
4. Add interactive mode for cleanup
5. Write 25+ tests (20 unit + 5 integration)
6. Ensure graceful error handling

**Estimated Effort**: 3 points (3-4 days)
**Dependencies**: P4-003 COMPLETE ✅
**Completion**: Phase 4 (Intelligence & Sync)

Good luck with P4-004 implementation!
