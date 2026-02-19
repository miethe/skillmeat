---
prd: versioning-merge-system
total_phases: 11
priority_phases:
- 5
- 6
- 4
- 7
- 10
- 11
skip_phases: []
estimated_total_effort: 40h
last_updated: 2025-12-17
phase_execution_order:
- phase: 5
  status: complete
  effort: 0h
  priority: critical
  reason: Three-way merge engine complete with all tests
- phase: 6
  status: complete
  effort: 0h
  priority: critical
  reason: Intelligent rollback and VersionMergeService implemented
  blocks: []
- phase: 4
  status: complete
  effort: 0h
  priority: high
  reason: Auto-capture hooks and pagination implemented
  blocks: []
- phase: 1
  status: partial
  effort: 2h
  priority: medium
  reason: Storage schema completeness (optional - tarball works)
  blocks: []
- phase: 2
  status: partial
  effort: 3h
  priority: medium
  reason: Repository abstraction for cleaner separation
  blocks: []
- phase: 3
  status: partial
  effort: 3h
  priority: medium
  reason: Retention policies and lineage queries
  blocks: []
- phase: 7
  status: complete
  effort: 0h
  priority: high
  reason: REST API for version/merge operations complete
  depends_on:
  - 4
  - 6
  blocks:
  - 8
  - 9
  notes: 'Routers: versions.py, merge.py. Endpoints: /analyze, /preview, /execute,
    /resolve'
- phase: 8
  status: complete
  effort: 0h
  priority: medium
  reason: History tab UI complete
  depends_on:
  - 7
  notes: 'Components: VersionTimeline, RollbackDialog, VersionComparisonView, SnapshotHistoryTab,
    SnapshotMetadata'
- phase: 9
  status: complete
  effort: 0h
  priority: medium
  reason: Merge conflict resolution UI complete
  depends_on:
  - 7
  notes: '10 components: MergeWorkflowDialog, ConflictList, ConflictResolver, ColoredDiffViewer,
    etc.'
- phase: 10
  status: complete
  effort: 0h
  priority: high
  reason: Sync integration complete - all backend wired, minor UI gap documented
  depends_on:
  - 4
  - 6
  notes: '95% complete. Backend: three-way merge, auto-snapshot, rollback all working.
    Frontend: minor gap - merge button in SyncStatusTab shows ''Coming Soon'' due
    to snapshot ID vs version string mismatch.'
- phase: 11
  status: partial
  effort: 2h
  priority: medium
  reason: Documentation complete, tests remaining
  depends_on:
  - 7
  - 8
  - 9
  - 10
  notes: All 6 documentation tasks complete (2025-12-17). Unit/E2E tests deferred.
agent_assignments:
  phase_1:
  - python-backend-engineer
  phase_2:
  - python-backend-engineer
  phase_3:
  - python-backend-engineer
  phase_4:
  - python-backend-engineer
  phase_5: []
  phase_6:
  - python-backend-engineer
  - ultrathink-debugger
  phase_7:
  - python-backend-engineer
  phase_8:
  - ui-engineer-enhanced
  phase_9:
  - ui-engineer-enhanced
  phase_10:
  - python-backend-engineer
  phase_11:
  - python-backend-engineer
  - documentation-writer
schema_version: 2
doc_type: progress
feature_slug: versioning-merge-system
type: progress
---

# Versioning & Merge System - Work Plan

**PRD**: `docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
**Status**: 95% complete (7 phases complete: 4, 5, 6, 7, 8, 9, 10 | 3 phases partial: 1, 2, 3, 11 (docs done))
**Next Action**: Phase 11 tests (deferred) - ~2h remaining

---

## Architecture Context

**DEVIATION FROM PRD**: Implementation uses collection-level tarball snapshots (`~/.skillmeat/snapshots/{collection}/{timestamp}.tar.gz`) instead of per-artifact versioned directories. This is functionally equivalent but architecturally different. Decision: Keep tarball approach for v1.

**Core Components Built**:
- ✅ `MergeEngine` (433 lines) - Three-way merge with conflict detection
- ✅ `DiffEngine` (~400 lines) - File diffing
- ✅ `VersionGraphBuilder` (626 lines) - Cross-project tracking
- ✅ `SnapshotManager` (271 lines) - Tarball storage
- ✅ `VersionManager` (261 lines) - Service layer integration complete (Phase 4)
- ✅ `VersionMergeService` (~300 lines) - Merge orchestration layer (Phase 6)

---

## Critical Path (Minimum Viable)

Execute in order to get working version/merge system:

1. ✅ **Phase 6** - Rollback intelligence + VersionMergeService (COMPLETE)
2. ✅ **Phase 4** - Version capture on sync/deploy (COMPLETE)
3. ✅ **Phase 7** - REST API endpoints (COMPLETE)
4. ✅ **Phase 10** - Integrate into sync workflow (COMPLETE - 95%)
5. ⏳ **Phase 11** (3h) - Test & document

**Remaining MVP Effort**: 3h (Phase 11 only)

---

## Phase Execution Details

### Phase 5: Three-Way Merge Engine ✅ COMPLETE

**Status**: 100% complete
**Skip**: No work needed
**Files**: `skillmeat/core/merge_engine.py`, comprehensive tests
**Achievement**: Handles text/binary, conflict markers, atomic writes, 35+ test scenarios

---

### Phase 6: Rollback & Integration ✅ COMPLETE

**Status**: 100% complete
**Progress File**: `.claude/progress/versioning-merge-system/phase-6-progress.md`

**COMPLETED**:
- ✅ Intelligent `rollback()` with local change preservation via three-way diff
- ✅ Selective rollback (specific files/artifacts)
- ✅ `auto_snapshot()` in CollectionManager
- ✅ VersionGraphBuilder for cross-project tracking
- ✅ `VersionMergeService` with `merge_with_conflict_detection()` and `analyze_merge_safety()`
- ✅ Conflict detection pipeline integrated

**Files Created/Modified**:
- `skillmeat/core/version.py` - Enhanced VersionManager with intelligent rollback
- `skillmeat/core/version_merge.py` - VersionMergeService orchestration layer
- `tests/test_version_merge_service.py` - Service layer tests

**Agent**: python-backend-engineer

---

### Phase 4: Service Layer - Version Management ✅ COMPLETE

**Status**: 100% complete
**Progress File**: `.claude/progress/versioning-merge-system/phase-4-progress.md`

**COMPLETED**:
- ✅ VersionManager core operations (create, list, get, compare)
- ✅ Auto-capture hooks: `capture_version_on_sync()` and `capture_version_on_deploy()`
- ✅ Pagination for large histories with cursor-based `list_versions(cursor, limit)`
- ✅ Version lifecycle management integrated

**Files Created/Modified**:
- `skillmeat/core/version.py` - VersionManager with pagination
- `skillmeat/core/sync.py` - Auto-capture on sync
- `skillmeat/core/deployment.py` - Auto-capture on deploy

**Note**: Full retention policy (auto-cleanup) deferred to Phase 3 (optional).

**Agent**: python-backend-engineer

---

### Phase 1-3: Storage/Repository/Comparison (OPTIONAL)

**Combined Effort**: 8h
**Priority**: Medium (not blocking critical path)

**Phase 1** (2h): Complete TOML schema, optional per-artifact directories
**Phase 2** (3h): VersionRepository abstraction layer
**Phase 3** (3h): Retention policies, lineage queries

**Decision**: These improve architecture but aren't required for MVP. Consider post-MVP refactor.

---

### Phase 7: API Layer ✅ COMPLETE

**Status**: 100% complete
**Progress File**: `.claude/progress/versioning-merge-system/phase-7-progress.md`

**COMPLETED - REST Endpoints**:

**Version Management** (`/api/v1/versions/*`):
- ✅ `GET /versions/snapshots` - List snapshots with pagination
- ✅ `GET /versions/snapshots/{id}` - Get snapshot details
- ✅ `POST /versions/snapshots` - Create snapshot
- ✅ `DELETE /versions/snapshots/{id}` - Delete snapshot
- ✅ `GET /versions/snapshots/{id}/rollback-analysis` - Analyze rollback safety
- ✅ `POST /versions/snapshots/{id}/rollback` - Execute rollback
- ✅ `POST /versions/snapshots/diff` - Compare two snapshots

**Merge Operations** (`/api/v1/merge/*`):
- ✅ `POST /merge/analyze` - Analyze merge safety (dry-run)
- ✅ `POST /merge/preview` - Preview merge changes
- ✅ `POST /merge/execute` - Execute merge with conflict detection
- ✅ `POST /merge/resolve` - Resolve single conflict

**Files Created**:
- `skillmeat/api/routers/versions.py` - Version/snapshot endpoints
- `skillmeat/api/routers/merge.py` - Merge operation endpoints
- `skillmeat/api/schemas/version.py` - Pydantic schemas (Snapshot, Rollback, Diff)
- `skillmeat/api/schemas/merge.py` - Pydantic schemas (Analyze, Preview, Execute, Resolve)

**Agent**: python-backend-engineer

---

### Phase 8: Frontend History Tab ✅ COMPLETE

**Status**: 100% complete
**Progress File**: `.claude/progress/versioning-merge-system/phase-8-progress.md`

**COMPLETED - Components** (`skillmeat/web/components/history/`):
- ✅ `SnapshotHistoryTab` - Main tab container with snapshot list
- ✅ `VersionTimeline` - Timeline visualization of snapshots
- ✅ `VersionComparisonView` - Side-by-side snapshot comparison with diff stats
- ✅ `SnapshotMetadata` - Display snapshot details (timestamp, message, artifact count)
- ✅ `RollbackDialog` - Rollback confirmation with safety analysis

**Supporting Files**:
- ✅ `skillmeat/web/hooks/use-snapshots.ts` - TanStack Query hooks for snapshot operations
- ✅ `skillmeat/web/lib/api/snapshots.ts` - API client functions
- ✅ `skillmeat/web/types/snapshot.ts` - TypeScript interfaces

**Features Implemented**:
- View version history with pagination
- Compare two versions side-by-side with file diff visualization
- Rollback to previous version with safety checks
- Loading states, error handling, accessibility

**Agent**: ui-engineer-enhanced

---

### Phase 9: Frontend Merge UI ✅ COMPLETE

**Status**: 100% complete
**Progress File**: `.claude/progress/versioning-merge-system/phase-9-progress.md`

**COMPLETED - Components** (`skillmeat/web/components/merge/`):
- ✅ `MergeWorkflowDialog` - Multi-step workflow (Analyze → Preview → Resolve → Execute)
- ✅ `MergeAnalysisDialog` - Pre-merge safety check with warnings
- ✅ `MergePreviewView` - Preview files added/removed/changed
- ✅ `ConflictList` - List conflicts with type indicators
- ✅ `ConflictResolver` - Resolution controls (local/remote/base/custom)
- ✅ `ColoredDiffViewer` - Three-way diff with color coding
- ✅ `MergeStrategySelector` - Choose merge strategy (auto/manual/abort)
- ✅ `MergeProgressIndicator` - Multi-file merge progress
- ✅ `MergeResultToast` - Success/failure notifications

**Supporting Files**:
- ✅ `skillmeat/web/hooks/use-merge.ts` - TanStack Query hooks (analyze, preview, execute, resolve)
- ✅ `skillmeat/web/lib/api/merge.ts` - API client functions
- ✅ `skillmeat/web/types/merge.ts` - TypeScript interfaces

**Features Implemented**:
- Analyze merge safety before attempting
- Preview merge changes with color-coded file list
- Resolve conflicts with four options (local/remote/base/custom)
- Three-way diff viewer with color coding
- Multi-step workflow with progress tracking
- Toast notifications for results

**Agent**: ui-engineer-enhanced

---

### Phase 10: Sync Integration ✅ COMPLETE (100%)

**Status**: 100% complete
**Effort**: 0h (backend already implemented, frontend 30min)
**Progress File**: `.claude/progress/versioning-merge-system/phase-10-progress.md`
**Depends On**: Phase 4, Phase 6

**COMPLETED - Backend Integration**:

1. ✅ **Pre-Sync Snapshot** - `sync_from_project_with_rollback()` lines 651-658
2. ✅ **Conflict Detection** - `_sync_merge()` uses MergeEngine for three-way merge
3. ✅ **Post-Sync Version** - `auto_snapshot()` called after sync success (lines 993-1015)
4. ✅ **Rollback on Failure** - Automatic rollback in error handler (lines 711-729)
5. ✅ **Deploy Versioning** - `auto_snapshot()` in deployment.py (lines 248-267)
6. ✅ **CLI Integration** - `--with-rollback` flag in sync-pull command

**COMPLETED - Frontend Integration**:

- ✅ SyncStatusTab with drift detection, diff viewer, actions
- ✅ SyncDialog with ConflictResolver and progress indicator
- ✅ Merge button wired to SyncDialog (commit: d5a0107)

**Success Criteria**: 6/8 complete (SC-7, SC-8 deferred to Phase 11)

**Agent**: python-backend-engineer

---

### Phase 11: Testing & Documentation

**Status**: 61% complete (documentation done, tests deferred)
**Effort**: 2h remaining
**Progress File**: `.claude/progress/versioning-merge-system/phase-11-progress.md`
**Depends On**: Phase 7, 8, 9, 10

**DONE**:
- ✅ test_merge_engine.py (35+ scenarios)
- ✅ test_version_manager.py
- ✅ test_version_graph_builder.py
- ✅ DOC-001: API documentation (`docs/features/versioning/api-reference.md`)
- ✅ DOC-002: User guide for version history (`docs/features/versioning/user-guide-history.md`)
- ✅ DOC-003: User guide for merge workflow (`docs/features/versioning/user-guide-merge.md`)
- ✅ DOC-004: Architecture documentation (`docs/architecture/versioning/README.md`)
- ✅ DOC-005: Developer guide for version APIs (`docs/development/versioning/dev-guide-apis.md`)
- ✅ DOC-006: Developer guide for merge engine (`docs/developers/versioning/dev-guide-merge-engine.md`)

**DEFERRED** (tests - not blocking MVP):

1. **API Tests** (1h)
   - Test all 13 REST endpoints
   - File: `tests/test_api_versions.py`, `tests/test_api_merge.py`

2. **E2E Tests** (1h)
   - Full version/merge workflow
   - File: `tests/test_versioning_e2e.py`

**Success Criteria**:
- ⏳ 80%+ test coverage maintained
- ⏳ All API endpoints tested
- ⏳ E2E workflow tested
- ✅ User documentation complete
- ✅ API documentation complete
- ✅ Architecture documentation complete
- ✅ Developer guides complete

**Agent**: python-backend-engineer (tests), documentation-writer (docs - COMPLETE)

---

## Execution Commands for `/dev:execute-phase`

### Start Critical Path

```bash
# 1. Complete rollback intelligence (CRITICAL)
/dev:execute-phase 6

# 2. Wire version capture into lifecycle
/dev:execute-phase 4

# 3. Build REST API
/dev:execute-phase 7

# 4. Integrate into sync
/dev:execute-phase 10

# 5. Test & document
/dev:execute-phase 11
```

### Optional Architecture Improvements (Post-MVP)

```bash
/dev:execute-phase 1  # Storage schema
/dev:execute-phase 2  # Repository abstraction
/dev:execute-phase 3  # Retention policies
```

### Frontend (After API Complete)

```bash
/dev:execute-phase 8  # History tab
/dev:execute-phase 9  # Merge UI
```

---

## Key Files Reference

**Core** (All Complete):
- `skillmeat/core/merge_engine.py` - Three-way merge ✅
- `skillmeat/core/version.py` - VersionManager with pagination ✅
- `skillmeat/core/version_merge.py` - VersionMergeService ✅
- `skillmeat/core/sync.py` - SyncEngine with version integration ✅
- `skillmeat/core/snapshot.py` - SnapshotManager ✅

**API** (All Complete):
- `skillmeat/api/routers/versions.py` - Version/snapshot endpoints ✅
- `skillmeat/api/routers/merge.py` - Merge operation endpoints ✅
- `skillmeat/api/schemas/version.py` - Version schemas ✅
- `skillmeat/api/schemas/merge.py` - Merge schemas ✅

**Frontend** (All Complete):
- `skillmeat/web/components/history/*` - History tab components ✅
- `skillmeat/web/components/merge/*` - Merge UI components ✅
- `skillmeat/web/hooks/use-snapshots.ts` - Snapshot hooks ✅
- `skillmeat/web/hooks/use-merge.ts` - Merge hooks ✅
- `skillmeat/web/lib/api/snapshots.ts` - Snapshot API client ✅
- `skillmeat/web/lib/api/merge.ts` - Merge API client ✅
- `skillmeat/web/types/snapshot.ts` - Snapshot types ✅
- `skillmeat/web/types/merge.ts` - Merge types ✅

**Tests**:
- `tests/test_merge_engine.py` - Merge engine tests ✅
- `tests/test_version_manager.py` - VersionManager tests ✅
- `tests/test_version_graph_builder.py` - Graph builder tests ✅
- `tests/test_api_versions.py` (CREATE - Phase 11)
- `tests/test_versioning_e2e.py` (CREATE - Phase 11)

---

## Success Metrics

**MVP Complete When**:
1. ✅ Three-way merge working (Phase 5 - DONE)
2. ✅ Intelligent rollback preserves changes (Phase 6 - DONE)
3. ✅ Versions auto-captured on sync/deploy (Phase 4 - DONE)
4. ✅ REST API functional (Phase 7 - DONE)
5. ✅ Sync integrated with versioning (Phase 10 - DONE)
6. ⏳ Tests + docs complete (Phase 11 - DOCS DONE, tests deferred)

**Full Feature Complete When**:
- ✅ Frontend history UI working (Phase 8 - DONE)
- ✅ Frontend merge UI working (Phase 9 - DONE)
- ✅ User documentation complete (Phase 11 - DONE 2025-12-17)
- ✅ API documentation complete (Phase 11 - DONE 2025-12-17)
- ✅ Architecture documentation complete (Phase 11 - DONE 2025-12-17)
- ✅ Developer guides complete (Phase 11 - DONE 2025-12-17)
- ⏳ Retention policies active (Phase 3 - OPTIONAL)
- ⏳ 80%+ test coverage (Phase 11 - DEFERRED)

---

## Notes for Orchestration Agents

1. **Phases 4, 5, 6, 7, 8, 9, 10 are COMPLETE** - Core backend, API, frontend, and sync integration done
2. **Phase 11 documentation is COMPLETE** - All 6 docs created (2025-12-17)
3. **Phase 11 tests are DEFERRED** - API tests, E2E tests (~2h estimated)
4. **Phases 1-3 are OPTIONAL** - Improve architecture but not blocking MVP
5. **Use existing tests as examples** - test_merge_engine.py shows patterns
6. **Tarball approach is VALID** - Don't refactor to per-artifact unless directed

**Remaining Work**:
- Phase 11: API tests, E2E tests (~2h) - DEFERRED

**Known Limitations**: None - Phase 10 UI integration complete (d5a0107)

**Token Budget**: This work plan is designed for token-efficient execution. Each phase has detailed progress files with task breakdowns and orchestration commands. Use those for implementation details.

---

## Completion Notes

### Phase 4 Complete (2025-12-15)

- `_auto_capture_version()` added to sync.py
- `_capture_version_from_project()` added for project sync
- Integration with VersionManager for automatic snapshots
- Error handling: continues sync even if version capture fails

### Phase 7 Complete (2025-12-15)

- All REST endpoints implemented in `skillmeat/api/routers/version.py`
- All endpoints in `skillmeat/api/routers/merge.py`
- API error handling follows ErrorResponse pattern
- Cursor pagination implemented for list endpoints

### Phase 8 Complete (2025-12-16)

- HistoryTab component with version timeline
- VersionDetailDialog for inspection
- CompareVersionsDialog for diffs
- DateRangePicker and FilterBar for filtering
- All components integrated with backend API

### Phase 9 Complete (2025-12-16)

- MergeWorkflowDialog orchestrates full merge process
- ConflictList and ConflictResolver for conflict handling
- ColoredDiffViewer for visual diff display
- MergeProgressIndicator and MergeResultToast for feedback
- All hooks (use-merge.ts) connected to backend API

### Phase 10 Complete (2025-12-17)

- All backend sync integration already implemented (discovered during execution)
- `_sync_merge()` in sync.py uses MergeEngine for three-way merge
- `sync_from_project_with_rollback()` has pre-sync snapshot (lines 651-658)
- Post-sync auto_snapshot() called after success (lines 993-1015)
- Auto-rollback on failure (lines 711-729)
- `--with-rollback` flag in CLI sync-pull command
- Frontend: SyncStatusTab wired to SyncDialog for merge operations
- Added entityToArtifact() helper to bridge Entity/Artifact type mismatch
- Commit: d5a0107 feat(web): wire SyncDialog to merge button in SyncStatusTab

### Phase 11 Documentation Complete (2025-12-17)

- All 6 documentation tasks completed via documentation-writer subagent
- DOC-001: API reference with all 11 endpoints (`docs/features/versioning/api-reference.md`)
- DOC-002: User guide for version history (`docs/features/versioning/user-guide-history.md`)
- DOC-003: User guide for merge workflow (`docs/features/versioning/user-guide-merge.md`)
- DOC-004: Architecture documentation (`docs/architecture/versioning/README.md`)
- DOC-005: Developer guide for version APIs (`docs/development/versioning/dev-guide-apis.md`)
- DOC-006: Developer guide for merge engine (`docs/developers/versioning/dev-guide-merge-engine.md`)
- Test tasks (TEST-001 through TEST-012) deferred per user request
- Phase status: 61% complete (docs done, tests pending)
