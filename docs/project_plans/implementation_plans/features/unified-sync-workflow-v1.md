---
title: 'Implementation Plan: Unified Sync Workflow Enhancement'
description: Phased implementation for conflict-aware sync flows across all three
  directions (Source->Collection->Project) with integrated diff viewer
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- web-ui
- sync
- conflict-resolution
- backend
created: 2026-02-04
updated: '2026-02-07'
category: product-planning
status: completed
version: '2.0'
related:
- /skillmeat/web/components/sync-status/sync-status-tab.tsx
- /skillmeat/web/components/sync-status/artifact-flow-banner.tsx
- /skillmeat/web/components/entity/diff-viewer.tsx
- /skillmeat/api/routers/artifacts.py
- /docs/project_plans/reports/unified-sync-workflow-plan-review-2026-02-05.md
---

# Implementation Plan: Unified Sync Workflow Enhancement

**Plan ID**: `IMPL-2026-02-04-UNIFIED-SYNC-WORKFLOW`

**Date**: 2026-02-04 | **Revised**: 2026-02-05

**Author**: Claude Code (Implementation Orchestrator)

**Complexity**: Medium-High (M+)

**Total Estimated Effort**: 25 story points

**Target Timeline**: 10-14 days

---

## Executive Summary

This plan enhances SkillMeat's sync workflow to provide a conflict-aware, DiffViewer-first experience across **all three** sync directions from the Sync Status Tab. Every direction (Pull, Push, Deploy) gets a unified confirmation dialog showing file-level diffs before execution, with Overwrite and Merge options gated by target-side changes.

### Current State (Validated 2026-02-05)

| Direction | Current State | Gaps |
|-----------|--------------|------|
| Pull Source→Collection | Fully functional with simple confirmation | No DiffViewer integration, no merge option in confirmation |
| Deploy Collection→Project | Overwrite-only with confirmation dialog | No pre-diff check, no merge strategy, deploy API is overwrite-only |
| Push Project→Collection | **Fully functional** with AlertDialog confirmation, push button, mutation, cache invalidation | No DiffViewer in confirmation, uses simple AlertDialog |
| Merge Infrastructure | MergeWorkflowDialog (bidirectional, 5-step), merge API (analyze/preview/execute/resolve) | Not connected to deploy/push flows; SyncDialog is upstream-only |
| Diff Infrastructure | DiffViewer (side-by-side), DiffEngine (backend, production-ready) | No source-vs-project endpoint |

### Key Outcomes

- **Unified DiffViewer dialog** for all three sync directions
- **Backend: source-vs-project diff endpoint** (new, ~50 LOC)
- **Backend: merge-capable deploy** (extend deploy endpoint)
- **Merge gating**: enabled only when target has changes not in source
- **Pull flow upgraded** with DiffViewer (previously omitted)
- **Push flow upgraded** from AlertDialog to DiffViewer dialog
- **Source vs Project** direct comparison in ComparisonSelector
- **Persistent drift dismissal** (localStorage-backed, 24h expiry)

---

## Architecture Overview

### Implementation Strategy

**Build-Up Approach** (backend first, then unified UI):

1. **Phase 1**: Backend enablement + unified conflict-check hook
2. **Phase 2**: Single DiffViewer confirmation dialog for ALL three directions
3. **Phase 3**: Source vs Project comparison + MergeWorkflow integration
4. **Phase 4**: Tests, a11y, performance, polish

### Backend Changes Required

Two backend additions are needed (all other APIs production-ready):

| Endpoint | Type | Purpose | Complexity |
|----------|------|---------|-----------|
| `GET /artifacts/{id}/source-project-diff` | **New** | Direct source-vs-project comparison using existing DiffEngine | Low (~50 LOC) |
| `POST /artifacts/{id}/deploy` | **Extend** | Add `strategy: 'merge'` with conflict reporting, currently overwrite-only | Moderate (~150 LOC) |

### Unified Flow Pattern (Target State)

All three directions follow the same UX:

```
User clicks sync action (Deploy/Push/Pull)
  │
  ▼
Pre-operation diff check (useConflictCheck hook)
  │
  ├── [No changes] → Show "Safe to proceed" → Single confirm button
  │
  ├── [Changes exist, no conflicts] → Show DiffViewer
  │   → Buttons: [Overwrite] [Merge*] [Cancel]
  │
  └── [Conflicts detected] → Show DiffViewer with conflict markers
      → Buttons: [Overwrite] [Merge] [Cancel]

* Merge enabled only when target has changes not in source
```

### Merge Gating Rules

Merge is **enabled** only when the **target** has changes the source doesn't have:

| Direction | Target | Merge Enabled When | Diff Endpoint |
|-----------|--------|-------------------|---------------|
| Deploy (Collection→Project) | Project | Project has modified/added files | `GET /diff` |
| Push (Project→Collection) | Collection | Collection has modified/added files relative to project | `GET /diff` |
| Pull (Source→Collection) | Collection | Collection has modified/added files relative to source | `GET /upstream-diff` |

### Component Architecture

```
SyncStatusTab (orchestrator)
  │
  ├── ArtifactFlowBanner (3-tier visualization)
  ├── ComparisonSelector (scope: source-vs-collection | collection-vs-project | source-vs-project)
  ├── DriftAlertBanner (status indicators)
  ├── DiffViewer (file-level comparison)
  ├── SyncActionsFooter
  │
  ├── SyncConfirmationDialog (NEW - unified for all directions)
  │     └── Embeds DiffViewer, direction-specific labels, merge gating
  │
  └── MergeWorkflowDialog (existing - 5-step conflict resolution)
        └── Routed to from SyncConfirmationDialog when user clicks "Merge"
```

---

## Phase Breakdown

### Phase 1: Backend Enablement + Unified Hook

**Duration**: 2-3 days | **Story Points**: 6

**Dependencies**: None

**Goal**: Add missing backend endpoints and create the unified frontend hook for pre-operation conflict detection.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-B01 | Source-vs-project diff endpoint | Add `GET /artifacts/{id}/source-project-diff?project_path=...` using existing DiffEngine. Follow `/upstream-diff` pattern, compare upstream source directly against project deployment. | Returns `ArtifactDiffResponse` with file-level diffs between source and project | 1.5 pts | python-backend-engineer | None |
| SYNC-B02 | Extend deploy with merge strategy | Extend `POST /deploy` to accept `strategy: 'overwrite' \| 'merge'`. When merge: use DiffEngine for comparison, attempt file-level merge, return conflicts if both sides modified same file. | Deploy with `strategy: 'merge'` performs file-level merge and reports conflicts; existing `overwrite` behavior unchanged | 2 pts | python-backend-engineer | None |
| SYNC-H01 | Create unified useConflictCheck hook | Single `useConflictCheck(direction, artifactId, opts)` hook. Direction `'deploy'` fetches `/diff`, `'push'` fetches `/diff`, `'pull'` fetches `/upstream-diff`. Returns `{ diffData, hasChanges, hasConflicts, targetHasChanges, isLoading }`. | Hook correctly routes to appropriate diff API per direction; `targetHasChanges` computed from diff file statuses for merge gating | 1.5 pts | ui-engineer-enhanced | None |
| SYNC-B03 | Backend unit tests | Pytest tests for new endpoint and extended deploy with merge strategy. | Tests cover: source-project diff with changes/no changes, deploy with merge strategy success/conflicts, error cases | 1 pt | python-backend-engineer | SYNC-B01, SYNC-B02 |

**Phase 1 Subtotal**: 6 story points

**Parallelization**:
```
batch_1: [SYNC-B01, SYNC-B02, SYNC-H01]  # All independent
batch_2: [SYNC-B03]                        # After backend tasks
```

**Quality Gates**:
- [ ] Source-project diff endpoint returns accurate file-level diffs
- [ ] Deploy with `strategy: 'merge'` performs file merge, reports conflicts
- [ ] useConflictCheck routes to correct API per direction
- [ ] `targetHasChanges` flag correctly computed for merge gating
- [ ] All backend tests pass
- [ ] No regressions in existing sync/deploy flows

---

### Phase 2: Unified DiffViewer Confirmation Dialog

**Duration**: 3-4 days | **Story Points**: 9

**Dependencies**: Phase 1 (SYNC-H01 hook)

**Goal**: Build a single configurable dialog that replaces all sync confirmation flows with DiffViewer integration for all three directions.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-U01 | Create SyncConfirmationDialog | Single dialog component configurable for any direction. Props: `direction`, `artifact`, `projectPath`, `open`, `onOpenChange`, `onOverwrite`, `onMerge`, `onCancel`. Embeds DiffViewer with direction-appropriate labels. Shows merge button gated by `targetHasChanges`. | Dialog renders correctly for all 3 directions with appropriate labels, actions, and merge gating | 3 pts | ui-engineer-enhanced | SYNC-H01 |
| SYNC-U02 | Integrate for Deploy (Collection→Project) | Wire dialog in SyncStatusTab for deploy flow. Replace existing deploy confirmation with SyncConfirmationDialog. onOverwrite calls deploy API, onMerge routes to MergeWorkflowDialog or merge-deploy. | Deploy button opens SyncConfirmationDialog with collection-vs-project diff | 1 pt | ui-engineer-enhanced | SYNC-U01 |
| SYNC-U03 | Integrate for Push (Project→Collection) | Replace existing AlertDialog push confirmation (lines 778-792 in sync-status-tab.tsx) with SyncConfirmationDialog. Push mutation already exists (lines 415-450). | Push button opens DiffViewer dialog instead of simple AlertDialog; existing mutation reused | 1 pt | ui-engineer-enhanced | SYNC-U01 |
| SYNC-U04 | Integrate for Pull (Source→Collection) | Replace existing pull confirmation with SyncConfirmationDialog. Wire to upstream-diff for pre-check. onOverwrite calls sync mutation, onMerge routes to MergeWorkflowDialog. | Pull button opens DiffViewer dialog; user sees upstream changes before confirming | 1 pt | ui-engineer-enhanced | SYNC-U01 |
| SYNC-U05 | Merge gating logic | Implement in SyncConfirmationDialog: merge button enabled only when `targetHasChanges` from useConflictCheck. Disabled state shows tooltip: "Target has no local changes to merge." | Merge button correctly enabled/disabled per direction and diff state | 1 pt | ui-engineer-enhanced | SYNC-U01 |
| SYNC-U06 | Unit tests for dialog and hook | Tests under `__tests__/components/sync-confirmation-dialog.test.tsx` and `__tests__/hooks/use-conflict-check.test.ts`. Cover: loading, diff display, no-conflict path, merge gating, all 3 directions, error states. | Tests pass with >85% coverage | 2 pts | ui-engineer-enhanced | SYNC-U01, SYNC-H01 |

**Phase 2 Subtotal**: 9 story points

**Parallelization**:
```
batch_1: [SYNC-U01]                                      # Dialog component first
batch_2: [SYNC-U02, SYNC-U03, SYNC-U04, SYNC-U05]       # All integrations parallel
batch_3: [SYNC-U06]                                      # Tests after integration
```

**Quality Gates**:
- [ ] Single dialog renders correctly for Deploy, Push, and Pull directions
- [ ] DiffViewer displays file changes with direction-appropriate labels
- [ ] Merge button gated: enabled only when target has changes
- [ ] Deploy flow: diff check before overwrite, merge routes to MergeWorkflowDialog
- [ ] Push flow: replaces existing AlertDialog, reuses existing mutation
- [ ] Pull flow: shows upstream diff before confirming sync
- [ ] No-conflict fast path shows "Safe to proceed" for all directions
- [ ] Unit tests pass with >85% coverage

---

### Phase 3: Source vs Project + Merge Integration + Banner

**Duration**: 2-3 days | **Story Points**: 4

**Dependencies**: Phase 1 (SYNC-B01) and Phase 2 (SYNC-U01)

**Goal**: Add Source vs Project direct comparison, wire MergeWorkflowDialog from unified dialog, and polish banner visuals.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-A01 | Source vs Project comparison option | Add `'source-vs-project'` to ComparisonSelector. Enable only when `hasValidUpstreamSource(entity) && projectPath`. Wire to new backend endpoint. | ComparisonSelector shows 3 options; source-vs-project fetches from new endpoint | 1.5 pts | ui-engineer-enhanced | SYNC-B01 |
| SYNC-A02 | DiffViewer label config for all scopes | Ensure left/right labels are correct for each scope: source-vs-collection ("Source"/"Collection"), collection-vs-project ("Collection"/"Project"), source-vs-project ("Source"/"Project"). | Labels dynamically set per comparison scope | 0.5 pts | ui-engineer-enhanced | SYNC-A01 |
| SYNC-A03 | Wire MergeWorkflowDialog from unified dialog | When user clicks "Merge" in SyncConfirmationDialog, close it and open MergeWorkflowDialog with direction-appropriate context. MergeWorkflowDialog is already bidirectional. | Merge button routes to 5-step merge workflow for Pull and Push directions; Deploy merge uses extended deploy API | 1.5 pts | ui-engineer-enhanced | SYNC-U01, SYNC-B02 |
| SYNC-A04 | Banner styling: push arrow + button | Make Connector 3 arrow solid when project has changes (currently solid when projectInfo exists, keep that). Update button variant to `'default'` when project diff shows changes. | Push arrow visual reflects change status; button more prominent when action available | 0.5 pts | ui-engineer-enhanced | None |

**Phase 3 Subtotal**: 4 story points

**Parallelization**:
```
batch_1: [SYNC-A01, SYNC-A03, SYNC-A04]  # Independent
batch_2: [SYNC-A02]                        # After SYNC-A01
```

**Quality Gates**:
- [ ] Source vs Project comparison works with new endpoint
- [ ] ComparisonSelector enables all valid combinations
- [ ] DiffViewer labels correct for all 3 scopes
- [ ] Merge button routes to MergeWorkflowDialog for pull/push
- [ ] Merge-capable deploy works via extended API
- [ ] Banner push arrow reflects project change status

---

### Phase 4: Tests, Accessibility & Polish

**Duration**: 2-3 days | **Story Points**: 6

**Dependencies**: Phase 3 complete

**Goal**: Comprehensive testing, accessibility audit, performance optimization, and persistent drift dismissal.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-P01 | Persistent drift dismissal | Store dismissed drift in localStorage. Key: `skillmeat:drift-dismissed:{id}:{scope}`. 24h expiry. SSR-safe. Clear on new changes detected. | Dismissal persists across page refreshes; expires after 24h | 1 pt | ui-engineer-enhanced | None |
| SYNC-P02 | E2E: Deploy with conflicts | Playwright spec at `tests/sync-workflow.spec.ts`. Test deploy opens DiffViewer dialog, user confirms overwrite, deploy succeeds. | Playwright test passes | 0.75 pts | ui-engineer-enhanced | SYNC-U02 |
| SYNC-P03 | E2E: Push with conflicts | Playwright spec. Test push opens DiffViewer dialog, shows collection-vs-project diff, user confirms. | Playwright test passes | 0.75 pts | ui-engineer-enhanced | SYNC-U03 |
| SYNC-P04 | E2E: Pull with conflicts | Playwright spec. Test pull opens DiffViewer dialog, shows upstream diff, user confirms. | Playwright test passes | 0.75 pts | ui-engineer-enhanced | SYNC-U04 |
| SYNC-P05 | E2E: Full sync cycle | Pull → local edit → Push → Deploy cycle end-to-end. | Full cycle completes without errors | 1 pt | ui-engineer-enhanced | All |
| SYNC-P06 | Accessibility audit | axe-core tests under `__tests__/a11y/`. Focus management in dialogs, ARIA labels on all buttons. | Zero accessibility violations | 0.5 pts | ui-engineer-enhanced | All dialogs |
| SYNC-P07 | Performance: large diffs | Profile DiffViewer with >1000 lines. Add "Show first N files" cap if rendering >500ms. | Dialog renders in <200ms for typical diffs; graceful degradation for large diffs | 0.5 pts | ui-engineer-enhanced | All |
| SYNC-P08 | Code review and merge | Final review of all changes. | Code reviewed, no blocking comments, merged | 0.75 pts | code-reviewer | All |

**Phase 4 Subtotal**: 6 story points

**Parallelization**:
```
batch_1: [SYNC-P01, SYNC-P02, SYNC-P03, SYNC-P04, SYNC-P06, SYNC-P07]  # All independent
batch_2: [SYNC-P05]                                                        # After individual tests
batch_3: [SYNC-P08]                                                        # Final review
```

**Quality Gates**:
- [ ] Drift dismissal persists across sessions, expires after 24h
- [ ] All E2E tests pass
- [ ] Zero axe-core accessibility violations
- [ ] Dialog renders in <200ms for typical diffs
- [ ] Code review complete with no blockers

---

## File Changes Summary

### New Files

| File | LOC | Phase | Purpose |
|------|-----|-------|---------|
| `api/routers/artifacts.py` additions | ~50 | 1 | Source-vs-project diff endpoint |
| `web/components/sync-status/sync-confirmation-dialog.tsx` | ~300 | 2 | Unified confirmation dialog for all directions |
| `web/hooks/use-conflict-check.ts` | ~80 | 1 | Unified pre-operation diff hook |
| `web/__tests__/components/sync-confirmation-dialog.test.tsx` | ~250 | 2 | Dialog tests |
| `web/__tests__/hooks/use-conflict-check.test.ts` | ~150 | 2 | Hook tests |
| `web/tests/sync-workflow.spec.ts` | ~300 | 4 | Playwright E2E tests |
| `web/__tests__/a11y/sync-dialogs.test.tsx` | ~80 | 4 | Accessibility tests |

### Modified Files

| File | Changes | Phase | Purpose |
|------|---------|-------|---------|
| `api/routers/artifacts.py` (deploy endpoint) | +150 LOC | 1 | Add merge strategy support |
| `web/components/sync-status/sync-status-tab.tsx` | +60/-40 LOC | 2 | Wire unified dialog for all 3 directions, remove old AlertDialog |
| `web/components/sync-status/comparison-selector.tsx` | +20 LOC | 3 | Add source-vs-project option |
| `web/components/sync-status/artifact-flow-banner.tsx` | +10 LOC | 3 | Push arrow/button styling |
| `web/components/sync-status/drift-alert-banner.tsx` | +15 LOC | 4 | Persistent dismissal callback |
| `web/hooks/index.ts` | +3 LOC | 1 | Export new hook |

**Total New Code**: ~1,210 LOC | **Total Modified**: ~300 LOC

---

## Orchestration Quick Reference

### Phase 1 Delegation

```text
# Batch 1: Backend + Hook (parallel)
Task("python-backend-engineer", "SYNC-B01: Add source-vs-project diff endpoint
  File: skillmeat/api/routers/artifacts.py
  Pattern: Follow /upstream-diff endpoint structure (~line 4055)
  New: GET /artifacts/{id}/source-project-diff?project_path=...
  Implementation: Use existing DiffEngine to compare upstream source files
  directly against project deployment files. Return ArtifactDiffResponse.
  ~50 LOC addition.")

Task("python-backend-engineer", "SYNC-B02: Extend deploy endpoint with merge strategy
  File: skillmeat/api/routers/artifacts.py (~line 2898)
  Extend POST /deploy request model to accept strategy: 'overwrite' | 'merge'
  When strategy='merge':
  - Use DiffEngine to compare collection vs project files
  - For files only in collection: copy to project
  - For files only in project: keep (don't delete)
  - For both sides modified: attempt merge, return conflict if can't auto-resolve
  - Return conflicts array in response
  Existing overwrite behavior MUST remain unchanged as default.")

Task("ui-engineer-enhanced", "SYNC-H01: Create unified useConflictCheck hook
  File: skillmeat/web/hooks/use-conflict-check.ts
  Export from hooks/index.ts
  Signature: useConflictCheck(direction: 'deploy' | 'push' | 'pull', artifactId, opts)
  Direction routing:
  - 'deploy': GET /artifacts/{id}/diff?project_path=... (collection vs project)
  - 'push': GET /artifacts/{id}/diff?project_path=... (collection vs project)
  - 'pull': GET /artifacts/{id}/upstream-diff (source vs collection)
  Returns: { diffData, hasChanges, hasConflicts, targetHasChanges, isLoading, error }
  targetHasChanges computed from FileDiff statuses (any modified/added in target side)
  Stale time: 30 seconds. Enabled controlled by opts.enabled.")

# Batch 2: Backend tests (after batch 1)
Task("python-backend-engineer", "SYNC-B03: Write pytest tests for new/extended endpoints
  Cover: source-project diff (changes/no changes/error), deploy merge strategy
  (success/conflicts/fallback to overwrite), no regression on existing deploy", model="sonnet")
```

### Phase 2 Delegation

```text
# Batch 1: Build dialog
Task("ui-engineer-enhanced", "SYNC-U01: Create SyncConfirmationDialog
  File: skillmeat/web/components/sync-status/sync-confirmation-dialog.tsx
  SINGLE configurable dialog for all sync directions. Props:
  - direction: 'deploy' | 'push' | 'pull'
  - artifact: Artifact
  - projectPath: string
  - open/onOpenChange: dialog state
  - onOverwrite: () => void (execute with overwrite)
  - onMerge: () => void (route to merge workflow)
  Uses useConflictCheck hook internally.
  Direction config determines:
  - Title: 'Deploy to Project' / 'Push to Collection' / 'Pull from Source'
  - DiffViewer labels: Collection↔Project / Project↔Collection / Source↔Collection
  - Warning text per direction
  - Merge button gated by targetHasChanges (disabled with tooltip when false)
  Loading skeleton while fetching. Error state. No-conflict fast path.
  Pattern: Dialog > DialogContent(max-w-4xl) > Header > DiffViewer > Footer(Cancel/Merge/Overwrite)")

# Batch 2: Wire all 3 directions (parallel, after dialog)
Task("ui-engineer-enhanced", "SYNC-U02: Integrate SyncConfirmationDialog for Deploy
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  - Add showDeployConfirmDialog state
  - Replace handleDeployToProject to open dialog (direction='deploy')
  - onOverwrite: call deployMutation with overwrite=true
  - onMerge: close dialog, open MergeWorkflowDialog or call deploy with strategy='merge'")

Task("ui-engineer-enhanced", "SYNC-U03: Integrate SyncConfirmationDialog for Push
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  - Replace existing AlertDialog (lines 778-792) with SyncConfirmationDialog(direction='push')
  - Reuse existing pushToCollectionMutation (lines 415-450)
  - onOverwrite: call pushToCollectionMutation
  - onMerge: route to MergeWorkflowDialog
  NOTE: Push button, mutation, and cache invalidation already fully exist. Only replacing the confirmation UI.")

Task("ui-engineer-enhanced", "SYNC-U04: Integrate SyncConfirmationDialog for Pull
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  - Add showPullConfirmDialog state
  - Replace existing pull confirmation with dialog (direction='pull')
  - onOverwrite: call syncMutation
  - onMerge: route to MergeWorkflowDialog")

Task("ui-engineer-enhanced", "SYNC-U05: Implement merge gating in dialog
  File: sync-confirmation-dialog.tsx
  Merge button enabled when useConflictCheck returns targetHasChanges=true
  Disabled state: variant='ghost', tooltip 'No local changes to merge'", model="sonnet")

# Batch 3: Tests
Task("ui-engineer-enhanced", "SYNC-U06: Unit tests for SyncConfirmationDialog and useConflictCheck
  Files: __tests__/components/sync-confirmation-dialog.test.tsx, __tests__/hooks/use-conflict-check.test.ts
  Cover: loading, diff display for each direction, merge gating (enabled/disabled),
  no-conflict path, button actions, error states. Target >85% coverage.", model="sonnet")
```

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Large diffs slow dialog | Poor UX | Medium | Virtualized rendering for >1000 lines; "Show first N files" option |
| Deploy merge complexity | Backend scope creep | Medium | Start with file-copy merge (no 3-way); upgrade later |
| Race condition: check vs execute | Stale data | Low | 30s stale time; refetch on dialog open |
| Direction confusion | Wrong data overwritten | Medium | Direction-specific labels, arrows, confirmation text |
| MergeWorkflowDialog integration | Context mismatch | Medium | Validate snapshot-based workflow accepts project context |

---

## Success Metrics

- **100%** of sync operations with conflicts show DiffViewer before execution
- **All 3 directions** use the same unified dialog pattern
- **Merge gating** correctly prevents merge when target has no changes
- **<200ms** dialog render time for typical diffs (5-20 files)
- **>85%** test coverage for new components and hooks
- **Zero** accessibility violations in new dialogs

---

## Dependencies & Assumptions

### Hard Dependencies
- Backend DiffEngine (exists, production-ready)
- Backend merge API (exists: analyze/preview/execute/resolve)
- TanStack React Query v5+ (available)
- shadcn Dialog components (available)
- DiffViewer component (exists, functional)
- MergeWorkflowDialog (exists, bidirectional)

### Assumptions
1. DiffEngine can be reused for source-vs-project without modification
2. Deploy merge can start with simple file-level merge (no 3-way initially)
3. MergeWorkflowDialog can accept project-context parameters
4. Existing push mutation/cache invalidation requires no changes

### Known Limitations
1. Deploy merge is file-level (not line-level 3-way merge) in v1
2. Source vs Project comparison requires dedicated endpoint (not client-side composition)
3. Drift dismissal does not sync across devices/browsers
4. MergeWorkflowDialog operates on snapshots; may need adapter for project paths

---

## Timeline Summary

| Phase | Duration | Story Points | Key Deliverables |
|-------|----------|--------------|------------------|
| Phase 1 | 2-3 days | 6 pts | Backend endpoints + unified hook |
| Phase 2 | 3-4 days | 9 pts | Unified dialog for all 3 directions |
| Phase 3 | 2-3 days | 4 pts | Source vs Project, merge routing, banner |
| Phase 4 | 2-3 days | 6 pts | E2E tests, a11y, persistent drift, review |
| **Total** | **10-14 days** | **25 pts** | Complete unified sync workflow |

---

## Review Disposition (2026-02-05)

Changes applied from plan review report:

| Finding | Disposition | Action |
|---------|-----------|--------|
| F1: Merge on deploy impossible | **Accepted** | Added SYNC-B02: extend deploy with merge strategy |
| F2: Backend changes needed | **Accepted (scoped down)** | Added SYNC-B01: source-project diff (~50 LOC). Review overstated complexity - DiffEngine handles it. |
| F3: Push flow UI stale | **Accepted** | Rewritten: push has full UI already. Tasks now UPGRADE existing AlertDialog, not build from scratch. |
| F4: Pull flow not upgraded | **Accepted** | Added SYNC-U04: integrate pull direction with unified dialog |
| F5: usePrePushCheck wrong direction | **Accepted** | Replaced with unified useConflictCheck; push uses `/diff` (collection-side), not upstream |
| F6: Estimate mismatch | **Accepted** | Reconciled to 25 pts total |
| Review Phase 0 proposal | **Rejected** | Fixed in-place, no separate alignment phase needed |
| Review 5-phase structure | **Modified** | Kept 4 phases, rebalanced. Backend in Phase 1, unified dialog in Phase 2. |

---

**Document Version**: 2.0

**Status**: Ready for Implementation

**Next Steps**: Execute Phase 1 batch 1 (SYNC-B01, SYNC-B02, SYNC-H01 in parallel)
