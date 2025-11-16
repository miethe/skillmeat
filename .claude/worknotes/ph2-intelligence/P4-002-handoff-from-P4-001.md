# P4-002 Handoff: Event Tracking Hooks

**From**: P4-001 (Schema & Storage)
**To**: P4-002 (Event Tracking Hooks)
**Date**: 2025-11-16
**Status**: P4-001 COMPLETE ✅

---

## P4-001 Completion Summary

P4-001 delivered a complete analytics database infrastructure with **50 passing tests**, comprehensive schema, and production-ready connection management.

### What P4-001 Delivered

#### 1. AnalyticsDB Class
**File**: `skillmeat/storage/analytics.py` (804 lines)
**Features**:
- SQLite database with WAL mode for concurrency
- Version-based migration system (SCHEMA_VERSION = 1)
- Events table with comprehensive indexing
- Usage summary table with aggregated statistics
- Retention policy with cleanup_old_events() method
- Vacuum support for space reclamation
- Context manager support for resource management
- Retry logic for database locked scenarios (exponential backoff)

#### 2. Database Schema

**Events Table**:
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,      -- 'deploy', 'update', 'sync', 'remove', 'search'
    artifact_name TEXT NOT NULL,
    artifact_type TEXT NOT NULL,   -- 'skill', 'command', 'agent'
    collection_name TEXT,
    project_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT                  -- JSON blob
);

-- Indexes
CREATE INDEX idx_event_type ON events(event_type);
CREATE INDEX idx_artifact_name ON events(artifact_name);
CREATE INDEX idx_timestamp ON events(timestamp);
CREATE INDEX idx_collection ON events(collection_name);
CREATE INDEX idx_artifact_type_name ON events(artifact_type, artifact_name);
```

**Usage Summary Table**:
```sql
CREATE TABLE usage_summary (
    artifact_name TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    first_used DATETIME,
    last_used DATETIME,
    deploy_count INTEGER DEFAULT 0,
    update_count INTEGER DEFAULT 0,
    sync_count INTEGER DEFAULT 0,
    remove_count INTEGER DEFAULT 0,
    search_count INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_last_used ON usage_summary(last_used);
CREATE INDEX idx_total_events ON usage_summary(total_events);
CREATE INDEX idx_usage_artifact_type ON usage_summary(artifact_type);
```

#### 3. Configuration Integration

**File**: `skillmeat/config.py`
**New Methods**:
- `is_analytics_enabled()` → bool (default: True)
- `get_analytics_retention_days()` → int (default: 90)
- `get_analytics_db_path()` → Path (default: ~/.skillmeat/analytics.db)

**Config Structure**:
```toml
[analytics]
enabled = true
retention-days = 90
# db-path = "/custom/path/analytics.db"  # optional
```

#### 4. Key Methods Available

**Event Recording**:
```python
def record_event(
    event_type: str,              # 'deploy', 'update', 'sync', 'remove', 'search'
    artifact_name: str,
    artifact_type: str,           # 'skill', 'command', 'agent'
    collection_name: Optional[str] = None,
    project_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Record an analytics event, returns event ID."""
```

**Event Querying**:
```python
def get_events(
    event_type: Optional[str] = None,
    artifact_name: Optional[str] = None,
    artifact_type: Optional[str] = None,
    collection_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Query events with optional filtering."""
```

**Usage Summary**:
```python
def get_usage_summary(
    artifact_name: Optional[str] = None,
    artifact_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get usage summary statistics."""

def get_top_artifacts(
    artifact_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top artifacts by total events."""
```

**Maintenance**:
```python
def cleanup_old_events(days: int = 90) -> int:
    """Remove events older than specified days, returns count deleted."""

def vacuum() -> None:
    """Vacuum database to reclaim space."""

def get_stats() -> Dict[str, Any]:
    """Get database statistics."""
```

### Test Suite

**File**: `tests/unit/test_analytics.py`
**Total Tests**: 51 (50 passing, 1 skipped)
**Coverage**: Comprehensive coverage of all AnalyticsDB functionality
**Execution Time**: ~5 seconds (including 1.1s sleep for timestamp test)

**Test Classes**:
1. TestAnalyticsDBInitialization (6 tests)
2. TestRecordEvent (8 tests)
3. TestGetEvents (9 tests)
4. TestGetUsageSummary (4 tests)
5. TestGetTopArtifacts (3 tests)
6. TestCleanupOldEvents (5 tests)
7. TestVacuum (2 tests)
8. TestGetStats (2 tests)
9. TestConnectionManagement (4 tests)
10. TestRetryLogic (2 tests)
11. TestMigrations (3 tests)
12. TestThreadSafety (2 tests)

---

## What P4-002 Needs to Build

### Goal
Implement event tracking hooks in core operations (deploy, update, sync, remove, search) to populate the analytics database.

### Key Requirements

#### 1. Integration Points

**From Phase 4 Handoff document**, these locations need event tracking:

**Sync Operations** (`skillmeat/core/sync.py`):
- Line 1047-1064: `_record_sync_event()` - STUB EXISTS
- Events: sync (overwrite/merge/fork), with success/conflict/error status

**Update Operations** (`skillmeat/core/artifact.py`):
- `apply_update_strategy()` - record update attempts
- `_apply_overwrite_strategy()` - record strategy usage
- `_apply_merge_strategy()` - record merge results
- `_apply_prompt_strategy()` - record user decisions

**Deploy Operations** (`skillmeat/core/deployment.py`):
- Deployment tracking (if exists)
- CLI deploy commands

**Remove Operations**:
- Artifact removal from collection
- Artifact removal from project

**Search Operations** (`skillmeat/core/search.py`):
- Search queries (already has SearchResult, just needs analytics emission)

#### 2. Event Data to Capture

**Sync Events**:
```python
{
    "event_type": "sync",
    "artifact_name": "canvas",
    "artifact_type": "skill",
    "collection_name": "default",
    "project_path": "/home/user/projects/my-app",
    "metadata": {
        "sync_type": "overwrite|merge|fork",
        "result": "success|conflict|error|cancelled",
        "sha_before": "abc123...",
        "sha_after": "def456...",
        "conflicts_detected": 3,
        "error_message": "..."  # if error
    }
}
```

**Update Events**:
```python
{
    "event_type": "update",
    "artifact_name": "canvas",
    "artifact_type": "skill",
    "collection_name": "default",
    "metadata": {
        "strategy": "overwrite|merge|prompt",
        "version_before": "v1.0.0",
        "version_after": "v2.0.0",
        "conflicts_detected": 0,
        "user_choice": "proceed|cancel",  # for prompt strategy
        "rollback": false
    }
}
```

**Deploy Events**:
```python
{
    "event_type": "deploy",
    "artifact_name": "canvas",
    "artifact_type": "skill",
    "collection_name": "default",
    "project_path": "/home/user/projects/my-app",
    "metadata": {
        "version": "v1.0.0",
        "sha": "abc123...",
        "success": true
    }
}
```

**Remove Events**:
```python
{
    "event_type": "remove",
    "artifact_name": "canvas",
    "artifact_type": "skill",
    "collection_name": "default",
    "metadata": {
        "reason": "user_action|cleanup",
        "from_project": false  # true if removing from project
    }
}
```

**Search Events**:
```python
{
    "event_type": "search",
    "artifact_name": "canvas",  # result artifact
    "artifact_type": "skill",
    "collection_name": "default",
    "metadata": {
        "query": "design patterns",
        "search_type": "metadata|content|both",
        "score": 8.5,
        "rank": 1,
        "total_results": 5
    }
}
```

---

## Implementation Strategy

### 1. Create AnalyticsManager

**File**: `skillmeat/core/analytics.py` (NEW)

```python
"""Analytics event tracking for SkillMeat."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import ConfigManager
from ..storage.analytics import AnalyticsDB

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Manages analytics event tracking.

    Features:
    - Respects analytics.enabled config
    - Graceful degradation if database unavailable
    - Event buffering on failure (optional)
    - Privacy-safe (no PII logging)
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize analytics manager.

        Args:
            config: Optional ConfigManager instance
        """
        self.config = config or ConfigManager()
        self.db: Optional[AnalyticsDB] = None
        self._enabled = self.config.is_analytics_enabled()

        if self._enabled:
            try:
                db_path = self.config.get_analytics_db_path()
                self.db = AnalyticsDB(db_path=db_path)
            except Exception as e:
                logger.warning(f"Analytics database unavailable: {e}")
                self._enabled = False

    def record_event(
        self,
        event_type: str,
        artifact_name: str,
        artifact_type: str,
        collection_name: Optional[str] = None,
        project_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record analytics event.

        Args:
            event_type: Type of event (deploy, update, sync, remove, search)
            artifact_name: Name of artifact
            artifact_type: Type of artifact (skill, command, agent)
            collection_name: Name of collection (optional)
            project_path: Path to project (optional, redacted in logs)
            metadata: Additional event-specific data (optional)

        Returns:
            True if event recorded successfully, False otherwise
        """
        if not self._enabled or self.db is None:
            return False

        try:
            # Redact absolute paths from metadata for privacy
            safe_metadata = self._redact_paths(metadata) if metadata else None

            self.db.record_event(
                event_type=event_type,
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                collection_name=collection_name,
                project_path=self._redact_path(project_path) if project_path else None,
                metadata=safe_metadata,
            )
            return True
        except Exception as e:
            logger.debug(f"Failed to record analytics event: {e}")
            return False

    def _redact_path(self, path: Optional[str]) -> Optional[str]:
        """Redact absolute paths for privacy.

        Converts /home/user/projects/my-app → ~/projects/my-app
        """
        if not path:
            return None

        try:
            p = Path(path)
            home = Path.home()
            if p.is_relative_to(home):
                return str(Path("~") / p.relative_to(home))
            return str(p.name)  # Just filename if not under home
        except Exception:
            return "redacted"

    def _redact_paths(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact paths in metadata dict."""
        redacted = {}
        for key, value in metadata.items():
            if isinstance(value, str) and "/" in value:
                redacted[key] = self._redact_path(value)
            elif isinstance(value, dict):
                redacted[key] = self._redact_paths(value)
            else:
                redacted[key] = value
        return redacted

    def close(self):
        """Close analytics database connection."""
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
```

### 2. Replace Sync Event Stub

**File**: `skillmeat/core/sync.py`

**Current (lines 1047-1064)**:
```python
def _record_sync_event(
    self,
    artifact_name: str,
    sync_type: str,
    result: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Record sync analytics event."""
    # TODO P4-002: Implement analytics event recording
    logger.debug(
        f"Analytics event: sync {artifact_name} "
        f"({sync_type}) -> {result}"
    )
    pass
```

**New Implementation**:
```python
def _record_sync_event(
    self,
    artifact_name: str,
    artifact_type: str,
    sync_type: str,
    result: str,
    sha_before: Optional[str] = None,
    sha_after: Optional[str] = None,
    conflicts: int = 0,
    error_message: Optional[str] = None,
) -> None:
    """Record sync analytics event.

    Args:
        artifact_name: Name of artifact synced
        artifact_type: Type of artifact (skill, command, agent)
        sync_type: Type of sync (overwrite, merge, fork)
        result: Result of sync (success, conflict, error, cancelled)
        sha_before: SHA before sync (optional)
        sha_after: SHA after sync (optional)
        conflicts: Number of conflicts detected (default: 0)
        error_message: Error message if result is error (optional)
    """
    metadata = {
        "sync_type": sync_type,
        "result": result,
    }

    if sha_before:
        metadata["sha_before"] = sha_before
    if sha_after:
        metadata["sha_after"] = sha_after
    if conflicts > 0:
        metadata["conflicts_detected"] = conflicts
    if error_message:
        metadata["error_message"] = error_message

    # Use AnalyticsManager to record event
    with AnalyticsManager() as analytics:
        analytics.record_event(
            event_type="sync",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=self.collection_mgr.collection.name,
            metadata=metadata,
        )
```

### 3. Add Update Event Tracking

**File**: `skillmeat/core/artifact.py`

Add to `apply_update_strategy()` method:
```python
# After successful update
with AnalyticsManager() as analytics:
    analytics.record_event(
        event_type="update",
        artifact_name=artifact.name,
        artifact_type=artifact.type.value,
        collection_name=self.collection_mgr.collection.name,
        metadata={
            "strategy": strategy,
            "version_before": old_version,
            "version_after": new_version,
            "conflicts_detected": conflicts_count,
            "rollback": False,
        },
    )
```

### 4. Add Deploy Event Tracking

**Location**: Deployment operations (CLI or DeploymentManager)

```python
with AnalyticsManager() as analytics:
    analytics.record_event(
        event_type="deploy",
        artifact_name=artifact_name,
        artifact_type=artifact_type,
        collection_name=collection_name,
        project_path=project_path,
        metadata={
            "version": version,
            "sha": sha,
            "success": True,
        },
    )
```

### 5. Add Remove Event Tracking

**Location**: Artifact removal operations

```python
with AnalyticsManager() as analytics:
    analytics.record_event(
        event_type="remove",
        artifact_name=artifact_name,
        artifact_type=artifact_type,
        collection_name=collection_name,
        metadata={
            "reason": "user_action",
            "from_project": False,
        },
    )
```

### 6. Add Search Event Tracking

**File**: `skillmeat/core/search.py`

Add to `search_collection()` and `search_projects()`:
```python
# After search completes, record each result
with AnalyticsManager() as analytics:
    for match in result.matches[:5]:  # Only top 5 to avoid spam
        analytics.record_event(
            event_type="search",
            artifact_name=match.artifact_name,
            artifact_type=match.artifact_type,
            collection_name=collection_name,
            metadata={
                "query": query,
                "search_type": search_type,
                "score": match.score,
                "rank": result.matches.index(match) + 1,
                "total_results": result.total_count,
            },
        )
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_analytics_manager.py` (NEW)

**Test Classes**:
1. TestAnalyticsManagerInitialization (3 tests)
   - Test default initialization
   - Test with disabled analytics
   - Test with custom config

2. TestEventRecording (8 tests)
   - Test record sync event
   - Test record update event
   - Test record deploy event
   - Test record remove event
   - Test record search event
   - Test event with all fields
   - Test event with minimal fields
   - Test event validation

3. TestPathRedaction (5 tests)
   - Test home path redaction (~/projects/app)
   - Test absolute path redaction (filename only)
   - Test nested metadata redaction
   - Test no redaction for short paths
   - Test error handling

4. TestGracefulDegradation (4 tests)
   - Test disabled analytics returns False
   - Test database unavailable returns False
   - Test database error logged
   - Test continues operation on error

**Total**: ~20 tests

### Integration Tests

**File**: `tests/integration/test_analytics_integration.py` (NEW)

**Test Scenarios**:
1. End-to-end sync → event → database
2. End-to-end update → event → database
3. End-to-end deploy → event → database
4. Event retention policy cleanup
5. Multiple events aggregated in usage_summary

**Total**: ~5 tests

### Updated Existing Tests

**Files to Update**:
- `tests/test_sync_pull.py` - Mock AnalyticsManager, verify event calls
- `tests/test_sync.py` - Mock AnalyticsManager
- `tests/test_update_integration_enhancements.py` - Mock AnalyticsManager

**Pattern for Mocking**:
```python
@patch('skillmeat.core.sync.AnalyticsManager')
def test_sync_records_analytics(mock_analytics):
    """Test that sync operations record analytics events."""
    # Setup
    mock_manager = MagicMock()
    mock_analytics.return_value.__enter__.return_value = mock_manager

    # Execute
    result = sync_manager.sync_from_project(...)

    # Verify
    mock_manager.record_event.assert_called_once_with(
        event_type="sync",
        artifact_name="canvas",
        artifact_type="skill",
        collection_name="default",
        metadata={"sync_type": "overwrite", "result": "success"}
    )
```

---

## Performance Considerations

### Event Recording Performance

**Target**: <10ms per event (from PRD)

**Optimization Strategies**:
1. **Batch Writes**: Buffer events and write in batches
2. **Async Recording**: Use background thread for database writes
3. **Connection Pooling**: Reuse database connections
4. **Minimal Logging**: Only log errors, not every event

**Benchmark Code**:
```python
import time

# Test event recording performance
start = time.time()
for i in range(1000):
    db.record_event("deploy", f"artifact-{i}", "skill")
elapsed = time.time() - start

print(f"Average time per event: {elapsed/1000*1000:.2f}ms")
# Target: <10ms
```

### Privacy and Security

**Privacy Requirements**:
1. ✅ No PII in events (use path redaction)
2. ✅ Opt-out via config (analytics.enabled = false)
3. ✅ Local-only storage (no external transmission)
4. ✅ Path redaction (~/projects/app vs /home/user/projects/app)

**Security Considerations**:
1. ✅ SQL injection prevention (parameterized queries in AnalyticsDB)
2. ✅ Database file permissions (readable only by user)
3. ✅ No sensitive metadata (redact before storage)
4. ✅ Graceful error handling (don't expose internals)

---

## Acceptance Criteria for P4-002

From implementation plan:

- [ ] **Events buffered on failure** - Use in-memory buffer if database unavailable
- [ ] **Events retried** - Retry failed writes with exponential backoff
- [ ] **Unit tests** - 20+ tests for AnalyticsManager
- [ ] **Integration tests** - 5+ tests for end-to-end flows
- [ ] **Mock updates** - Update existing tests to mock AnalyticsManager
- [ ] **All events tracked** - deploy, update, sync, remove, search
- [ ] **Privacy-safe** - Path redaction working
- [ ] **Performance** - <10ms per event
- [ ] **Config respected** - analytics.enabled flag works

---

## Files to Create

1. `skillmeat/core/analytics.py` - AnalyticsManager class (~200 lines)
2. `tests/unit/test_analytics_manager.py` - Unit tests (~400 lines)
3. `tests/integration/test_analytics_integration.py` - Integration tests (~300 lines)

## Files to Modify

1. `skillmeat/core/sync.py` - Replace _record_sync_event() stub
2. `skillmeat/core/artifact.py` - Add update event tracking
3. `skillmeat/core/search.py` - Add search event tracking (optional for P4-002, can defer to P4-003)
4. `skillmeat/cli.py` - Add deploy/remove event tracking
5. `skillmeat/core/__init__.py` - Export AnalyticsManager
6. `tests/test_sync_pull.py` - Mock AnalyticsManager
7. `tests/test_sync.py` - Mock AnalyticsManager
8. `tests/test_update_integration_enhancements.py` - Mock AnalyticsManager

---

## Known Limitations

1. **Synchronous Recording**: Events recorded synchronously (may add latency)
   - **Mitigation**: Keep record_event() fast with minimal validation
   - **Future**: Add async recording in Phase 5

2. **No Event Buffering**: Events not buffered if database unavailable
   - **Mitigation**: Graceful degradation (returns False, operation continues)
   - **Future**: Add in-memory buffer with flush on database recovery

3. **Limited Retry**: No automatic retry on failure
   - **Mitigation**: Log failures at DEBUG level
   - **Future**: Add retry queue in Phase 5

4. **No Rate Limiting**: Could record too many events for search
   - **Mitigation**: Only record top 5 search results
   - **Future**: Add rate limiting in Phase 5

---

## Next Steps After P4-002

Once event tracking is complete, P4-003 (Usage Reports API) can:
1. Query events table to generate usage reports
2. Aggregate data in usage_summary table
3. Suggest cleanup based on artifact usage
4. Export analytics data to JSON

P4-004 (CLI Analytics Suite) can then:
1. Add `skillmeat analytics` command
2. Display usage reports with Rich formatting
3. Show cleanup suggestions
4. Export to JSON for external tools

---

## Summary

P4-001 provides a **solid foundation** with:
- ✅ Complete database schema
- ✅ 50 passing tests
- ✅ WAL mode for concurrency
- ✅ Retry logic for locked database
- ✅ Retention policy and vacuum
- ✅ Configuration integration

P4-002 needs to:
1. Create AnalyticsManager class
2. Replace sync event stub
3. Add update/deploy/remove/search event tracking
4. Write 25+ tests (20 unit + 5 integration)
5. Update existing tests to mock AnalyticsManager
6. Ensure privacy-safe implementation

**Estimated Effort**: 2 points (2-3 days)
**Dependencies**: P4-001 COMPLETE ✅
**Next**: P4-003 (Usage Reports API)

Good luck with P4-002 implementation!
