---
type: progress
prd: "unified-sync-workflow"
phase: 1
phase_name: "Conflict-Aware Deploy Dialog"
status: pending
progress: 0
created: 2026-02-04
updated: 2026-02-04

tasks:
  - id: "SYNC-001"
    name: "Create ConflictAwareDeployDialog"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "2 pts"
    model: "opus"

  - id: "SYNC-002"
    name: "Add usePreDeployCheck hook"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1 pt"
    model: "opus"

  - id: "SYNC-003"
    name: "Integrate with SyncStatusTab"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-001", "SYNC-002"]
    estimate: "1 pt"
    model: "opus"

  - id: "SYNC-004"
    name: "Handle no-conflict fast path"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-003"]
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-005"
    name: "Connect to Merge Workflow"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-001"]
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-006"
    name: "Unit tests for dialog and hook"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-001", "SYNC-002"]
    estimate: "1.5 pts"
    model: "sonnet"

parallelization:
  batch_1: ["SYNC-001", "SYNC-002"]
  batch_2: ["SYNC-003", "SYNC-005", "SYNC-006"]
  batch_3: ["SYNC-004"]

quality_gates:
  - "ConflictAwareDeployDialog renders with proper loading skeleton"
  - "DiffViewer correctly displays project vs collection changes"
  - "Overwrite button triggers deploy with overwrite=true"
  - "Merge button opens SyncDialog"
  - "Cancel button closes dialog without action"
  - "No-conflict path skips dialog and deploys directly"
  - "Unit tests pass with >85% coverage"
  - "No TypeScript errors"
---

# Phase 1: Conflict-Aware Deploy Dialog

**Goal**: Before deploying Collection → Project, check for conflicts. If project has local changes, show diff and ask user to confirm overwrite OR open merge workflow.

**Duration**: 3-4 days | **Story Points**: 6.5

## Task Details

### SYNC-001: Create ConflictAwareDeployDialog

**File**: `skillmeat/web/components/sync-status/conflict-aware-deploy-dialog.tsx`

**Requirements**:
- Props: `artifact`, `projectPath`, `open`, `onOpenChange`, `onSuccess`, `onMergeRequested`
- Fetch diff using `usePreDeployCheck` hook when dialog opens
- Show loading skeleton while fetching
- Display `DiffViewer` when `has_changes=true`
- Warning alert: "The project has local modifications that will be overwritten"
- Buttons: Overwrite & Deploy, Merge Changes, Cancel
- Handle error states

### SYNC-002: Add usePreDeployCheck hook

**File**: `skillmeat/web/hooks/use-pre-deploy-check.ts`

**Requirements**:
- TanStack Query `useQuery` wrapper
- Fetches `GET /artifacts/{id}/diff?project_path=...`
- Returns `ArtifactDiffResponse` with `has_changes`, `files`, `summary`
- Stale time: 30 seconds (interactive operation)
- Export from `hooks/index.ts`

### SYNC-003: Integrate with SyncStatusTab

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- Add state: `showDeployDialog`
- Update deploy button handler to open dialog instead of direct mutation
- Pass `artifact`, `projectPath`, handlers to dialog
- Handle `onSuccess` callback
- Handle `onMergeRequested` to open SyncDialog

### SYNC-004: Handle no-conflict fast path

**File**: Same as SYNC-003

**Requirements**:
- If diff shows `has_changes=false`, show simplified dialog
- "No conflicts detected. Safe to deploy." message
- Single "Deploy" button (no merge option needed)

### SYNC-005: Connect to Merge Workflow

**File**: `conflict-aware-deploy-dialog.tsx`

**Requirements**:
- "Merge Changes" button calls `onMergeRequested` prop
- Parent (SyncStatusTab) opens existing SyncDialog with proper context
- Close ConflictAwareDeployDialog when merge workflow starts

### SYNC-006: Unit tests

**Files**:
- `skillmeat/web/__tests__/conflict-aware-deploy-dialog.test.tsx`
- `skillmeat/web/__tests__/use-pre-deploy-check.test.ts`

**Requirements**:
- Test loading state
- Test diff display when conflicts exist
- Test "safe to deploy" when no conflicts
- Test button actions (Overwrite, Merge, Cancel)
- Test error states
- Target >85% coverage

## Quick Reference

### Execute Phase

```text
# Batch 1: Create dialog and hook (parallel)
Task("ui-engineer-enhanced", "SYNC-001: Create ConflictAwareDeployDialog component
  File: skillmeat/web/components/sync-status/conflict-aware-deploy-dialog.tsx
  See implementation plan for full component spec with props, state, and rendering structure.
  Key features:
  - Fetch diff using usePreDeployCheck hook (created in SYNC-002)
  - Show DiffViewer when has_changes=true
  - Warning alert for local modifications
  - Buttons: 'Overwrite & Deploy', 'Merge Changes', 'Cancel'")

Task("ui-engineer-enhanced", "SYNC-002: Create usePreDeployCheck hook
  File: skillmeat/web/hooks/use-pre-deploy-check.ts
  TanStack Query wrapper for GET /artifacts/{id}/diff?project_path=...
  Returns ArtifactDiffResponse with has_changes, files, summary
  Stale time: 30 seconds
  Also export from hooks/index.ts")

# Batch 2: Integration and tests (after batch 1)
Task("ui-engineer-enhanced", "SYNC-003: Integrate ConflictAwareDeployDialog with SyncStatusTab
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  - Add showDeployDialog state
  - Update handleDeployToProject to open dialog
  - Handle onSuccess and onMergeRequested callbacks")

Task("ui-engineer-enhanced", "SYNC-006: Write unit tests for dialog and hook
  Files: __tests__/conflict-aware-deploy-dialog.test.tsx, __tests__/use-pre-deploy-check.test.ts
  Test loading, diff display, no-conflict path, button actions, error states
  Target >85% coverage", model="sonnet")

# Batch 3: Polish (after batch 2)
Task("ui-engineer-enhanced", "SYNC-004 + SYNC-005: Add no-conflict fast path and merge workflow connection
  - SYNC-004: Simplified dialog when has_changes=false
  - SYNC-005: Merge button opens SyncDialog with proper context", model="sonnet")
```

### Update Status (CLI)

```bash
# Single task
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/unified-sync-workflow/phase-1-progress.md \
  -t SYNC-001 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-1-progress.md \
  --updates "SYNC-001:completed,SYNC-002:completed"
```
