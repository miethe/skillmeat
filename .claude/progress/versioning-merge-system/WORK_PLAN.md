---
prd: versioning-merge-system
total_phases: 11
priority_phases: [5, 6, 4, 7, 10, 11]  # Complete core, then API/frontend, then integration
skip_phases: []  # None - all phases needed
estimated_total_effort: 40h
last_updated: 2025-12-17

phase_execution_order:
  # Core Backend (finish foundation)
  - phase: 5
    status: complete
    effort: 0h
    priority: critical
    reason: "Three-way merge engine complete with all tests"

  - phase: 6
    status: complete
    effort: 0h
    priority: critical
    reason: "Intelligent rollback and VersionMergeService implemented"
    blocks: []

  - phase: 4
    status: complete
    effort: 0h
    priority: high
    reason: "Auto-capture hooks and pagination implemented"
    blocks: []

  - phase: 1
    status: partial
    effort: 2h
    priority: medium
    reason: "Storage schema completeness (optional - tarball works)"
    blocks: []

  - phase: 2
    status: partial
    effort: 3h
    priority: medium
    reason: "Repository abstraction for cleaner separation"
    blocks: []

  - phase: 3
    status: partial
    effort: 3h
    priority: medium
    reason: "Retention policies and lineage queries"
    blocks: []

  # API Layer
  - phase: 7
    status: complete
    effort: 0h
    priority: high
    reason: "REST API for version/merge operations complete"
    depends_on: [4, 6]
    blocks: [8, 9]
    notes: "Routers: versions.py, merge.py. Endpoints: /analyze, /preview, /execute, /resolve"

  # Frontend
  - phase: 8
    status: complete
    effort: 0h
    priority: medium
    reason: "History tab UI complete"
    depends_on: [7]
    notes: "Components: VersionTimeline, RollbackDialog, VersionComparisonView, SnapshotHistoryTab, SnapshotMetadata"

  - phase: 9
    status: complete
    effort: 0h
    priority: medium
    reason: "Merge conflict resolution UI complete"
    depends_on: [7]
    notes: "10 components: MergeWorkflowDialog, ConflictList, ConflictResolver, ColoredDiffViewer, etc."

  # Integration & Polish
  - phase: 10
    status: not_started
    effort: 4h
    priority: high
    reason: "Wire versioning into sync workflow"
    depends_on: [4, 6]

  - phase: 11
    status: partial
    effort: 3h
    priority: medium
    reason: "Complete test coverage and documentation"
    depends_on: [7, 8, 9, 10]

agent_assignments:
  phase_1: [python-backend-engineer]
  phase_2: [python-backend-engineer]
  phase_3: [python-backend-engineer]
  phase_4: [python-backend-engineer]
  phase_5: []  # COMPLETE
  phase_6: [python-backend-engineer, ultrathink-debugger]
  phase_7: [python-backend-engineer]
  phase_8: [ui-engineer-enhanced]
  phase_9: [ui-engineer-enhanced]
  phase_10: [python-backend-engineer]
  phase_11: [python-backend-engineer, documentation-writer]
---

# Versioning & Merge System - Work Plan

**PRD**: `docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
**Status**: 75% complete (6 phases complete: 4, 5, 6, 7, 8, 9 | 3 phases partial: 1, 2, 3 | 2 phases pending: 10, 11)
**Next Action**: Phase 10 (Sync integration) or Phase 11 (Testing & Documentation)

---

## Architecture Context

**DEVIATION FROM PRD**: Implementation uses collection-level tarball snapshots (`~/.skillmeat/snapshots/{collection}/{timestamp}.tar.gz`) instead of per-artifact versioned directories. This is functionally equivalent but architecturally different. Decision: Keep tarball approach for v1.

**Core Components Built**:
- ✅ `MergeEngine` (433 lines) - Three-way merge with conflict detection
- ✅ `DiffEngine` (~400 lines) - File diffing
- ✅ `VersionGraphBuilder` (626 lines) - Cross-project tracking
- ✅ `SnapshotManager` (271 lines) - Tarball storage
- ⚠️ `VersionManager` (261 lines) - Needs service layer integration
- ⚠️ `VersionMergeService` - Not yet created (Phase 6)

---

## Critical Path (Minimum Viable)

Execute in order to get working version/merge system:

1. **Phase 6** (6h) - Complete rollback intelligence + VersionMergeService
2. **Phase 4** (4h) - Wire version capture into sync/deploy
3. **Phase 7** (6h) - REST API endpoints
4. **Phase 10** (4h) - Integrate into sync workflow
5. **Phase 11** (3h) - Test & document

**Total MVP Effort**: 23h

---

## Phase Execution Details

### Phase 5: Three-Way Merge Engine ✅ COMPLETE

**Status**: 100% complete
**Skip**: No work needed
**Files**: `skillmeat/core/merge_engine.py`, comprehensive tests
**Achievement**: Handles text/binary, conflict markers, atomic writes, 35+ test scenarios

---

### Phase 6: Rollback & Integration (CRITICAL - START HERE)

**Status**: 40% complete
**Effort**: 6h
**Progress File**: `.claude/progress/versioning-merge-system/phase-6-progress.md`

**DONE**:
- Basic `rollback()` in VersionManager
- `auto_snapshot()` in CollectionManager
- VersionGraphBuilder for cross-project tracking

**REMAINING**:
1. **Intelligent Rollback** (2h)
   - Preserve local changes (detect via diff)
   - Selective rollback (specific files/artifacts)
   - File: `skillmeat/core/version.py`

2. **VersionMergeService** (3h) - NEW FILE
   - `merge_with_conflict_detection()`
   - `analyze_merge_safety()`
   - Integration layer between VersionManager + MergeEngine
   - File: `skillmeat/core/version_merge.py`

3. **Conflict Detection Pipeline** (1h)
   - Wire into sync/deploy operations
   - File: `skillmeat/core/artifact.py`

**Success Criteria**:
- `rollback()` preserves uncommitted changes
- `VersionMergeService` detects conflicts before attempting merge
- Tests: test_intelligent_rollback.py, test_version_merge_service.py

**Agent**: python-backend-engineer

---

### Phase 4: Service Layer - Version Management

**Status**: 40% complete
**Effort**: 4h
**Progress File**: `.claude/progress/versioning-merge-system/phase-4-progress.md`

**DONE**:
- VersionManager core operations (create, list, get, compare)

**REMAINING**:
1. **Auto-capture Hooks** (2h)
   - `capture_version_on_sync()` in SyncEngine
   - `capture_version_on_deploy()` in DeploymentManager
   - Files: `skillmeat/core/sync.py`, `skillmeat/core/deployment.py`

2. **Pagination for Large Histories** (1h)
   - `list_versions(cursor, limit)`
   - File: `skillmeat/core/version.py`

3. **Version Lifecycle** (1h)
   - Auto-cleanup old versions (retention policy from Phase 3)
   - File: `skillmeat/core/version.py`

**Success Criteria**:
- Sync creates versions automatically
- Deploy creates versions automatically
- `list_versions()` supports pagination

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

### Phase 7: API Layer (BLOCKS FRONTEND)

**Status**: 0% complete
**Effort**: 6h
**Progress File**: `.claude/progress/versioning-merge-system/phase-7-progress.md`
**Depends On**: Phase 4, Phase 6

**Create 13 REST Endpoints**:

**Version Management** (4 endpoints):
- `GET /api/v1/versions` - List versions
- `GET /api/v1/versions/{version_id}` - Get version
- `POST /api/v1/versions` - Create version
- `POST /api/v1/versions/{version_id}/rollback` - Rollback

**Comparison** (3 endpoints):
- `GET /api/v1/versions/{v1}/compare/{v2}` - Compare versions
- `GET /api/v1/artifacts/{id}/diff` - Diff artifact states
- `GET /api/v1/versions/{version_id}/changes` - Show changes

**Merge** (6 endpoints):
- `POST /api/v1/merge/analyze` - Analyze merge safety
- `POST /api/v1/merge/execute` - Execute merge
- `GET /api/v1/merge/conflicts/{merge_id}` - List conflicts
- `POST /api/v1/merge/conflicts/{conflict_id}/resolve` - Resolve conflict
- `POST /api/v1/merge/preview` - Preview merge result
- `GET /api/v1/merge/status/{merge_id}` - Check status

**Files to Create**:
- `skillmeat/api/routers/versions.py` (version management endpoints)
- `skillmeat/api/routers/merge.py` (merge endpoints)
- `skillmeat/api/schemas/version.py` (Pydantic schemas)
- `skillmeat/api/schemas/merge.py` (Pydantic schemas)

**Success Criteria**:
- All 13 endpoints return correct status codes
- OpenAPI docs generated
- Error handling per router patterns

**Agent**: python-backend-engineer

---

### Phase 8: Frontend History Tab

**Status**: 0% complete
**Effort**: 5h
**Progress File**: `.claude/progress/versioning-merge-system/phase-8-progress.md`
**Depends On**: Phase 7

**Create 10 Components** (Next.js + Radix UI):
1. `VersionHistoryTab.tsx` - Main tab container
2. `VersionList.tsx` - Timeline of versions
3. `VersionCard.tsx` - Single version display
4. `VersionCompareDialog.tsx` - Side-by-side comparison
5. `FileChangesList.tsx` - List of changed files
6. `FileDiffViewer.tsx` - Syntax-highlighted diff
7. `RollbackDialog.tsx` - Rollback confirmation
8. `VersionFilters.tsx` - Filter by date/artifact
9. `VersionSearch.tsx` - Search versions
10. `VersionStats.tsx` - Stats dashboard

**Files to Create**:
- `web/components/versions/*` (10 components)
- `web/hooks/use-versions.ts` (TanStack Query)
- `web/lib/api/versions.ts` (API client)
- `web/types/version.ts` (TypeScript types)

**Success Criteria**:
- View version history with pagination
- Compare two versions side-by-side
- Rollback to previous version
- Filter and search versions

**Agent**: ui-engineer-enhanced

---

### Phase 9: Frontend Merge UI

**Status**: 0% complete
**Effort**: 6h
**Progress File**: `.claude/progress/versioning-merge-system/phase-9-progress.md`
**Depends On**: Phase 7

**Create 10 Components**:
1. `MergeAnalysisDialog.tsx` - Pre-merge safety check
2. `MergeConflictView.tsx` - Main conflict resolution UI
3. `ConflictList.tsx` - List of conflicts
4. `ConflictEditor.tsx` - Three-pane editor (theirs/base/yours)
5. `ConflictResolutionControls.tsx` - Accept theirs/ours/manual
6. `MergePreviewDialog.tsx` - Preview before commit
7. `MergeProgressIndicator.tsx` - Show progress
8. `MergeStrategySelector.tsx` - Choose merge strategy
9. `MergeHistoryDialog.tsx` - View past merges
10. `MergeSafetyWarnings.tsx` - Show warnings

**Files to Create**:
- `web/components/merge/*` (10 components)
- `web/hooks/use-merge.ts` (TanStack Query)
- `web/lib/api/merge.ts` (API client)
- `web/types/merge.ts` (TypeScript types)

**Success Criteria**:
- Analyze merge safety before attempting
- Resolve conflicts with three-pane editor
- Preview merge result
- Execute merge with conflict resolution

**Agent**: ui-engineer-enhanced

---

### Phase 10: Sync Integration

**Status**: 0% complete
**Effort**: 4h
**Progress File**: `.claude/progress/versioning-merge-system/phase-10-progress.md`
**Depends On**: Phase 4, Phase 6

**Wire Versioning into Sync Workflow**:

1. **Pre-Sync Snapshot** (1h)
   - Auto-capture version before sync
   - File: `skillmeat/core/sync.py`

2. **Conflict Detection** (1h)
   - Detect local changes vs remote changes
   - Trigger merge workflow if conflicts
   - File: `skillmeat/core/sync.py`

3. **Post-Sync Version** (1h)
   - Capture version after successful sync
   - File: `skillmeat/core/sync.py`

4. **Rollback on Failure** (1h)
   - Auto-rollback if sync fails
   - File: `skillmeat/core/sync.py`

**Files to Modify**:
- `skillmeat/core/sync.py` (add versioning hooks)
- `skillmeat/cli.py` (update sync command output)

**Success Criteria**:
- Sync creates pre/post versions
- Conflicts trigger merge workflow
- Failed syncs rollback automatically

**Agent**: python-backend-engineer

---

### Phase 11: Testing & Documentation

**Status**: 30% complete
**Effort**: 3h
**Progress File**: `.claude/progress/versioning-merge-system/phase-11-progress.md`
**Depends On**: Phase 7, 8, 9, 10

**DONE**:
- ✅ test_merge_engine.py (35+ scenarios)
- ✅ test_version_manager.py
- ✅ test_version_graph_builder.py

**REMAINING**:

1. **API Tests** (1h)
   - Test all 13 REST endpoints
   - File: `tests/test_api_versions.py`, `tests/test_api_merge.py`

2. **E2E Tests** (1h)
   - Full version/merge workflow
   - File: `tests/test_versioning_e2e.py`

3. **Documentation** (1h)
   - User guide for version/merge
   - API documentation
   - File: `docs/features/versioning-merge.md`

**Success Criteria**:
- 80%+ test coverage maintained
- All API endpoints tested
- E2E workflow tested
- User documentation complete

**Agent**: python-backend-engineer, documentation-writer

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

**Core**:
- `skillmeat/core/merge_engine.py` - Three-way merge (COMPLETE)
- `skillmeat/core/version.py` - VersionManager (NEEDS: Phase 4, 6)
- `skillmeat/core/version_merge.py` - VersionMergeService (NEEDS: Phase 6)
- `skillmeat/core/sync.py` - SyncEngine (NEEDS: Phase 10)

**API** (Phase 7):
- `skillmeat/api/routers/versions.py` (CREATE)
- `skillmeat/api/routers/merge.py` (CREATE)

**Frontend** (Phase 8, 9):
- `web/components/versions/*` (CREATE)
- `web/components/merge/*` (CREATE)

**Tests**:
- `tests/test_merge_engine.py` (COMPLETE)
- `tests/test_api_versions.py` (CREATE - Phase 11)
- `tests/test_versioning_e2e.py` (CREATE - Phase 11)

---

## Success Metrics

**MVP Complete When**:
1. ✅ Three-way merge working (DONE)
2. ⏳ Intelligent rollback preserves changes (Phase 6)
3. ⏳ Versions auto-captured on sync/deploy (Phase 4)
4. ⏳ REST API functional (Phase 7)
5. ⏳ Sync integrated with versioning (Phase 10)
6. ⏳ Tests + docs complete (Phase 11)

**Full Feature Complete When**:
- Frontend history/merge UI working (Phase 8, 9)
- Retention policies active (Phase 3)
- 80%+ test coverage (Phase 11)

---

## Notes for Orchestration Agents

1. **Phase 5 is COMPLETE** - No work needed, skip execution
2. **Start with Phase 6** - Unblocks critical path (Phase 7, 10)
3. **Phases 1-3 are OPTIONAL** - Improve architecture but not blocking
4. **Frontend blocked until Phase 7** - API must exist first
5. **Use existing tests as examples** - test_merge_engine.py shows patterns
6. **Tarball approach is VALID** - Don't refactor to per-artifact unless directed

**Token Budget**: This work plan is designed for token-efficient execution. Each phase has detailed progress files with task breakdowns and orchestration commands. Use those for implementation details.
