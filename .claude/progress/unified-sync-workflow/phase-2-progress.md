---
type: progress
prd: unified-sync-workflow
phase: 2
phase_name: Unified DiffViewer Confirmation Dialog
status: completed
progress: 100
created: 2026-02-04
updated: '2026-02-05'
tasks:
- id: SYNC-U01
  name: Create SyncConfirmationDialog
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-H01
  estimate: 3 pts
  model: opus
- id: SYNC-U02
  name: Integrate for Deploy (Collection→Project)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U01
  estimate: 1 pt
  model: opus
- id: SYNC-U03
  name: Integrate for Push (Project→Collection)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U01
  estimate: 1 pt
  model: opus
- id: SYNC-U04
  name: Integrate for Pull (Source→Collection)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U01
  estimate: 1 pt
  model: opus
- id: SYNC-U05
  name: Merge gating logic
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U01
  estimate: 1 pt
  model: sonnet
- id: SYNC-U06
  name: Unit tests for dialog and hook
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U01
  - SYNC-H01
  estimate: 2 pts
  model: sonnet
parallelization:
  batch_1:
  - SYNC-U01
  batch_2:
  - SYNC-U02
  - SYNC-U03
  - SYNC-U04
  - SYNC-U05
  batch_3:
  - SYNC-U06
quality_gates:
- Single dialog renders correctly for Deploy, Push, and Pull directions
- DiffViewer displays file changes with direction-appropriate labels
- 'Merge button gated: enabled only when target has changes'
- 'Deploy flow: diff check before overwrite, merge routes to MergeWorkflowDialog'
- 'Push flow: replaces existing AlertDialog, reuses existing mutation'
- 'Pull flow: shows upstream diff before confirming sync'
- No-conflict fast path shows 'Safe to proceed' for all directions
- Unit tests pass with >85% coverage
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
---

# Phase 2: Unified DiffViewer Confirmation Dialog

**Goal**: Build a single configurable dialog that replaces all sync confirmation flows with DiffViewer integration for all three directions.

**Duration**: 3-4 days | **Story Points**: 9

**Depends on**: Phase 1 (SYNC-H01 hook)

## Task Details

### SYNC-U01: Create SyncConfirmationDialog

**File**: `skillmeat/web/components/sync-status/sync-confirmation-dialog.tsx`

**Requirements**:
- Single configurable dialog for ALL sync directions
- Props: `direction`, `artifact`, `projectPath`, `open`, `onOpenChange`, `onOverwrite`, `onMerge`
- Uses `useConflictCheck` hook internally
- Direction config determines: title, DiffViewer labels, warning text, merge availability
- Merge button gated by `targetHasChanges`
- Loading skeleton, error state, no-conflict fast path
- Pattern: `Dialog > DialogContent(max-w-4xl) > Header > DiffViewer > Footer`

### SYNC-U02: Integrate for Deploy (Collection→Project)

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- Add `showDeployConfirmDialog` state
- Replace `handleDeployToProject` to open dialog with `direction='deploy'`
- `onOverwrite`: call `deployMutation` with `overwrite=true`
- `onMerge`: close dialog, route to MergeWorkflowDialog or merge-deploy

### SYNC-U03: Integrate for Push (Project→Collection)

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- **Replace existing AlertDialog** (lines 778-792) with `SyncConfirmationDialog(direction='push')`
- **Reuse existing** `pushToCollectionMutation` (lines 415-450)
- Push button, mutation, cache invalidation already fully exist
- Only the confirmation UI is being upgraded from AlertDialog to DiffViewer dialog

### SYNC-U04: Integrate for Pull (Source→Collection)

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- Add `showPullConfirmDialog` state
- Replace existing pull confirmation with `SyncConfirmationDialog(direction='pull')`
- `onOverwrite`: call `syncMutation`
- `onMerge`: route to MergeWorkflowDialog

### SYNC-U05: Merge gating logic

**File**: `sync-confirmation-dialog.tsx`

**Requirements**:
- Merge button enabled only when `useConflictCheck` returns `targetHasChanges=true`
- Disabled state: `variant='ghost'`, tooltip "No local changes to merge"
- Clear visual distinction between enabled/disabled merge

### SYNC-U06: Unit tests

**Files**:
- `skillmeat/web/__tests__/components/sync-confirmation-dialog.test.tsx`
- `skillmeat/web/__tests__/hooks/use-conflict-check.test.ts`

**Requirements**:
- Loading state for each direction
- Diff display with correct labels per direction
- Merge gating (enabled/disabled)
- No-conflict fast path
- Button actions (overwrite, merge, cancel)
- Error states
- Target >85% coverage

## Quick Reference

### Execute Phase

```text
# Batch 1: Build dialog
Task("ui-engineer-enhanced", "SYNC-U01: Create SyncConfirmationDialog
  File: skillmeat/web/components/sync-status/sync-confirmation-dialog.tsx
  SINGLE configurable dialog for all sync directions.
  Props: direction, artifact, projectPath, open, onOpenChange, onOverwrite, onMerge
  Uses useConflictCheck hook internally.
  Merge button gated by targetHasChanges.")

# Batch 2: Wire all 3 directions (parallel)
Task("ui-engineer-enhanced", "SYNC-U02: Integrate for Deploy in SyncStatusTab")
Task("ui-engineer-enhanced", "SYNC-U03: Integrate for Push - replace AlertDialog (lines 778-792)")
Task("ui-engineer-enhanced", "SYNC-U04: Integrate for Pull in SyncStatusTab")
Task("ui-engineer-enhanced", "SYNC-U05: Merge gating in dialog", model="sonnet")

# Batch 3: Tests
Task("ui-engineer-enhanced", "SYNC-U06: Unit tests for dialog and hook", model="sonnet")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-2-progress.md \
  --updates "SYNC-U01:completed,SYNC-U02:completed,SYNC-U03:completed"
```
