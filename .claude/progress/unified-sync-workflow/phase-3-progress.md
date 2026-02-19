---
type: progress
prd: unified-sync-workflow
phase: 3
phase_name: Source vs Project + Merge Integration + Banner
status: completed
progress: 100
created: 2026-02-04
updated: '2026-02-05'
tasks:
- id: SYNC-A01
  name: Source vs Project comparison option
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-B01
  estimate: 1.5 pts
  model: opus
- id: SYNC-A02
  name: DiffViewer label config for all scopes
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-A01
  estimate: 0.5 pts
  model: sonnet
- id: SYNC-A03
  name: Wire MergeWorkflowDialog from unified dialog
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SYNC-U01
  - SYNC-B02
  estimate: 1.5 pts
  model: opus
- id: SYNC-A04
  name: 'Banner styling: push arrow + button'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimate: 0.5 pts
  model: sonnet
parallelization:
  batch_1:
  - SYNC-A01
  - SYNC-A03
  - SYNC-A04
  batch_2:
  - SYNC-A02
quality_gates:
- Source vs Project comparison works with new endpoint
- ComparisonSelector enables all valid combinations
- DiffViewer labels correct for all 3 scopes
- Merge button routes to MergeWorkflowDialog for pull/push
- Merge-capable deploy works via extended API
- Banner push arrow reflects project change status
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
schema_version: 2
doc_type: progress
feature_slug: unified-sync-workflow
---

# Phase 3: Source vs Project + Merge Integration + Banner

**Goal**: Add Source vs Project direct comparison, wire MergeWorkflowDialog from unified dialog, and polish banner visuals.

**Duration**: 2-3 days | **Story Points**: 4

**Depends on**: Phase 1 (SYNC-B01) and Phase 2 (SYNC-U01)

## Task Details

### SYNC-A01: Source vs Project comparison option

**File**: `skillmeat/web/components/sync-status/comparison-selector.tsx`

**Requirements**:
- Add `'source-vs-project'` to ComparisonScope type
- Enable only when `hasValidUpstreamSource(entity) && projectPath`
- Wire to new backend endpoint `GET /artifacts/{id}/source-project-diff`
- New TanStack Query in SyncStatusTab for this scope

### SYNC-A02: DiffViewer label config for all scopes

**File**: `skillmeat/web/components/entity/diff-viewer.tsx` (label configuration)

**Requirements**:
- Source-vs-collection: "Source" (left), "Collection" (right)
- Collection-vs-project: "Collection" (left), "Project" (right)
- Source-vs-project: "Source" (left), "Project" (right)
- Labels dynamically set based on comparison scope

### SYNC-A03: Wire MergeWorkflowDialog from unified dialog

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- When user clicks "Merge" in SyncConfirmationDialog, close it and open MergeWorkflowDialog
- MergeWorkflowDialog is already bidirectional (verified)
- For Pull/Push: route with appropriate snapshot context
- For Deploy merge: use extended deploy API with `strategy='merge'`
- Validate MergeWorkflowDialog can accept project-context parameters

### SYNC-A04: Banner styling: push arrow + button

**File**: `skillmeat/web/components/sync-status/artifact-flow-banner.tsx`

**Requirements**:
- Arrow already solid when `projectInfo` exists (keep)
- Update push button variant to `'default'` when project diff shows changes
- Currently `variant='ghost'` always

## Quick Reference

### Execute Phase

```text
# Batch 1: Independent tasks (parallel)
Task("ui-engineer-enhanced", "SYNC-A01: Add source-vs-project comparison to ComparisonSelector
  File: skillmeat/web/components/sync-status/comparison-selector.tsx
  New option 'source-vs-project', enabled when hasValidUpstreamSource AND projectPath
  Wire to GET /artifacts/{id}/source-project-diff endpoint")

Task("ui-engineer-enhanced", "SYNC-A03: Wire MergeWorkflowDialog from SyncConfirmationDialog
  When user clicks Merge, route to MergeWorkflowDialog with direction context.
  Deploy merge uses extended deploy API. Pull/Push use existing merge endpoints.")

Task("ui-engineer-enhanced", "SYNC-A04: Update push button variant in banner
  File: artifact-flow-banner.tsx. Button variant='default' when changes exist.", model="sonnet")

# Batch 2: After SYNC-A01
Task("ui-engineer-enhanced", "SYNC-A02: Configure DiffViewer labels for all comparison scopes", model="sonnet")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-3-progress.md \
  --updates "SYNC-A01:completed,SYNC-A03:completed,SYNC-A04:completed"
```
