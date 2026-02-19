---
title: 'Phase 6: Caching & Polish - Collections & Navigation Enhancement'
phase: 6
status: inferred_complete
assigned_to:
- python-backend-engineer
- ui-engineer-enhanced
- testing-specialist
dependencies:
- Phase 5 (Groups & Deployment Dashboard)
story_points: 8
duration: 1 week
schema_version: 2
doc_type: phase_plan
feature_slug: collections-navigation
prd_ref: null
plan_ref: null
---
# Phase 6: Caching & Polish

**Complexity**: Local caching, background refresh, comprehensive testing, documentation
**Story Points**: 8 | **Duration**: 1 week | **Status**: Pending

---

## Phase Objective

Implement intelligent local artifact caching with background refresh, ensure all code is thoroughly tested, complete documentation, and prepare for production deployment.

---

## Task Breakdown

### 1. Local Artifact Cache Implementation (TASK-6.1)
**Description**: SQLite-based local cache for artifact metadata and collection data

**Acceptance Criteria**:
- [ ] Cache database created at `~/.skillmeat/cache/artifacts.db`
- [ ] Cache tables created:
  - [ ] `artifact_cache` - artifact metadata with sync timestamp
  - [ ] `collection_cache` - collection metadata and groups
  - [ ] `cache_metadata` - version, last_sync, stats
- [ ] Migration from existing artifact storage to cache:
  - [ ] Pull all artifacts on app startup
  - [ ] Store in local cache with metadata
  - [ ] Update sync timestamp
  - [ ] Handle duplicate detection (skip if already cached)
- [ ] Cache data includes:
  - [ ] Artifact ID, name, type, source, version
  - [ ] Collection membership
  - [ ] Group membership
  - [ ] Last updated timestamp
  - [ ] Fetch hash (for invalidation detection)
- [ ] Cache keys/indexes optimized:
  - [ ] Index on artifact_id for quick lookup
  - [ ] Index on collection_id for filtering
  - [ ] Index on (collection_id, type) for grouped queries
  - [ ] Indexes on sync timestamp for TTL checks
- [ ] Cache operations:
  - [ ] Get artifact by ID (from cache)
  - [ ] Get all artifacts (from cache)
  - [ ] Filter by collection/group (from cache)
  - [ ] Update artifact in cache (local change)
  - [ ] Invalidate cache entry (mark stale)
  - [ ] Clear entire cache (reset button)
- [ ] Fallback strategy:
  - [ ] If cache missing, fetch from API
  - [ ] If API fails, show cached data (even if stale)
  - [ ] Show warning if data is stale (> 1 hour old)
- [ ] Thread-safe implementation:
  - [ ] Use locks for concurrent access
  - [ ] WAL mode for SQLite (already configured)
  - [ ] Atomic operations for multi-table updates

**Files to Create/Modify**:
- Create: `/skillmeat/cache/artifact_cache.py` - Cache manager class
- Create: `/skillmeat/cache/cache_schema.sql` - SQLite schema
- Modify: `/skillmeat/cache/models.py` - Add ArtifactCache model
- Modify: `/skillmeat/api/dependencies.py` - Inject cache manager

**Estimated Effort**: 2.5 points

---

### 2. Background Refresh Mechanism (TASK-6.2)
**Description**: Periodic background refresh of cached artifacts without blocking UI

**Acceptance Criteria**:
- [ ] Background task implemented:
  - [ ] Runs every 5-10 minutes (configurable)
  - [ ] Fetches artifact updates from API
  - [ ] Compares with cached data using hash/version
  - [ ] Updates cache with new/modified artifacts
  - [ ] Logs refresh activities
- [ ] Refresh strategy:
  - [ ] Full refresh on startup
  - [ ] Incremental refresh based on last_sync + TTL
  - [ ] Only fetch modified artifacts (etag/timestamp comparison)
  - [ ] Batch updates to minimize database operations
- [ ] Non-blocking implementation:
  - [ ] Background task runs in separate thread/async task
  - [ ] Does not lock UI or API
  - [ ] Uses low-priority task scheduler
  - [ ] Can be cancelled if new manual refresh requested
- [ ] Error handling:
  - [ ] Network errors don't fail refresh (use cached data)
  - [ ] Log errors for monitoring
  - [ ] Retry with exponential backoff on failure
  - [ ] Don't refresh too frequently on repeated failures
- [ ] Invalidation on mutations:
  - [ ] When user creates/updates artifact, invalidate cache entry
  - [ ] When user moves/copies artifact, update cache
  - [ ] When user manages groups, update cache
  - [ ] Clear relevant cache keys on API mutations
- [ ] Frontend integration:
  - [ ] Toast notification when refresh completes
  - [ ] Show "refreshing..." indicator
  - [ ] Display last sync time in UI
  - [ ] Automatically refetch UI queries on refresh completion
- [ ] Configuration:
  - [ ] Refresh interval configurable via environment
  - [ ] Can be disabled for offline mode
  - [ ] Can be forced via UI button

**Files to Create/Modify**:
- Create: `/skillmeat/cache/refresh_scheduler.py` - Background task scheduler
- Create: `/skillmeat/api/tasks/cache_refresh.py` - Refresh task
- Modify: `/skillmeat/api/server.py` - Start refresh scheduler on startup
- Modify: `/skillmeat/web/hooks/use-collections.ts` - Add refresh button

**Estimated Effort**: 2 points

---

### 3. Cache Persistence Across Restarts (TASK-6.3)
**Description**: Ensure cache survives app restarts for instant loading

**Acceptance Criteria**:
- [ ] Cache database persists to disk:
  - [ ] Located at `~/.skillmeat/cache/artifacts.db`
  - [ ] Survives app restart
  - [ ] Survives system restart
  - [ ] Survives cache manager reinitialization
- [ ] Startup behavior:
  - [ ] Load cache from disk on app startup
  - [ ] If cache not found, create it (initialization)
  - [ ] If cache corrupted, delete and recreate
  - [ ] Display cached data immediately while refreshing
- [ ] Cache validity:
  - [ ] Check cache age on startup (last_sync timestamp)
  - [ ] If cache < 1 hour old, show as current
  - [ ] If cache > 1 hour old, mark as "stale" visually
  - [ ] If cache > 24 hours old, force refresh on load
- [ ] User experience:
  - [ ] App loads collections instantly from cache
  - [ ] "Last synced X minutes ago" indicator
  - [ ] No loading spinners for cached data
  - [ ] Seamless transition when refresh completes
- [ ] Database maintenance:
  - [ ] Periodic VACUUM to reclaim space
  - [ ] Automatic cleanup of orphaned entries
  - [ ] Detect and repair corruption (sqlite3 PRAGMA integrity_check)
  - [ ] Provide manual cache cleanup button (Settings page)

**Files to Create/Modify**:
- Modify: `/skillmeat/api/server.py` - Load cache on startup
- Modify: `/skillmeat/web/components/providers.tsx` - Show cached data immediately
- Modify: `/skillmeat/cache/artifact_cache.py` - Add persistence logic

**Estimated Effort**: 1 point

---

### 4. Manual Refresh Button (TASK-6.4)
**Description**: UI control for manual cache refresh

**Acceptance Criteria**:
- [ ] Refresh button placed in collection page toolbar
  - [ ] Button shows "Refresh" text with refresh icon
  - [ ] Disabled state while refresh in progress
  - [ ] Loading spinner while refreshing
- [ ] Click behavior:
  - [ ] Triggers immediate cache refresh
  - [ ] Fetches latest data from API
  - [ ] Updates all cached data
  - [ ] Shows progress indicator (optional: progress bar)
  - [ ] Shows success/error toast
- [ ] User feedback:
  - [ ] "Refreshing..." message while in progress
  - [ ] Timestamp of last refresh in tooltip
  - [ ] Success toast: "Collection refreshed"
  - [ ] Error toast with retry button if refresh fails
  - [ ] Estimated time remaining (optional)
- [ ] Performance:
  - [ ] Refresh completes in < 5 seconds (typical)
  - [ ] Non-blocking: UI remains responsive
  - [ ] Can cancel mid-refresh (optional)
- [ ] Behavior:
  - [ ] Debounced: prevent multiple clicks triggering multiple refreshes
  - [ ] Keyboard accessible (Enter/Space to click)
  - [ ] Works on all pages (collection, all collections, dashboard)
- [ ] Integration with TanStack Query:
  - [ ] After refresh completes, invalidate relevant queries
  - [ ] Causes automatic refetch of UI data
  - [ ] Shows loading states for affected components

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/collection/refresh-button.tsx`
- Modify: `/skillmeat/web/components/collection/collection-toolbar.tsx`
- Modify: `/skillmeat/web/hooks/use-collections.ts` - Add refresh mutation

**Estimated Effort**: 1 point

---

### 5. Comprehensive Testing Suite (TASK-6.5)
**Description**: Achieve 85%+ test coverage across all new code

**Acceptance Criteria**:
- [ ] Backend testing:
  - [ ] Unit tests for cache models (90%+ coverage)
  - [ ] Integration tests for cache operations (read, write, invalidate)
  - [ ] Tests for background refresh logic
  - [ ] Tests for error handling and rollback
  - [ ] Performance tests for cache queries
  - [ ] Tests for concurrent access/thread safety
  - [ ] Migration tests (SQLite schema)
  - [ ] File: `/skillmeat/cache/tests/test_artifact_cache.py`
  - [ ] File: `/skillmeat/cache/tests/test_cache_refresh.py`
- [ ] Frontend testing:
  - [ ] Unit tests for caching hooks
  - [ ] Component tests for refresh button
  - [ ] Integration tests for cache-to-UI flow
  - [ ] Tests for cache persistence (localStorage + indexedDB)
  - [ ] Tests for offline mode (API down, use cache)
  - [ ] File: `/skillmeat/web/__tests__/hooks/use-cache.test.ts`
  - [ ] File: `/skillmeat/web/__tests__/components/refresh-button.test.tsx`
- [ ] E2E tests:
  - [ ] Cache loads on app startup
  - [ ] Cached data shows instantly
  - [ ] Manual refresh updates data
  - [ ] Background refresh keeps cache fresh
  - [ ] Cache survives app restart
  - [ ] Offline mode works with cached data
  - [ ] File: `/skillmeat/web/tests/caching-workflow.spec.ts`
- [ ] Coverage reports:
  - [ ] Backend cache code: >= 90%
  - [ ] Frontend cache code: >= 85%
  - [ ] Overall new code: >= 85%
  - [ ] Generate coverage reports: `pytest --cov`, `pnpm coverage`

**Files to Create/Modify**:
- Create: `/skillmeat/cache/tests/test_artifact_cache.py` (~300 lines)
- Create: `/skillmeat/cache/tests/test_cache_refresh.py` (~200 lines)
- Create: `/skillmeat/web/__tests__/hooks/use-cache.test.ts` (~200 lines)
- Create: `/skillmeat/web/tests/caching-workflow.spec.ts` (~150 lines)

**Estimated Effort**: 2 points

---

### 6. Documentation (TASK-6.6)
**Description**: Complete API documentation, user guide, and architecture docs

**Acceptance Criteria**:
- [ ] API Documentation:
  - [ ] OpenAPI/Swagger specs auto-generated and accurate
  - [ ] Endpoint reference with examples
  - [ ] Error response documentation
  - [ ] Query parameter documentation
  - [ ] Schema documentation with examples
  - [ ] File: Auto-generated from code comments
- [ ] User Guide:
  - [ ] Collections: Create, edit, delete collections
  - [ ] Groups: Create, manage, organize
  - [ ] Grouped View: Drag-and-drop guide
  - [ ] Deployment Dashboard: Deployment tracking
  - [ ] Caching: How cache works, refresh behavior
  - [ ] File: `/docs/user/guide/collections.md`
  - [ ] File: `/docs/user/guide/deployment-dashboard.md`
- [ ] Developer Documentation:
  - [ ] Architecture overview (database, API, frontend layers)
  - [ ] Type definitions and interfaces
  - [ ] Hook usage patterns
  - [ ] Context provider API
  - [ ] Cache API and refresh scheduler
  - [ ] File: `/docs/dev/architecture/collections-system.md`
  - [ ] File: `/docs/dev/developers/caching-system.md`
- [ ] Deployment Guide:
  - [ ] Migration from old system to new
  - [ ] Database schema changes
  - [ ] Configuration options
  - [ ] Troubleshooting cache issues
  - [ ] File: `/docs/deployment/collections-migration.md`
- [ ] README updates:
  - [ ] Update main README with new features
  - [ ] Link to full documentation
  - [ ] Quick start guide for Collections

**Files to Create/Modify**:
- Create: `/docs/user/guide/collections.md` (~200 lines)
- Create: `/docs/user/guide/deployment-dashboard.md` (~150 lines)
- Create: `/docs/dev/architecture/collections-system.md` (~200 lines)
- Create: `/docs/dev/developers/caching-system.md` (~150 lines)
- Create: `/docs/deployment/collections-migration.md` (~150 lines)
- Modify: `/README.md` - Add collections feature section

**Estimated Effort**: 1.5 points

---

## Task Breakdown Table

| Task ID | Task Name | Description | Story Points | Assigned To |
|---------|-----------|-------------|--------------|-------------|
| TASK-6.1 | Local Cache Implementation | SQLite cache with models | 2.5 | python-backend-engineer |
| TASK-6.2 | Background Refresh | Periodic cache updates | 2 | python-backend-engineer |
| TASK-6.3 | Cache Persistence | Cache survives restarts | 1 | python-backend-engineer |
| TASK-6.4 | Manual Refresh Button | UI control for refresh | 1 | ui-engineer-enhanced |
| TASK-6.5 | Comprehensive Testing | 85%+ coverage | 2 | testing-specialist |
| TASK-6.6 | Documentation | User and developer docs | 1.5 | documentation-writer |

**Total**: 8 story points

---

## Cache Architecture

### Cache Tables

```sql
-- Artifact cache with sync tracking
CREATE TABLE artifact_cache (
    id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL UNIQUE,
    data_json TEXT NOT NULL,           -- Full artifact object as JSON
    fetch_hash TEXT,                    -- Hash for change detection
    cached_at DATETIME NOT NULL,
    synced_at DATETIME,                 -- Last sync from API
    is_stale BOOLEAN DEFAULT 0,
    PRIMARY KEY(artifact_id)
);

-- Collection cache
CREATE TABLE collection_cache (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL UNIQUE,
    data_json TEXT NOT NULL,
    cached_at DATETIME NOT NULL,
    synced_at DATETIME,
    PRIMARY KEY(collection_id)
);

-- Cache metadata
CREATE TABLE cache_metadata (
    key TEXT PRIMARY KEY,               -- 'last_sync', 'cache_version'
    value TEXT NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Indexes
CREATE INDEX idx_artifact_cache_synced_at ON artifact_cache(synced_at);
CREATE INDEX idx_artifact_cache_is_stale ON artifact_cache(is_stale);
CREATE INDEX idx_collection_cache_synced_at ON collection_cache(synced_at);
```

### Backend Cache Manager

```python
class ArtifactCacheManager:
    """Manages local cache of artifacts."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Path.home() / ".skillmeat" / "cache" / "artifacts.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.session = sessionmaker(bind=self.engine)()

    def get_artifact(self, artifact_id: str) -> Optional[dict]:
        """Get artifact from cache."""
        entry = self.session.query(ArtifactCache).filter_by(
            artifact_id=artifact_id
        ).first()
        return json.loads(entry.data_json) if entry else None

    def save_artifact(self, artifact: dict) -> None:
        """Save artifact to cache."""
        entry = ArtifactCache(
            artifact_id=artifact['id'],
            data_json=json.dumps(artifact),
            cached_at=datetime.utcnow(),
            fetch_hash=hash_artifact(artifact)
        )
        self.session.merge(entry)
        self.session.commit()

    def refresh_cache(self) -> None:
        """Background refresh of cache."""
        try:
            artifacts = fetch_all_artifacts_from_api()
            for artifact in artifacts:
                self.save_artifact(artifact)
            self.update_metadata('last_sync', datetime.utcnow().isoformat())
        except Exception as e:
            logger.error(f"Cache refresh failed: {e}")
```

### Frontend Cache Hook

```typescript
export function useArtifactCache() {
  const [cache, setCache] = useState<Map<string, Artifact>>(new Map());
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load cache from storage on mount
  useEffect(() => {
    loadCacheFromStorage();
  }, []);

  // Background refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(refreshCache, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const refreshCache = async () => {
    setIsRefreshing(true);
    try {
      const artifacts = await api.getArtifacts();
      // Update cache and storage
      saveCacheToStorage(artifacts);
      setLastSync(new Date());
    } finally {
      setIsRefreshing(false);
    }
  };

  return { cache, lastSync, isRefreshing, refreshCache };
}
```

---

## Testing Strategy

### Unit Tests

**Backend Cache Tests**:
```python
def test_save_and_retrieve_artifact():
    """Test artifact save and retrieval."""
    manager = ArtifactCacheManager()
    artifact = {"id": "art-1", "name": "Test"}
    manager.save_artifact(artifact)
    retrieved = manager.get_artifact("art-1")
    assert retrieved == artifact

def test_refresh_cache():
    """Test background refresh updates cache."""
    # Mock API, trigger refresh, verify cache updated

def test_cache_persistence():
    """Test cache survives process restart."""
    # Save cache, restart manager, verify data still there
```

### E2E Tests

**Cache Workflow**:
```typescript
test('cache loads data immediately and refreshes in background', async () => {
  // App loads, collections display from cache
  await expect(page.getByText('My Collection')).toBeVisible();

  // Refresh button visible
  await expect(page.locator('[data-testid="refresh-button"]')).toBeVisible();

  // Click refresh
  await page.click('[data-testid="refresh-button"]');

  // Success toast appears
  await expect(page.getByText('Collection refreshed')).toBeVisible();
});
```

---

## Quality Gates

### Cache Implementation Checklist
- [ ] SQLite cache properly configured with WAL mode
- [ ] Thread-safe cache access with locks
- [ ] Proper indexes for query performance
- [ ] Hash-based change detection for efficiency
- [ ] Error handling with graceful fallback
- [ ] Atomic operations for data consistency

### Refresh Mechanism Checklist
- [ ] Background task runs on schedule
- [ ] Non-blocking (doesn't freeze UI)
- [ ] Error handling doesn't break app
- [ ] Proper logging for monitoring
- [ ] Exponential backoff on failures
- [ ] Cache invalidation on mutations

### Documentation Checklist
- [ ] User guide covers all new features
- [ ] Developer docs explain architecture
- [ ] API docs are auto-generated and accurate
- [ ] Migration guide for existing users
- [ ] Deployment instructions included
- [ ] Troubleshooting section provided

### Testing Checklist
- [ ] 90%+ backend cache code coverage
- [ ] 85%+ frontend cache code coverage
- [ ] E2E tests cover critical cache workflows
- [ ] Performance tests verify < 5 second refresh
- [ ] Offline mode tested
- [ ] Cache persistence tested

---

## Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| Local Cache Implementation | 10 | Database setup, models, operations |
| Background Refresh | 8 | Scheduler, API integration |
| Cache Persistence | 4 | Startup logic, corruption detection |
| Manual Refresh Button | 4 | UI component, integration |
| Testing Suite | 12 | Unit, integration, E2E tests |
| Documentation | 6 | User guide, developer docs |
| **Total** | **44 hours** | ~5.5 days actual work, ~8 business days calendar |

---

## Success Criteria

Phase 6 is complete when:

1. **Cache**: SQLite cache working with proper persistence
2. **Refresh**: Background refresh every 5-10 minutes
3. **Persistence**: Cache survives app restart
4. **Manual Refresh**: Button working, UI properly updated
5. **Testing**: 85%+ coverage achieved for new code
6. **Documentation**: Complete user and developer guides
7. **Performance**: Startup < 1 second with cache, refresh < 5 seconds
8. **Code Review**: Approved by testing-specialist and python-backend-engineer
9. **Production Ready**: All quality gates passed

---

## Final Validation Checklist

Before marking project complete, verify:

### Functional Requirements
- [ ] All 8 enhancement areas implemented and working
- [ ] Navigation restructuring complete and tested
- [ ] Collection page with all view modes functional
- [ ] Custom groups with drag-and-drop working
- [ ] Deployment Dashboard replacing /manage
- [ ] Multiple collections management working
- [ ] Artifact cards with ellipsis menu
- [ ] Unified modal with new tabs
- [ ] Caching system fully implemented

### Performance
- [ ] App startup with cache < 1 second
- [ ] Collection page load < 2 seconds
- [ ] Filters/search < 300ms response time
- [ ] Drag-and-drop smooth (60 fps)
- [ ] Deployment Dashboard summary < 100ms
- [ ] Cache refresh < 5 seconds non-blocking

### Quality
- [ ] Overall test coverage >= 85%
- [ ] Zero critical bugs reported
- [ ] Accessibility WCAG 2.1 AA verified
- [ ] TypeScript strict mode (no `any`)
- [ ] All code reviewed and approved
- [ ] Performance budgets met

### Documentation
- [ ] User guide complete
- [ ] Developer documentation complete
- [ ] API documentation accurate
- [ ] Migration guide provided
- [ ] Deployment procedures documented
- [ ] Troubleshooting guide included

### Deployment
- [ ] Migration scripts prepared
- [ ] Rollback procedures documented
- [ ] Data backup strategy confirmed
- [ ] Monitoring/alerting configured
- [ ] Performance baselines established

---

## Post-Launch Monitoring

### Metrics to Track
- Cache hit rate (target: > 95%)
- Background refresh success rate (target: > 99%)
- User adoption of new features (target: > 80% within 2 weeks)
- Performance metrics (target: maintain < 2s loads)
- Error rates for new features (target: < 0.1%)

### Support Documentation
- FAQ for common issues
- Video tutorials for key workflows
- Troubleshooting guide for errors
- Community forum for user discussion

---

## Orchestration Quick Reference

### Task Delegation Commands

Batch 1 (Parallel):
- **TASK-6.1** → `python-backend-engineer` (2.5h) - Local cache implementation
- **TASK-6.4** → `ui-engineer-enhanced` (1h) - Manual refresh button

Batch 2 (Sequential, after Batch 1):
- **TASK-6.2** → `python-backend-engineer` (2h) - Background refresh
- **TASK-6.3** → `python-backend-engineer` (1h) - Cache persistence

Batch 3 (Parallel, after Batch 2):
- **TASK-6.5** → `testing-specialist` (2h) - Comprehensive testing
- **TASK-6.6** → `documentation-writer` (1.5h) - Documentation

---

## Project Completion

Upon successful completion of all 6 phases with 65 story points of work:

1. **Merge to main**: All changes integrated to production branch
2. **Release**: Deploy to production environment
3. **Announce**: Communicate feature to users
4. **Support**: Monitor and provide support for 2 weeks
5. **Retrospective**: Team review lessons learned
6. **Plan Next**: Identify future enhancements

**Expected Timeline**: 6 weeks from Phase 1 start
**Team Required**: 4-5 developers (full-time equivalent)
**Estimated Budget**: ~300-400 development hours

---

## Post-Project Enhancements

Potential features for future phases:
- Artifact versioning within collections
- Collection sharing and permissions
- Advanced search with saved filters
- Deployment history and rollback
- Analytics on artifact usage
- Integration with CI/CD pipelines
- Mobile app support
- Offline-first support with sync
