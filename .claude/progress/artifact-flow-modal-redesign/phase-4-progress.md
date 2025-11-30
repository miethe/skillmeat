---
type: progress
prd: "artifact-flow-modal-redesign"
phase: 4
title: "Polish & Action Wiring"
status: "completed"
progress: 100
total_tasks: 2
completed_tasks: 2
in_progress_tasks: 0
blocked_tasks: 0
owners: ["ui-engineer-enhanced"]
created: "2025-11-29"
updated: "2025-11-29"

tasks:
  - id: "TASK-4.1"
    description: "Wire all action buttons to API hooks (~100 lines)"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimated_effort: "2h"
    priority: "high"
    files:
      - "skillmeat/web/components/entity/sync-status/sync-status-tab.tsx"
      - "skillmeat/web/components/entity/sync-status/artifact-flow-banner.tsx"
      - "skillmeat/web/components/entity/sync-status/drift-alert-banner.tsx"
      - "skillmeat/web/components/entity/sync-status/sync-actions-footer.tsx"

  - id: "TASK-4.2"
    description: "Add Coming Soon tooltips for unimplemented features (~50 lines)"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimated_effort: "1h"
    priority: "medium"
    files:
      - "skillmeat/web/components/entity/sync-status/artifact-flow-banner.tsx"
      - "skillmeat/web/components/entity/sync-status/sync-actions-footer.tsx"

parallelization:
  batch_1: ["TASK-4.1", "TASK-4.2"]
  critical_path: ["TASK-4.1"]
---

# Phase 4: Polish & Action Wiring

**Objective**: Wire action buttons to API hooks and add Coming Soon states.

## Orchestration Quick Reference

**Batch 1** (Parallel - Both blocked by Phase 3):
- TASK-4.1 → Wire action buttons (~100 lines, 2h)
- TASK-4.2 → Coming Soon tooltips (~50 lines, 1h)
  - **Blocked by**: TASK-3.1

### Task Delegation Commands

```bash
# After Phase 3 completes - launch in parallel
Task("ui-engineer-enhanced", "TASK-4.1: Wire all action buttons to API hooks. Connect Pull from Source→useSync, Deploy to Project→useDeploy, Sync from Collection→useSync, Merge→MergeWorkflow, Apply→execute pending actions. Add error handling with toast notifications. Add loading states. Refetch queries on success. ~100 lines across 4 files.")

Task("ui-engineer-enhanced", "TASK-4.2: Add Coming Soon tooltips using shadcn/ui Tooltip. Add to: Push to Collection button (ArtifactFlowBanner), Push Local Changes button (SyncActionsFooter), Rollback button (SyncActionsFooter). Tooltips show on hover, buttons are disabled (ghost variant), clicking shows toast. ~50 lines.")
```

## Tasks

| ID | Task | Lines | Est | Agent | Dependencies | Status |
|----|------|-------|-----|-------|--------------|--------|
| TASK-4.1 | Wire Actions | ~100 | 2h | ui-engineer-enhanced | TASK-3.1 | ⏳ Pending |
| TASK-4.2 | Coming Soon Tooltips | ~50 | 1h | ui-engineer-enhanced | TASK-3.1 | ⏳ Pending |

## TASK-4.1: Action Wiring

### Buttons to Wire
- **Pull from Source** → `useSync({ direction: 'upstream' })`
- **Deploy to Project** → `useDeploy()`
- **Sync from Collection** → `useSync({ direction: 'downstream' })`
- **Merge Conflicts** → Open `MergeWorkflow` component
- **Resolve All** → Batch conflict resolution
- **Apply** → Execute pending actions queue
- **Cancel** → Clear actions and close modal

### Requirements
- Loading spinners during mutations
- Success toast notifications
- Error toast with user-friendly messages
- Query invalidation on success
- Disabled state during loading

## TASK-4.2: Coming Soon Tooltips

### Buttons Needing Tooltips
- **Push to Collection** (ArtifactFlowBanner)
  - Tooltip: "Coming Soon: Push local changes to collection"
  - Ghost button, disabled, shows toast on click
- **Push Local Changes** (SyncActionsFooter)
  - Tooltip: "Coming Soon"
  - Ghost button, disabled, shows toast on click
- **Rollback** (SyncActionsFooter - conditional)
  - Tooltip: "Coming Soon: Rollback to previous version"
  - Only visible when entity has version history

### Requirements
- shadcn/ui Tooltip component
- Consistent ghost button styling
- Keyboard accessible (focus triggers tooltip)
- aria-disabled="true" on buttons
- Toast on click with informative message

## Success Criteria

- [ ] All action buttons trigger correct API calls
- [ ] Loading states display during operations
- [ ] Success/error toasts appear appropriately
- [ ] Query invalidation refreshes UI
- [ ] Coming Soon tooltips show on hover
- [ ] Coming Soon buttons disabled and styled correctly
- [ ] Keyboard navigation works
- [ ] No console errors

## Completion Note

All action wiring and polish completed successfully on 2025-11-29:

TASK-4.1: Action Button Wiring
- Pull from Source connected to useSync (upstream direction)
- Deploy to Project connected to useDeploy
- Sync from Collection connected to useSync (downstream direction)
- Merge Conflicts integrated with MergeWorkflow component
- Resolve All implemented for batch conflict resolution
- Apply button executes pending actions queue
- Cancel clears actions and closes modal
- Loading spinners implemented on all mutations
- Success/error toast notifications active
- Query invalidation refreshes UI after mutations
- Proper disabled states during loading

TASK-4.2: Coming Soon Tooltips
- Push to Collection button: Ghost variant, disabled, tooltip active
- Push Local Changes button: Ghost variant, disabled, tooltip active
- Rollback button: Conditional visibility, Coming Soon state
- Tooltips styled with shadcn/ui Tooltip component
- Keyboard accessible (focus triggers tooltips)
- aria-disabled="true" attributes on buttons
- Toast notifications on click with informative messages

## Final Phase

Feature COMPLETED and ready for deployment.

### Delivery Summary
- Phase 1: 5 sub-components created (ArtifactFlowBanner, ComparisonSelector, DriftAlertBanner, FilePreviewPane, SyncActionsFooter)
- Phase 2: SyncStatusTab orchestration component created (476 lines)
- Phase 3: Integration into unified-entity-modal.tsx completed
- Phase 4: All action buttons wired and Coming Soon states implemented
- Total implementation: ~1100+ lines across 8 components
- Ready for production deployment
