---
type: progress
prd: "unified-sync-workflow"
phase: 3
phase_name: "Unified Flow Integration & Source vs Project"
status: pending
progress: 0
created: 2026-02-04
updated: 2026-02-04

tasks:
  - id: "SYNC-013"
    name: "Extract shared useConflictCheck pattern"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-002", "SYNC-009"]
    estimate: "1 pt"
    model: "sonnet"

  - id: "SYNC-014"
    name: "Create SyncConfirmationDialog base"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-001", "SYNC-008"]
    estimate: "1 pt"
    model: "sonnet"

  - id: "SYNC-015"
    name: "Add Source vs Project comparison"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1.5 pts"
    model: "opus"

  - id: "SYNC-016"
    name: "Implement source-vs-project diff API call"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-015"]
    estimate: "1 pt"
    model: "opus"

  - id: "SYNC-017"
    name: "Update DiffViewer for all scopes"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-015"]
    estimate: "0.5 pts"
    model: "sonnet"

parallelization:
  batch_1: ["SYNC-013", "SYNC-014", "SYNC-015"]
  batch_2: ["SYNC-016", "SYNC-017"]

quality_gates:
  - "All three sync directions use consistent hook and dialog patterns"
  - "Source vs Project comparison shows transitive changes"
  - "ComparisonSelector enables all valid combinations"
  - "DiffViewer displays correct labels for each scope"
  - "Code duplication reduced by >60%"
---

# Phase 3: Unified Flow Integration & Source vs Project

**Goal**: Extract shared patterns, add Source vs Project direct comparison, ensure all three flows use consistent UX.

**Duration**: 2-3 days | **Story Points**: 5

**Depends on**: Phase 1 and Phase 2 complete

## Task Details

### SYNC-013: Extract shared useConflictCheck pattern

**File**: `skillmeat/web/hooks/use-conflict-check.ts`

**Requirements**:
- Refactor `usePreDeployCheck` and `usePrePushCheck` into single hook
- Direction parameter: `'deploy' | 'push' | 'pull'`
- Returns consistent interface for all directions
- Deprecate individual hooks (keep as wrappers for backwards compat)

### SYNC-014: Create SyncConfirmationDialog base

**File**: `skillmeat/web/components/sync-status/sync-confirmation-dialog.tsx`

**Requirements**:
- Shared base component for all sync confirmations
- Configurable: direction, diff data, action handlers
- Reduces duplication between deploy and push dialogs
- Composable with direction-specific messaging

### SYNC-015: Add Source vs Project comparison

**File**: `skillmeat/web/components/sync-status/comparison-selector.tsx`

**Requirements**:
- New option: "Source vs Project"
- Only enabled when both source and project exist
- Updates DiffViewer labels appropriately
- Clear visual distinction from other options

### SYNC-016: Implement source-vs-project diff API call

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- New TanStack Query for combined diff
- Fetches both upstream-diff and project-diff
- Computes transitive changes (what's in source but not in project)
- Handles case where collection is intermediate

### SYNC-017: Update DiffViewer for all scopes

**File**: `skillmeat/web/components/entity/diff-viewer.tsx`

**Requirements**:
- Labels correct for all three comparison scopes
- Source vs Project: "Source" (left), "Project" (right)
- No rendering changes needed, just label configuration

## Quick Reference

### Execute Phase

```text
# Batch 1: Consolidation and new feature (parallel)
Task("ui-engineer-enhanced", "SYNC-013: Extract shared useConflictCheck hook
  File: skillmeat/web/hooks/use-conflict-check.ts
  Single hook with direction parameter handles deploy/push/pull
  Keep usePreDeployCheck and usePrePushCheck as thin wrappers", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-014: Create SyncConfirmationDialog base component
  File: skillmeat/web/components/sync-status/sync-confirmation-dialog.tsx
  Shared dialog component for all sync confirmations
  Reduces duplication between deploy and push dialogs", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-015: Add Source vs Project comparison to ComparisonSelector
  File: skillmeat/web/components/sync-status/comparison-selector.tsx
  New option 'source-vs-project'
  Only enabled when hasValidUpstreamSource AND projectPath exists")

# Batch 2: API and viewer updates (after batch 1)
Task("ui-engineer-enhanced", "SYNC-016: Implement source-vs-project diff query
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  Query that fetches both diffs and computes transitive changes")

Task("ui-engineer-enhanced", "SYNC-017: Update DiffViewer label configuration for all scopes
  File: skillmeat/web/components/entity/diff-viewer.tsx
  Correct labels for source-vs-project scope", model="sonnet")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-3-progress.md \
  --updates "SYNC-013:completed,SYNC-014:completed,SYNC-015:completed"
```
