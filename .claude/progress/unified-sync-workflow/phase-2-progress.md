---
type: progress
prd: "unified-sync-workflow"
phase: 2
phase_name: "Conflict-Aware Push Enhancement"
status: pending
progress: 0
created: 2026-02-04
updated: 2026-02-04

tasks:
  - id: "SYNC-007"
    name: "Update banner arrow styling"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-008"
    name: "Create ConflictAwarePushDialog"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-001"]
    estimate: "2 pts"
    model: "opus"

  - id: "SYNC-009"
    name: "Add usePrePushCheck hook"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1 pt"
    model: "opus"

  - id: "SYNC-010"
    name: "Integrate with SyncStatusTab"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-008", "SYNC-009"]
    estimate: "1 pt"
    model: "opus"

  - id: "SYNC-011"
    name: "Add action button to banner connector"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-007"]
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-012"
    name: "Unit tests for push dialog and hook"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-008", "SYNC-009"]
    estimate: "1 pt"
    model: "sonnet"

parallelization:
  batch_1: ["SYNC-007", "SYNC-008", "SYNC-009"]
  batch_2: ["SYNC-010", "SYNC-011", "SYNC-012"]

quality_gates:
  - "Push arrow is solid when project deployment exists with changes"
  - "ConflictAwarePushDialog shows correct diff direction (project -> collection)"
  - "Push operation uses correct API parameters (strategy: 'theirs')"
  - "Inline action button triggers push flow"
  - "All confirmation dialogs have consistent UX with deploy dialog"
  - "Unit tests pass with >85% coverage"
---

# Phase 2: Conflict-Aware Push Enhancement

**Goal**: Make Push (Project → Collection) a first-class citizen with solid arrow visualization, proper confirmation dialog, and pre-conflict checking.

**Duration**: 3-4 days | **Story Points**: 6

**Depends on**: Phase 1 patterns (SYNC-001 dialog pattern)

## Task Details

### SYNC-007: Update banner arrow styling

**File**: `skillmeat/web/components/sync-status/artifact-flow-banner.tsx`

**Requirements**:
- Connector 3 (Project→Collection) arrow solid when `projectInfo?.isModified=true`
- Update `strokeDasharray` condition
- Button variant `'default'` when changes exist
- Visual consistency with other connectors

### SYNC-008: Create ConflictAwarePushDialog

**File**: `skillmeat/web/components/sync-status/conflict-aware-push-dialog.tsx`

**Requirements**:
- Similar structure to ConflictAwareDeployDialog (reuse patterns)
- Different messaging: "Push project changes to collection"
- Check for upstream changes in collection not in project
- Uses `usePrePushCheck` hook
- Diff labels: Project (left) vs Collection (right)

### SYNC-009: Add usePrePushCheck hook

**File**: `skillmeat/web/hooks/use-pre-push-check.ts`

**Requirements**:
- Check if collection has upstream changes not reflected in project
- Fetches `GET /artifacts/{id}/upstream-diff`
- Returns `{ hasUpstreamChanges, diffData, isLoading }`
- Stale time: 30 seconds

### SYNC-010: Integrate with SyncStatusTab

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- Add state: `showPushDialog`
- Update push button handler to open dialog
- Handle all strategies (overwrite, merge)
- Proper cache invalidation on success

### SYNC-011: Add action button to banner connector

**File**: `skillmeat/web/components/sync-status/artifact-flow-banner.tsx`

**Requirements**:
- Small button on Project→Collection connector
- Clear label: "Push to Collection"
- Disabled when no changes or no project
- Triggers push dialog flow

### SYNC-012: Unit tests

**Files**:
- `skillmeat/web/__tests__/conflict-aware-push-dialog.test.tsx`
- `skillmeat/web/__tests__/use-pre-push-check.test.ts`

**Requirements**:
- Test all user paths
- Test edge cases (no project, no changes)
- Target >85% coverage

## Quick Reference

### Execute Phase

```text
# Batch 1: Banner and dialogs (parallel)
Task("ui-engineer-enhanced", "SYNC-007: Update ArtifactFlowBanner arrow styling
  File: skillmeat/web/components/sync-status/artifact-flow-banner.tsx
  - Make Connector 3 solid when projectInfo?.isModified=true
  - Update strokeDasharray and button variant", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-008: Create ConflictAwarePushDialog
  File: skillmeat/web/components/sync-status/conflict-aware-push-dialog.tsx
  Similar to ConflictAwareDeployDialog but for push direction
  - Different messaging: pushing project changes to collection
  - Uses usePrePushCheck hook
  - Diff labels: Project (left) vs Collection (right)")

Task("ui-engineer-enhanced", "SYNC-009: Create usePrePushCheck hook
  File: skillmeat/web/hooks/use-pre-push-check.ts
  Check for upstream changes in collection
  Fetches GET /artifacts/{id}/upstream-diff
  Returns { hasUpstreamChanges, diffData, isLoading }")

# Batch 2: Integration and tests (after batch 1)
Task("ui-engineer-enhanced", "SYNC-010: Integrate ConflictAwarePushDialog with SyncStatusTab
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  - Add showPushDialog state
  - Update push button handler
  - Handle callbacks and cache invalidation")

Task("ui-engineer-enhanced", "SYNC-011: Add inline action button to banner connector
  File: skillmeat/web/components/sync-status/artifact-flow-banner.tsx
  Small button on Project→Collection connector for quick push", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-012: Write unit tests for push dialog and hook
  Files: __tests__/conflict-aware-push-dialog.test.tsx, __tests__/use-pre-push-check.test.ts", model="sonnet")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-2-progress.md \
  --updates "SYNC-007:completed,SYNC-008:completed,SYNC-009:completed"
```
