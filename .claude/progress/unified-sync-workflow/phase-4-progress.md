---
type: progress
prd: unified-sync-workflow
phase: 4
phase_name: Tests, Accessibility & Polish
status: pending
progress: 0
created: 2026-02-04
updated: 2026-02-05
tasks:
- id: SYNC-P01
  name: Persistent drift dismissal
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 1 pt
  model: sonnet
- id: SYNC-P02
  name: 'E2E: Deploy with conflicts'
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U02
  estimate: 0.75 pts
  model: sonnet
- id: SYNC-P03
  name: 'E2E: Push with conflicts'
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U03
  estimate: 0.75 pts
  model: sonnet
- id: SYNC-P04
  name: 'E2E: Pull with conflicts'
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U04
  estimate: 0.75 pts
  model: sonnet
- id: SYNC-P05
  name: 'E2E: Full sync cycle'
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-P02
  - SYNC-P03
  - SYNC-P04
  estimate: 1 pt
  model: sonnet
- id: SYNC-P06
  name: Accessibility audit
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 0.5 pts
  model: sonnet
- id: SYNC-P07
  name: 'Performance: large diffs'
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 0.5 pts
  model: sonnet
- id: SYNC-P08
  name: Code review and merge
  status: pending
  assigned_to:
  - code-reviewer
  dependencies:
  - SYNC-P01
  - SYNC-P02
  - SYNC-P03
  - SYNC-P04
  - SYNC-P05
  - SYNC-P06
  - SYNC-P07
  estimate: 0.75 pts
  model: opus
parallelization:
  batch_1:
  - SYNC-P01
  - SYNC-P02
  - SYNC-P03
  - SYNC-P04
  - SYNC-P06
  - SYNC-P07
  batch_2:
  - SYNC-P05
  batch_3:
  - SYNC-P08
quality_gates:
- Drift dismissal persists across sessions, expires after 24h
- All E2E tests pass
- Zero axe-core accessibility violations
- Dialog renders in <200ms for typical diffs
- Code review complete with no blockers
schema_version: 2
doc_type: progress
feature_slug: unified-sync-workflow
---

# Phase 4: Tests, Accessibility & Polish

**Goal**: Comprehensive testing, accessibility audit, performance optimization, and persistent drift dismissal.

**Duration**: 2-3 days | **Story Points**: 6

**Depends on**: Phase 3 complete

## Task Details

### SYNC-P01: Persistent drift dismissal

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- localStorage key: `skillmeat:drift-dismissed:{artifactId}:{scope}`
- 24h expiry with timestamp
- SSR-safe (`typeof window` check)
- Clear on new changes detected
- Update `drift-alert-banner.tsx` to accept persistent dismissal callback

### SYNC-P02: E2E test - Deploy with conflicts

**File**: `skillmeat/web/tests/sync-workflow.spec.ts`

**Requirements**:
- Deploy opens DiffViewer dialog
- User sees file changes
- User confirms overwrite
- Deploy succeeds with toast

### SYNC-P03: E2E test - Push with conflicts

**File**: `skillmeat/web/tests/sync-workflow.spec.ts`

**Requirements**:
- Push opens DiffViewer dialog (not old AlertDialog)
- Shows collection-vs-project diff
- User confirms push
- Collection updated

### SYNC-P04: E2E test - Pull with conflicts

**File**: `skillmeat/web/tests/sync-workflow.spec.ts`

**Requirements**:
- Pull opens DiffViewer dialog
- Shows upstream diff
- User confirms sync

### SYNC-P05: E2E test - Full sync cycle

**File**: `skillmeat/web/tests/sync-workflow.spec.ts`

**Requirements**:
- Pull from source → local edit → Push to collection → Deploy to project
- All steps complete without errors
- Cache invalidation works correctly

### SYNC-P06: Accessibility audit

**File**: `skillmeat/web/__tests__/a11y/sync-dialogs.test.tsx`

**Requirements**:
- axe-core tests for SyncConfirmationDialog in all 3 directions
- Focus management: focus trapped in dialog, returns on close
- ARIA labels on all interactive elements
- Keyboard navigation works

### SYNC-P07: Performance - large diffs

**Requirements**:
- Profile DiffViewer with >1000 lines
- Add "Show first N files" option if rendering exceeds 500ms
- Target: <200ms render for typical diffs (5-20 files)
- Graceful degradation for large diffs

### SYNC-P08: Code review and merge

**Requirements**:
- Final review of all changes across all phases
- Verify quality gates met
- No blocking comments
- Merge to feature branch

## Quick Reference

### Execute Phase

```text
# Batch 1: Parallel polish tasks
Task("ui-engineer-enhanced", "SYNC-P01: Persistent drift dismissal
  localStorage with 24h expiry, SSR-safe", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-P02: E2E Playwright test for deploy with conflicts
  File: tests/sync-workflow.spec.ts", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-P03: E2E Playwright test for push with conflicts", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-P04: E2E Playwright test for pull with conflicts", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-P06: Accessibility audit with axe-core
  File: __tests__/a11y/sync-dialogs.test.tsx", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-P07: Performance profile and optimize large diffs", model="sonnet")

# Batch 2: Full cycle test (after individual tests)
Task("ui-engineer-enhanced", "SYNC-P05: E2E full sync cycle test", model="sonnet")

# Batch 3: Final review
Task("code-reviewer", "SYNC-P08: Final code review and merge")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-4-progress.md \
  --updates "SYNC-P01:completed,SYNC-P02:completed,SYNC-P03:completed"
```
