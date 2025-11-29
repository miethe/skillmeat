---
type: progress
prd: "artifact-flow-modal-redesign"
phase: 3
title: "Integration into Unified Entity Modal"
status: pending
progress: 0
total_tasks: 1
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["ui-engineer-enhanced"]
created: "2025-11-29"
updated: "2025-11-29"

tasks:
  - id: "TASK-3.1"
    description: "Integrate SyncStatusTab into unified-entity-modal.tsx (~100 lines)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "1h"
    priority: "high"
    file: "skillmeat/web/components/entity/unified-entity-modal.tsx"

parallelization:
  batch_1: ["TASK-3.1"]
  critical_path: ["TASK-3.1"]
---

# Phase 3: Integration into Unified Entity Modal

**Objective**: Replace existing "Sync Status" tab content with SyncStatusTab component.

## Orchestration Quick Reference

**Batch 1** (Sequential - Blocked by Phase 2):
- TASK-3.1 → Integration (~100 lines, 1h)
  - **Blocked by**: TASK-2.1

### Task Delegation Commands

```bash
# After Phase 2 completes
Task("ui-engineer-enhanced", "TASK-3.1: Integrate SyncStatusTab into unified-entity-modal.tsx. Replace existing Sync Status tab content. Wire entity, mode, and projectPath props. Ensure tab switching works. Update modal size if needed (suggest max-w-7xl, max-h-[90vh]). File: skillmeat/web/components/entity/unified-entity-modal.tsx. ~100 lines changed.")
```

## Tasks

| ID | Task | Lines | Est | Agent | Dependencies | Status |
|----|------|-------|-----|-------|--------------|--------|
| TASK-3.1 | Integration | ~100 | 1h | ui-engineer-enhanced | TASK-2.1 | ⏳ Pending |

## Integration Steps

1. Import SyncStatusTab component
2. Replace TabsContent for "sync-status" tab
3. Pass props: entity, mode, projectPath, onClose
4. Update modal size (max-w-7xl for 3-panel layout)
5. Remove old sync status implementation
6. Test tab switching and modal lifecycle

## Success Criteria

- [ ] SyncStatusTab component imported
- [ ] Sync Status tab renders new component
- [ ] All other tabs (Overview, Edit, History) still work
- [ ] Entity data flows correctly to SyncStatusTab
- [ ] Mode and projectPath props passed correctly
- [ ] Modal size accommodates 3-panel layout
- [ ] Modal closes correctly via all methods
- [ ] Dark mode works
- [ ] No TypeScript errors

## Next Phase

Phase 4 will wire all action buttons and add Coming Soon tooltips.
