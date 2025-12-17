---
type: progress
prd: versioning-merge-system-v1.5
phase: 6
title: "Testing & Validation"
status: pending
created: 2025-12-17
updated: 2025-12-17
duration_estimate: "2-3 days"
effort_estimate: "12-20h"
priority: HIGH

tasks:
  - id: "TASK-6.1"
    description: "Integration tests for deploy→sync→drift→merge workflow"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "3-4h"
    priority: "HIGH"
    files:
      - "tests/integration/test_version_workflow.py"

  - id: "TASK-6.2"
    description: "Integration tests for deploy→modify→sync→conflict workflow"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "3-4h"
    priority: "HIGH"
    files:
      - "tests/integration/test_conflict_workflow.py"

  - id: "TASK-6.3"
    description: "Performance tests for version chain queries"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "tests/performance/test_version_chain_performance.py"

  - id: "TASK-6.4"
    description: "Test migration from v1.0 deployments (no baseline)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2-3h"
    priority: "HIGH"
    files:
      - "tests/integration/test_migration_v1_0.py"

  - id: "TASK-6.5"
    description: "Manual testing of UI flows (diff viewer, version history)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2-3h"
    priority: "HIGH"
    files:
      - ".claude/worknotes/versioning-merge-system-v1.5/manual-testing-checklist.md"

  - id: "TASK-6.6"
    description: "Load testing with large version chains (100+ versions)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2-4h"
    priority: "MEDIUM"
    files:
      - "tests/performance/test_large_version_chains.py"

  - id: "TASK-6.7"
    description: "Documentation updates (API docs, user guides)"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: []
    estimated_effort: "3-5h"
    priority: "MEDIUM"
    files:
      - "docs/api/versioning.md"
      - "docs/guides/sync-and-merge.md"
      - "CHANGELOG.md"

parallelization:
  batch_1: ["TASK-6.1", "TASK-6.2", "TASK-6.3", "TASK-6.4", "TASK-6.5", "TASK-6.6", "TASK-6.7"]

completion: 0%
---

# Phase 6: Testing & Validation

## Overview

Comprehensive testing and validation of the versioning and merge system v1.5, including integration tests, performance tests, migration testing, and documentation updates.

**Goal**: Ensure system works correctly across all workflows and performs well at scale.

**Duration**: 2-3 days | **Effort**: 12-20h | **Priority**: HIGH

---

## Tasks

### TASK-6.1: Integration tests for deploy→sync→drift→merge workflow
**Status**: Pending | **Effort**: 3-4h | **Priority**: HIGH

**Description**:
Write end-to-end integration tests for the complete deploy→sync→drift→merge workflow, verifying that version chains are built correctly and merges use the correct baseline.

**Files**:
- `tests/integration/test_version_workflow.py`

**Test Scenarios**:

1. **Happy Path**: Deploy → Sync (no conflicts)
   - Deploy artifact v1.0 → baseline stored
   - Upstream changes to v1.1
   - Sync → three-way merge with correct baseline
   - No conflicts detected
   - Version chain: deploy → sync

2. **Upstream-only Changes**: Deploy → Sync (upstream changes)
   - Deploy artifact v1.0
   - Upstream changes v1.1
   - Drift detection shows upstream changes
   - Sync merges cleanly
   - Change origin: 'upstream'

3. **Multiple Syncs**: Deploy → Sync → Sync
   - Deploy v1.0 → baseline stored
   - Sync v1.1 → parent=v1.0
   - Sync v1.2 → parent=v1.1
   - Version lineage: [v1.0, v1.1, v1.2]

**Acceptance Criteria**:
- [ ] All scenarios pass
- [ ] Baseline retrieved correctly in all cases
- [ ] Version chains built correctly
- [ ] Three-way merge uses correct baseline
- [ ] No regressions in existing functionality

---

### TASK-6.2: Integration tests for deploy→modify→sync→conflict workflow
**Status**: Pending | **Effort**: 3-4h | **Priority**: HIGH

**Description**:
Write integration tests for conflict scenarios where both local and upstream changes occur.

**Files**:
- `tests/integration/test_conflict_workflow.py`

**Test Scenarios**:

1. **Local-only Changes**: Deploy → Local Modify → Drift
   - Deploy artifact v1.0
   - Modify locally (no sync)
   - Drift detection shows local changes
   - Change origin: 'local'
   - modification_detected_at set

2. **Conflict (Both Changed)**: Deploy → Local Modify → Upstream Change → Sync
   - Deploy artifact v1.0
   - Modify locally (same file)
   - Upstream changes same file
   - Drift detection shows both changed
   - Change origin: 'both' (conflict)
   - Sync requires manual merge

3. **Local Mod Version Record**: Deploy → Modify → Version Created
   - Deploy v1.0
   - Modify locally
   - ArtifactVersion created with change_origin='local_modification'
   - parent_hash=v1.0
   - Version lineage: [v1.0, local_hash]

**Acceptance Criteria**:
- [ ] All conflict scenarios handled correctly
- [ ] Local modifications create version records
- [ ] Change attribution correct (upstream, local, both)
- [ ] Conflicts detected and flagged
- [ ] Manual merge process works

---

### TASK-6.3: Performance tests for version chain queries
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Benchmark version chain queries to ensure performance is acceptable with long version histories.

**Files**:
- `tests/performance/test_version_chain_performance.py`

**Benchmarks**:

1. **Find Common Ancestor** (50 versions)
   - Create chain of 50 versions
   - Benchmark common ancestor search
   - Target: <50ms

2. **Build Version Lineage** (100 versions)
   - Create chain of 100 versions
   - Benchmark lineage building
   - Target: <100ms

3. **Drift Detection with Lineage** (50 versions)
   - Deploy + 50 syncs
   - Benchmark drift detection with lineage lookup
   - Target: <200ms

**Database Indexes**:
- Verify indexes on content_hash and parent_hash are used
- Check query plans with EXPLAIN

**Acceptance Criteria**:
- [ ] All benchmarks meet targets
- [ ] Indexes used by queries (EXPLAIN verification)
- [ ] No performance regression vs v1.0
- [ ] Performance acceptable at scale (100+ versions)

---

### TASK-6.4: Test migration from v1.0 deployments (no baseline)
**Status**: Pending | **Effort**: 2-3h | **Priority**: HIGH

**Description**:
Test backwards compatibility with v1.0 deployments that don't have `merge_base_snapshot` in metadata. Verify fallback logic works correctly.

**Files**:
- `tests/integration/test_migration_v1_0.py`

**Test Scenarios**:

1. **Old Deployment (No Baseline)**: Sync with fallback
   - Create deployment without merge_base_snapshot
   - Sync changes from upstream
   - Fallback logic finds common ancestor
   - Warning logged
   - Merge succeeds

2. **Mixed Deployments**: Old + New
   - Some deployments with baseline (v1.5)
   - Some without baseline (v1.0)
   - Sync works for both
   - Correct baseline/fallback used

3. **Gradual Migration**: Old → Modified → Sync (upgrade)
   - Old deployment (no baseline)
   - Sync once → v1.5 metadata added
   - Next sync uses correct baseline
   - No manual migration required

**Acceptance Criteria**:
- [ ] Old deployments work without errors
- [ ] Fallback logic finds reasonable baseline
- [ ] Warning logged for old deployments
- [ ] Gradual migration works (automatic upgrade)
- [ ] No data loss or corruption

---

### TASK-6.5: Manual testing of UI flows (diff viewer, version history)
**Status**: Pending | **Effort**: 2-3h | **Priority**: HIGH

**Description**:
Manual testing of web UI to verify change badges, tooltips, and version timeline display correctly.

**Files**:
- `.claude/worknotes/versioning-merge-system-v1.5/manual-testing-checklist.md`

**Test Checklist**:

1. **Diff Viewer**:
   - [ ] Change badges displayed for each file
   - [ ] Badge colors correct (upstream=blue, local=amber, both=red)
   - [ ] Tooltips show on hover
   - [ ] Tooltip content accurate
   - [ ] Responsive on mobile
   - [ ] Accessible (keyboard navigation)

2. **Version Timeline**:
   - [ ] Change origin labels shown
   - [ ] Colors match badge scheme
   - [ ] Timeline layout preserved
   - [ ] Responsive on mobile

3. **Summary Counts**:
   - [ ] Drift summary shows correct counts
   - [ ] Counts sum to total_files
   - [ ] Updates dynamically

4. **Edge Cases**:
   - [ ] No changes (all gray badges)
   - [ ] All conflicts (all red badges)
   - [ ] Mixed changes (multiple badge types)
   - [ ] Missing change_origin (graceful degradation)

**Testing Environment**:
- Desktop (Chrome, Firefox, Safari)
- Mobile (iOS Safari, Android Chrome)
- Screen reader (NVDA/JAWS)
- Keyboard-only navigation

**Acceptance Criteria**:
- [ ] All checklist items pass
- [ ] UI works across browsers
- [ ] Mobile experience good
- [ ] Accessible

---

### TASK-6.6: Load testing with large version chains (100+ versions)
**Status**: Pending | **Effort**: 2-4h | **Priority**: MEDIUM

**Description**:
Load testing to ensure system performs well with large version chains (100+ versions per artifact).

**Files**:
- `tests/performance/test_large_version_chains.py`

**Test Scenarios**:

1. **Create Large Chain** (100 versions)
   - Deploy artifact
   - Sync 100 times (simulate 100 upstream versions)
   - Measure total time
   - Target: <10s for chain creation

2. **Query Latest Version** (100 versions)
   - Chain of 100 versions
   - Query latest version
   - Target: <50ms

3. **Find Common Ancestor** (100 versions, 50-deep divergence)
   - Create two branches, each 50 versions deep
   - Find common ancestor
   - Target: <100ms

4. **Drift Detection** (100 versions)
   - Chain of 100 versions
   - Drift detection on latest
   - Target: <200ms

5. **API Response Time** (100 versions)
   - GET /api/v1/sync/drift (100 version chain)
   - Target: <500ms

**Acceptance Criteria**:
- [ ] All scenarios meet targets
- [ ] No memory leaks
- [ ] Database connections managed properly
- [ ] System stable under load

---

### TASK-6.7: Documentation updates (API docs, user guides)
**Status**: Pending | **Effort**: 3-5h | **Priority**: MEDIUM

**Description**:
Update documentation to reflect new versioning and change attribution features.

**Files**:
- `docs/api/versioning.md` - API reference for versioning endpoints
- `docs/guides/sync-and-merge.md` - User guide for sync and merge workflows
- `CHANGELOG.md` - Release notes for v1.5

**Documentation Updates**:

1. **API Reference** (`docs/api/versioning.md`):
   - Document new `change_origin` field in responses
   - Document `baseline_hash`, `current_hash` fields
   - Document `summary` counts in drift detection
   - Update examples with new fields

2. **User Guide** (`docs/guides/sync-and-merge.md`):
   - Explain change attribution (upstream, local, both)
   - Update screenshots with change badges
   - Add section on conflict resolution
   - Explain version timeline labels

3. **Changelog** (`CHANGELOG.md`):
   ```markdown
   ## [1.5.0] - 2025-12-XX

   ### Added
   - **Version Lineage Tracking**: Complete version history graph with parent-child relationships
   - **Change Attribution**: Distinguish upstream, local, and conflicting changes
   - **Baseline Storage**: Fix three-way merge by storing correct merge base
   - **Change Badges**: Visual indicators in UI showing change origin
   - **Version Timeline**: Show change origin labels in version history

   ### Fixed
   - Three-way merge now uses correct baseline (previously defaulted to empty)
   - Conflict detection accuracy improved

   ### Changed
   - Database schema: Added `change_origin` enum and indexes
   - API responses: Include `change_origin`, `baseline_hash`, `current_hash`
   ```

4. **Migration Guide** (optional):
   - Explain v1.0 → v1.5 upgrade process
   - Note: No manual migration required (automatic)
   - Fallback logic for old deployments

**Acceptance Criteria**:
- [ ] API docs updated with new fields
- [ ] User guide updated with screenshots
- [ ] Changelog complete
- [ ] Documentation accurate and clear
- [ ] Examples work (tested)

---

## Orchestration Quick Reference

**Batch 1** (All Parallel - Independent Testing):
- TASK-6.1 → `python-backend-engineer` (3-4h)
- TASK-6.2 → `python-backend-engineer` (3-4h)
- TASK-6.3 → `python-backend-engineer` (2-3h)
- TASK-6.4 → `python-backend-engineer` (2-3h)
- TASK-6.5 → `ui-engineer-enhanced` (2-3h)
- TASK-6.6 → `python-backend-engineer` (2-4h)
- TASK-6.7 → `documentation-writer` (3-5h)

### Task Delegation Commands

```python
# All tasks can run in parallel (batch 1)
Task("python-backend-engineer", """TASK-6.1: Integration tests for deploy→sync→drift→merge workflow

Files:
- tests/integration/test_version_workflow.py

Test Scenarios:
1. Happy path: Deploy → Sync (no conflicts)
2. Upstream-only changes: Drift shows upstream
3. Multiple syncs: Version chain builds correctly

Requirements:
- End-to-end workflow tests
- Baseline retrieved correctly
- Version chains built
- Three-way merge uses correct baseline

Coverage: All critical paths
""")

Task("python-backend-engineer", """TASK-6.2: Integration tests for deploy→modify→sync→conflict workflow

Files:
- tests/integration/test_conflict_workflow.py

Test Scenarios:
1. Local-only changes: Drift shows local
2. Conflict (both changed): Drift shows both
3. Local mod version record created

Requirements:
- Conflict scenarios handled
- Local mods create version records
- Change attribution correct
- Manual merge process works

Coverage: All conflict scenarios
""")

Task("python-backend-engineer", """TASK-6.3: Performance tests for version chain queries

Files:
- tests/performance/test_version_chain_performance.py

Benchmarks:
1. Find common ancestor (50 versions): <50ms
2. Build version lineage (100 versions): <100ms
3. Drift detection with lineage (50 versions): <200ms

Requirements:
- Meet performance targets
- Verify indexes used (EXPLAIN)
- No regression vs v1.0

Acceptance:
- All benchmarks pass
- Indexes used
- Performance acceptable
""")

Task("python-backend-engineer", """TASK-6.4: Test migration from v1.0 deployments (no baseline)

Files:
- tests/integration/test_migration_v1_0.py

Test Scenarios:
1. Old deployment (no baseline): Fallback works
2. Mixed deployments (old + new): Both work
3. Gradual migration: Automatic upgrade

Requirements:
- Old deployments work
- Fallback logic correct
- Warning logged
- No data loss

Acceptance:
- Backwards compatible
- Fallback works
- Gradual upgrade
""")

Task("ui-engineer-enhanced", """TASK-6.5: Manual testing of UI flows (diff viewer, version history)

Files:
- .claude/worknotes/versioning-merge-system-v1.5/manual-testing-checklist.md

Test Areas:
1. Diff viewer: Badges, tooltips
2. Version timeline: Labels, colors
3. Summary counts
4. Edge cases

Testing:
- Desktop browsers (Chrome, Firefox, Safari)
- Mobile (iOS, Android)
- Screen reader
- Keyboard navigation

Deliverable:
- Completed checklist
- Bug reports (if any)
""")

Task("python-backend-engineer", """TASK-6.6: Load testing with large version chains (100+ versions)

Files:
- tests/performance/test_large_version_chains.py

Test Scenarios:
1. Create large chain (100 versions): <10s
2. Query latest version (100 versions): <50ms
3. Find common ancestor (50-deep divergence): <100ms
4. Drift detection (100 versions): <200ms
5. API response time (100 versions): <500ms

Requirements:
- Meet all targets
- No memory leaks
- System stable

Acceptance:
- All scenarios pass
- Performance acceptable
- System stable
""")

Task("documentation-writer", """TASK-6.7: Documentation updates (API docs, user guides)

Files:
- docs/api/versioning.md
- docs/guides/sync-and-merge.md
- CHANGELOG.md

Updates:
1. API Reference:
   - Document change_origin field
   - Document baseline_hash, current_hash
   - Update examples

2. User Guide:
   - Explain change attribution
   - Update screenshots
   - Add conflict resolution section

3. Changelog:
   - Version 1.5.0 release notes
   - List new features
   - Note fixes and changes

Acceptance:
- Documentation accurate
- Examples work
- Clear and concise
""")
```

---

## Success Criteria

- [ ] All integration tests pass
- [ ] Performance benchmarks meet targets
- [ ] Migration from v1.0 works
- [ ] Manual UI testing complete (no critical bugs)
- [ ] Load testing passes (100+ versions)
- [ ] Documentation updated and accurate

---

## Dependencies

**Blocks**:
- Release of v1.5

**Blocked By**:
- All Phases 1-5 must be complete

---

## Notes

**Testing Priority**: Integration tests (6.1, 6.2) and migration tests (6.4) are HIGH priority. Performance tests (6.3, 6.6) are MEDIUM priority but important for production readiness.

**Manual Testing**: UI testing (6.5) should be done by a human tester, not automated. Create detailed checklist for reproducibility.

**Documentation**: Update docs before release to ensure users have up-to-date information.

**Release Blockers**: Tasks 6.1, 6.2, 6.4, 6.5, 6.7 are release blockers. Performance tests (6.3, 6.6) can be deferred if time-critical, but should be completed before v1.5.0 final release.
