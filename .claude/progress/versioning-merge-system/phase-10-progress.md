---
type: progress
prd: "versioning-merge-system"
phase: 10
title: "Sync Workflow Integration"
status: "pending"
started: null
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["python-backend-engineer", "ui-engineer-enhanced"]
contributors: ["frontend-developer"]
duration_days: "3-4"
dependencies:
  - phase_7
  - phase_9

tasks:
  - id: "SYNC-INT-001"
    description: "Wire three-way merge to upstream sync (Source→Collection)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MERGE-UI-007"]
    estimated_effort: "4 points"
    priority: "high"

  - id: "SYNC-INT-002"
    description: "Wire three-way merge to deploy sync (Collection→Project)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MERGE-UI-007"]
    estimated_effort: "4 points"
    priority: "high"

  - id: "SYNC-INT-003"
    description: "Wire three-way merge to pull sync (Project→Collection)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MERGE-UI-007"]
    estimated_effort: "4 points"
    priority: "high"

  - id: "SYNC-INT-004"
    description: "Enhance SyncStatusTab with merge display"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["MERGE-UI-001"]
    estimated_effort: "4 points"
    priority: "high"

  - id: "SYNC-INT-005"
    description: "Redesign sync dialogs for unified merge workflow"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-INT-004"]
    estimated_effort: "3 points"
    priority: "medium"

  - id: "SYNC-INT-006"
    description: "Auto-capture version on sync completion"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVCV-002"]
    estimated_effort: "2 points"
    priority: "high"

  - id: "SYNC-INT-007"
    description: "Add merge-specific error handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["MERGE-UI-009"]
    estimated_effort: "2 points"
    priority: "medium"

  - id: "SYNC-INT-008"
    description: "Add merge undo/rollback capability after sync"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["MERGE-UI-009"]
    estimated_effort: "2 points"
    priority: "medium"

parallelization:
  batch_1: ["SYNC-INT-001", "SYNC-INT-002", "SYNC-INT-003", "SYNC-INT-004"]
  batch_2: ["SYNC-INT-005", "SYNC-INT-006", "SYNC-INT-007", "SYNC-INT-008"]
  critical_path: ["SYNC-INT-001", "SYNC-INT-005"]
  estimated_total_time: "3-4d"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "All sync directions support three-way merge"
    status: "pending"
  - id: "SC-2"
    description: "Sync Status tab shows merge information clearly"
    status: "pending"
  - id: "SC-3"
    description: "Merge preview accurate for all sync types"
    status: "pending"
  - id: "SC-4"
    description: "Versions automatically created on sync"
    status: "pending"
  - id: "SC-5"
    description: "Error handling covers all failure cases"
    status: "pending"
  - id: "SC-6"
    description: "No breaking changes to existing sync behavior"
    status: "pending"
  - id: "SC-7"
    description: "Integration tests for all sync directions"
    status: "pending"
  - id: "SC-8"
    description: "User testing confirms merge workflow clear"
    status: "pending"
---

# versioning-merge-system - Phase 10: Sync Workflow Integration

**Phase**: 10 of 10
**Status**: ⏳ Pending (0% complete)
**Duration**: 3-4 days
**Owners**: python-backend-engineer, ui-engineer-enhanced
**Contributors**: frontend-developer

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - Core Sync Integrations, 4-6 hours):
- SYNC-INT-001 → `python-backend-engineer` (4 points) - Wire three-way merge to upstream sync - **Blocked by**: MERGE-UI-007
- SYNC-INT-002 → `python-backend-engineer` (4 points) - Wire three-way merge to deploy sync - **Blocked by**: MERGE-UI-007
- SYNC-INT-003 → `python-backend-engineer` (4 points) - Wire three-way merge to pull sync - **Blocked by**: MERGE-UI-007
- SYNC-INT-004 → `ui-engineer-enhanced` (4 points) - Enhance SyncStatusTab with merge display - **Blocked by**: MERGE-UI-001

**Batch 2** (Sequential - Polish & Error Handling, 3-4 hours after Batch 1):
- SYNC-INT-005 → `ui-engineer-enhanced` (3 points) - Redesign sync dialogs for unified merge workflow - **Blocked by**: SYNC-INT-004
- SYNC-INT-006 → `python-backend-engineer` (2 points) - Auto-capture version on sync completion - **Blocked by**: SVCV-002
- SYNC-INT-007 → `python-backend-engineer` (2 points) - Add merge-specific error handling - **Blocked by**: MERGE-UI-009
- SYNC-INT-008 → `frontend-developer` (2 points) - Add merge undo/rollback capability after sync - **Blocked by**: MERGE-UI-009

**Critical Path**: SYNC-INT-001 → SYNC-INT-005 (7 points, ~7-8 hours)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("python-backend-engineer", "SYNC-INT-001: Wire three-way merge to upstream sync (Source→Collection). Update sync_upstream() in skillmeat/core/sync.py to invoke merge when conflicts detected. Apply merge result to collection, update lock file with merged state. Test: upstream_sync_with_conflict")

Task("python-backend-engineer", "SYNC-INT-002: Wire three-way merge to deploy sync (Collection→Project). Update sync_deploy() in skillmeat/core/sync.py to invoke merge when conflicts detected. Apply merge result to project deployment, update project lock file. Test: deploy_sync_with_conflict")

Task("python-backend-engineer", "SYNC-INT-003: Wire three-way merge to pull sync (Project→Collection). Update sync_pull() in skillmeat/core/sync.py to invoke merge when conflicts detected. Apply merge result to collection, ensure no data loss. Test: pull_sync_with_conflict")

Task("ui-engineer-enhanced", "SYNC-INT-004: Enhance SyncStatusTab with merge display. Update skillmeat/web/components/entity/sync-status-tab.tsx to show merge status, versions, conflict count, and merge preview. Use MergeStatusIndicator and MergePreview components from Phase 8-9. Test: sync_status_merge_display")

# Batch 2 (After Batch 1 completes)
Task("ui-engineer-enhanced", "SYNC-INT-005: Redesign sync dialogs for unified merge workflow. Update sync confirmation dialogs to show merge resolution option, display merge preview, allow review before sync. Update error dialogs for merge-related errors. Ensure all three sync types use unified design.")

Task("python-backend-engineer", "SYNC-INT-006: Auto-capture version on sync completion. Hook sync completion to version capture system. Create version entry with sync metadata (source, direction, merge info). Include merge decision and resolved conflicts in version metadata.")

Task("python-backend-engineer", "SYNC-INT-007: Add merge-specific error handling. Handle merge timeout, invalid merge state, metadata corruption. Add MergeConflictUnresolvable, MergeStateInvalid exceptions. Provide user-friendly error messages, comprehensive logging.")

Task("frontend-developer", "SYNC-INT-008: Add merge undo/rollback capability after sync. Add 'Undo Sync' button to SyncStatusTab. Implement sync undo in skillmeat/core/sync.py to restore pre-sync states. Support all three sync directions. Test: sync_undo_workflow")
```

---

## Overview

Phase 10 integrates the three-way merge system into all sync workflows (upstream, deploy, pull). This phase wires merge resolution into the sync execution path, enhances the SyncStatusTab to display merge information, redesigns sync dialogs for a unified merge workflow, and adds version capture and error handling for sync operations.

**Why This Phase**: Sync workflows are the primary way users synchronize artifacts across collection and projects. Integrating merge into sync makes conflict resolution transparent and automated, allowing users to confidently sync even when conflicts exist.

**Scope**:
- ✅ **IN SCOPE**: Wire merge to three sync directions, SyncStatusTab merge display, sync dialog redesign, auto-version capture, merge error handling, sync undo capability
- ❌ **OUT OF SCOPE**: New sync types, deployment strategies, version retention policies (Phase 3), change propagation beyond direct sync (Phase 11)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | All sync directions support three-way merge | ⏳ Pending |
| SC-2 | Sync Status tab shows merge information clearly | ⏳ Pending |
| SC-3 | Merge preview accurate for all sync types | ⏳ Pending |
| SC-4 | Versions automatically created on sync | ⏳ Pending |
| SC-5 | Error handling covers all failure cases | ⏳ Pending |
| SC-6 | No breaking changes to existing sync behavior | ⏳ Pending |
| SC-7 | Integration tests for all sync directions | ⏳ Pending |
| SC-8 | User testing confirms merge workflow clear | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Priority |
|----|------|--------|-------|--------------|-----|----------|
| SYNC-INT-001 | Wire three-way merge to upstream sync | ⏳ | python-backend-engineer | MERGE-UI-007 | 4pt | High |
| SYNC-INT-002 | Wire three-way merge to deploy sync | ⏳ | python-backend-engineer | MERGE-UI-007 | 4pt | High |
| SYNC-INT-003 | Wire three-way merge to pull sync | ⏳ | python-backend-engineer | MERGE-UI-007 | 4pt | High |
| SYNC-INT-004 | Enhance SyncStatusTab with merge display | ⏳ | ui-engineer-enhanced | MERGE-UI-001 | 4pt | High |
| SYNC-INT-005 | Redesign sync dialogs for unified merge workflow | ⏳ | ui-engineer-enhanced | SYNC-INT-004 | 3pt | Medium |
| SYNC-INT-006 | Auto-capture version on sync completion | ⏳ | python-backend-engineer | SVCV-002 | 2pt | High |
| SYNC-INT-007 | Add merge-specific error handling | ⏳ | python-backend-engineer | MERGE-UI-009 | 2pt | Medium |
| SYNC-INT-008 | Add merge undo/rollback capability after sync | ⏳ | frontend-developer | MERGE-UI-009 | 2pt | Medium |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Completed Tasks

(None yet - Phase 10 not started)

---

## In Progress

(None yet - Phase 10 not started)

---

## Blocked Tasks

(None)

---

## Detailed Task Specifications

### SYNC-INT-001: Wire Three-Way Merge to Upstream Sync

**Status**: Pending
**Est**: 4 points
**Assigned to**: python-backend-engineer
**Dependencies**: MERGE-UI-007 (Phase 7 merge resolution system)

Wire the three-way merge resolution into the Source→Collection upstream sync workflow:

**What to do:**
- Update `sync_upstream()` in `skillmeat/core/sync.py` to invoke three-way merge when conflicts detected
- Use existing merge LCA (lowest common ancestor) computation from Phase 7
- Handle merge resolution results and apply to collection artifact
- Update lock file with merged state
- Add merge metadata to sync operation result
- Test with artifacts from multiple sources

**Definition of Done**:
- Upstream sync invokes three-way merge on conflict
- Merge result correctly applied to collection
- Lock file reflects merged state
- Integration test passes: `test_upstream_sync_with_conflict`
- No regression in non-conflict upstream sync paths

**Key Files**:
- `skillmeat/core/sync.py` (update `sync_upstream()`)
- `skillmeat/core/merge.py` (reference from Phase 7)
- `tests/integration/test_sync_upstream_merge.py` (new test)

---

### SYNC-INT-002: Wire Three-Way Merge to Deploy Sync

**Status**: Pending
**Est**: 4 points
**Assigned to**: python-backend-engineer
**Dependencies**: MERGE-UI-007 (Phase 7 merge resolution system)

Wire the three-way merge resolution into the Collection→Project deploy sync workflow:

**What to do:**
- Update `sync_deploy()` in `skillmeat/core/sync.py` to invoke three-way merge when conflicts detected
- Handle merge resolution results and apply to project deployment
- Update project's internal lock file with merged state
- Add merge metadata to deploy sync result
- Ensure version on merge completion is captured (pre-work for SYNC-INT-006)
- Test with multiple deployment scenarios

**Definition of Done**:
- Deploy sync invokes three-way merge on conflict
- Merge result correctly applied to project
- Project lock file reflects merged state
- Integration test passes: `test_deploy_sync_with_conflict`
- No regression in non-conflict deploy sync paths

**Key Files**:
- `skillmeat/core/sync.py` (update `sync_deploy()`)
- `skillmeat/api/routers/projects.py` (may need updates if sync is called from API)
- `tests/integration/test_sync_deploy_merge.py` (new test)

---

### SYNC-INT-003: Wire Three-Way Merge to Pull Sync

**Status**: Pending
**Est**: 4 points
**Assigned to**: python-backend-engineer
**Dependencies**: MERGE-UI-007 (Phase 7 merge resolution system)

Wire the three-way merge resolution into the Project→Collection pull sync workflow:

**What to do:**
- Update `sync_pull()` in `skillmeat/core/sync.py` to invoke three-way merge when conflicts detected
- Handle merge resolution results and apply to collection artifact
- Update collection's manifest and lock file with merged state
- Add merge metadata to pull sync result
- Test with local project modifications pulled back to collection
- Ensure no data loss during merge

**Definition of Done**:
- Pull sync invokes three-way merge on conflict
- Merge result correctly applied to collection
- Collection files reflect merged state
- Integration test passes: `test_pull_sync_with_conflict`
- No regression in non-conflict pull sync paths

**Key Files**:
- `skillmeat/core/sync.py` (update `sync_pull()`)
- `tests/integration/test_sync_pull_merge.py` (new test)

---

### SYNC-INT-004: Enhance SyncStatusTab with Merge Display

**Status**: Pending
**Est**: 4 points
**Assigned to**: ui-engineer-enhanced
**Dependencies**: MERGE-UI-001 (Phase 8 MergeStatusIndicator component)

Enhance the SyncStatusTab component to display merge information when applicable:

**What to do:**
- Add merge section to SyncStatusTab showing:
  - Merge status (in progress, resolved, conflicted)
  - Source, base, target artifact versions
  - Resolved conflicts count
  - Merge decision (automatic or manual)
- Display merge preview when merge is in progress
- Show merge result summary after sync completes
- Add visual indicators for merge state (icons, colors, badges)
- Integrate with existing sync status display
- Test with all three sync directions

**Definition of Done**:
- SyncStatusTab displays merge information
- Merge preview renders correctly in tab context
- Visual indicators are clear and accessible
- Component test passes: `test_sync_status_merge_display`
- Integration test passes: `test_sync_ui_merge_integration`
- Responsive design works on mobile

**Key Files**:
- `skillmeat/web/components/entity/sync-status-tab.tsx` (update)
- `skillmeat/web/components/merge/merge-status-indicator.tsx` (reference from Phase 8)
- `skillmeat/web/components/merge/merge-preview.tsx` (reference from Phase 9)
- `tests/components/SyncStatusTab.test.tsx` (new test)

---

### SYNC-INT-005: Redesign Sync Dialogs for Unified Merge Workflow

**Status**: Pending
**Est**: 3 points
**Assigned to**: ui-engineer-enhanced
**Dependencies**: SYNC-INT-004 (SyncStatusTab merge display)

Redesign sync confirmation/result dialogs to present unified merge workflow:

**What to do:**
- Update sync dialog to show merge resolution option before confirming sync
- Display merge preview in dialog
- Allow user to review changes before sync completes
- Show conflict resolution strategy (auto/manual)
- Display merged artifact diff in dialog
- Add "Review Merge" button leading to MergeViewer
- Update error dialogs to show merge-related errors clearly
- Ensure dialogs work across all three sync types
- Add help text explaining merge workflow

**Definition of Done**:
- Sync dialogs show merge resolution option
- Merge preview renders in dialog
- User can review before confirming sync
- All three sync types use unified dialog
- Component test passes: `test_sync_dialog_merge_workflow`
- Accessibility review passes (WCAG 2.1 AA)
- Help text is clear and discoverable

**Key Files**:
- `skillmeat/web/components/modals/sync-dialog.tsx` (main dialog)
- `skillmeat/web/components/modals/sync-result-dialog.tsx` (result dialog)
- `skillmeat/web/components/modals/sync-error-dialog.tsx` (error dialog)
- `tests/components/SyncDialog.test.tsx` (update)

---

### SYNC-INT-006: Auto-Capture Version on Sync Completion

**Status**: Pending
**Est**: 2 points
**Assigned to**: python-backend-engineer
**Dependencies**: SVCV-002 (Phase 11 version capture system - may need to coordinate)

Automatically capture and create version when sync (with or without merge) completes successfully:

**What to do:**
- Hook sync completion to version capture system
- Create version entry with sync metadata (source, direction, merge info)
- Include merge decision and resolved conflicts in version metadata
- Add version metadata to sync result
- Support version capture for all three sync directions
- Ensure version is only created on successful sync

**Definition of Done**:
- Version created after successful sync
- Version metadata includes sync details and merge info
- Works for all sync directions (upstream, deploy, pull)
- Integration test passes: `test_sync_auto_version_capture`
- Version ID is deterministic and sortable

**Key Files**:
- `skillmeat/core/sync.py` (add version capture hook)
- `skillmeat/core/version.py` (reference version capture API)
- `tests/integration/test_sync_auto_version.py` (new test)

---

### SYNC-INT-007: Add Merge-Specific Error Handling

**Status**: Pending
**Est**: 2 points
**Assigned to**: python-backend-engineer
**Dependencies**: MERGE-UI-009 (Phase 9 merge error handling)

Add comprehensive error handling for merge-specific failure cases in sync:

**What to do:**
- Handle merge timeout scenarios
- Handle invalid merge state scenarios
- Handle merge metadata corruption
- Add specific error types: MergeConflictUnresolvable, MergeStateInvalid, etc.
- Provide user-friendly error messages
- Add logging for merge-related errors
- Ensure rollback on merge failure

**Definition of Done**:
- All merge error cases handled gracefully
- Error messages are user-friendly and actionable
- Logging captures merge failure details for debugging
- Unit test passes: `test_merge_error_handling`
- Rollback on merge failure leaves system in consistent state

**Key Files**:
- `skillmeat/core/sync.py` (error handling in sync functions)
- `skillmeat/core/exceptions.py` (new exception types)
- `tests/unit/test_sync_merge_errors.py` (new test)

---

### SYNC-INT-008: Add Merge Undo/Rollback Capability After Sync

**Status**: Pending
**Est**: 2 points
**Assigned to**: frontend-developer
**Dependencies**: MERGE-UI-009 (Phase 9 merge error handling infrastructure)

Add UI and backend support for undoing/rolling back a sync that included merge:

**What to do:**
- Add "Undo Sync" button to SyncStatusTab after successful sync
- Implement sync undo in sync system (restore pre-sync states)
- Show confirmation dialog before undo
- Display undo progress and result
- Support undo for all three sync directions
- Ensure undo doesn't lose unrelated changes
- Add telemetry for undo operations

**Definition of Done**:
- Undo button appears after sync completes
- Undo restores pre-sync state
- Works for all three sync directions
- Component test passes: `test_sync_undo_ui`
- Integration test passes: `test_sync_undo_workflow`
- Undo doesn't interfere with subsequent sync operations

**Key Files**:
- `skillmeat/web/components/entity/sync-status-tab.tsx` (add undo button)
- `skillmeat/core/sync.py` (implement sync undo)
- `tests/integration/test_sync_undo.py` (new test)

---

## Architecture Context

### Three-Way Merge in Sync Workflows

**Phase 7 Foundation**: Provides three-way merge resolution system with LCA computation and conflict detection.

**Phase 10 Integration**: Integrates merge into sync execution:

```
Sync Flow (with merge support):
1. Fetch remote/upstream artifact
2. Check if local version matches base version
3. If mismatch detected → invoke three-way merge
4. Apply merge result to local copy
5. Update lock file with merged state
6. Auto-capture version (Phase 10 + Phase 11)
7. Return sync result with merge metadata
```

### SyncStatusTab Merge Display

**Current State**: Shows sync progress, source/destination, sync status.

**Phase 10 Enhancement**: Add merge information display:
```
SyncStatusTab
├── Sync Status (existing)
├── Merge Status (NEW)
│   ├── Status indicator
│   ├── Source/Base/Target versions
│   ├── Conflict count
│   └── Merge decision
└── Merge Preview (NEW)
    └── Show diff of merged result
```

### Sync Dialogs for Merge Workflow

**Current State**: Simple confirmation dialog.

**Phase 10 Redesign**: Show merge resolution before confirming:
```
Sync Dialog
├── Sync Details (source, destination)
├── Merge Info (if applicable)
│   ├── Merge preview
│   ├── Conflict count
│   └── Resolution strategy
└── Actions
    ├── Review Merge (→ MergeViewer)
    ├── Cancel
    └── Confirm Sync
```

---

## Dependencies

### External Dependencies (on other phases)

- **Phase 7**: Three-way merge resolution system (MERGE-UI-007) - **REQUIRED**
- **Phase 8**: MergeStatusIndicator component (MERGE-UI-001) - **REQUIRED**
- **Phase 9**: MergeViewer and MergePreview components (MERGE-UI-009) - **REQUIRED**
- **Phase 11**: Version capture system (SVCV-002) - **REQUIRED for SYNC-INT-006**

### Internal Integration Points

- `skillmeat/core/sync.py`: Primary modification point for all three sync directions
- `skillmeat/web/components/entity/sync-status-tab.tsx`: UI display for merge information
- Various sync dialog components: Unified merge workflow presentation

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | Merge error handling, state validation | 90%+ | ⏳ |
| Integration | Upstream/deploy/pull sync with merge | Core flows | ⏳ |
| Component | SyncStatusTab merge display, sync dialogs | UI interactions | ⏳ |
| E2E | Full sync workflow with conflict resolution | All paths | ⏳ |

**Test Data Sets**:
- Simple upstream sync (no conflict)
- Upstream sync with auto-resolvable conflict
- Upstream sync with unresolvable conflict
- Deploy sync with local project modifications
- Pull sync with upstream changes
- All three directions with version capture

---

## Blockers

### Active Blockers

_No active blockers at this time. Phase 10 is blocked by Phase 7 and Phase 9 completion._

### Potential Risks

1. **Merge state complexity in sync context**: Mitigation: Reference Phase 7 merge system, add comprehensive logging
2. **Dialog UX with merge preview**: Mitigation: Test with real merge scenarios, iterate on UX
3. **Version capture timing**: Mitigation: Coordinate with Phase 11, add clear API contract

---

## Next Session Agenda

### Immediate Actions (When Phase 7 & 9 Complete)

1. [ ] SYNC-INT-001: Wire three-way merge to `sync_upstream()`
2. [ ] SYNC-INT-002: Wire three-way merge to `sync_deploy()`
3. [ ] SYNC-INT-003: Wire three-way merge to `sync_pull()`
4. [ ] SYNC-INT-004: Add merge display to SyncStatusTab

### Upcoming Critical Items

- **Batch 1 completion**: Sync merge system functional
- **Batch 2 completion**: Polish, error handling, version capture
- **Phase 10 completion**: All sync workflows support merge, UX is clear

### Context for Continuing Agent

**Critical Integration Points**:
- Merge resolution from Phase 7: Use `compute_three_way_merge()` API
- MergeStatusIndicator from Phase 8: Use for status display
- MergePreview from Phase 9: Use in dialogs and tabs
- Version capture from Phase 11: Hook on sync completion

**Files to Modify**:
- `skillmeat/core/sync.py`: Three sync functions + error handling
- `skillmeat/core/exceptions.py`: New merge error types
- `skillmeat/web/components/entity/sync-status-tab.tsx`: Merge display
- Various sync dialog components: Unified merge workflow

**Design Decisions**:
- When should version be captured? (immediately after merge, or after user confirmation?)
- Should sync undo be available forever, or with time limit?
- How much merge context should SyncStatusTab show? (summary vs. full preview)

---

## Additional Resources

- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Phase 7 (Merge System)**: `.claude/progress/versioning-merge-system/phase-7-progress.md`
- **Phase 8 (Merge UI)**: `.claude/progress/versioning-merge-system/phase-8-progress.md`
- **Phase 9 (Merge Viewer)**: `.claude/progress/versioning-merge-system/phase-9-progress.md`
- **Phase 11 (Version Capture)**: `.claude/progress/versioning-merge-system/phase-11-progress.md`
