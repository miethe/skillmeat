---
type: progress
prd: "artifact-flow-modal-redesign"
phase: 2
title: "SyncStatusTab Composite Component"
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
  - id: "TASK-2.1"
    description: "Create SyncStatusTab orchestration component (~300 lines)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-1.1", "TASK-1.2", "TASK-1.3", "TASK-1.4", "TASK-1.5"]
    estimated_effort: "3h"
    priority: "high"
    file: "skillmeat/web/components/entity/sync-status/sync-status-tab.tsx"

parallelization:
  batch_1: ["TASK-2.1"]
  critical_path: ["TASK-2.1"]
---

# Phase 2: SyncStatusTab Composite Component

**Objective**: Orchestrate all 5 Phase 1 components with state management, API hooks, and event handlers.

## Orchestration Quick Reference

**Batch 1** (Sequential - Blocked by Phase 1):
- TASK-2.1 → SyncStatusTab (~300 lines, 3h)
  - **Blocked by**: TASK-1.1, TASK-1.2, TASK-1.3, TASK-1.4, TASK-1.5

### Task Delegation Commands

```bash
# After Phase 1 completes
Task("ui-engineer-enhanced", "TASK-2.1: Create SyncStatusTab orchestration component. Imports all 5 Phase 1 components. Implements state management (comparisonScope, selectedFile, pendingActions). Integrates query hooks (useUpstreamDiff, useProjectDiff, useFileContent). Integrates mutation hooks (useSync, useDeploy). Implements 3-panel layout (FileTree | Comparison+Diff | Preview). File: skillmeat/web/components/entity/sync-status/sync-status-tab.tsx. ~300 lines.")
```

## Tasks

| ID | Component | Lines | Est | Agent | Dependencies | Status |
|----|-----------|-------|-----|-------|--------------|--------|
| TASK-2.1 | SyncStatusTab | ~300 | 3h | ui-engineer-enhanced | Phase 1 (all) | ⏳ Pending |

## Implementation Requirements

### State Management
- `comparisonScope`: "collection-vs-project" | "source-vs-collection" | "source-vs-project"
- `selectedFile`: string | null
- `pendingActions`: PendingAction[]

### Query Hooks
- `useQuery` for upstream diff (source vs collection)
- `useQuery` for project diff (collection vs project)
- `useQuery` for file content (preview)

### Mutation Hooks
- `useSync` for pull from source
- `useDeploy` for deploy to project
- `usePushToCollection` stub (Coming Soon)

### Layout Structure
```
┌─────────────────────────────────────────────────────────┐
│              ArtifactFlowBanner (full width)            │
├──────────┬───────────────────────────┬──────────────────┤
│ FileTree │  ComparisonSelector       │                  │
│ (240px)  │  DriftAlertBanner         │ FilePreviewPane  │
│          │  DiffViewer               │ (320px)          │
├──────────┴───────────────────────────┴──────────────────┤
│              SyncActionsFooter (full width)             │
└─────────────────────────────────────────────────────────┘
```

## Success Criteria

- [ ] All 5 Phase 1 components imported and rendered
- [ ] State management implemented (comparisonScope, selectedFile, pendingActions)
- [ ] Query hooks integrated and working
- [ ] Mutation hooks integrated with success/error handling
- [ ] 3-panel layout renders correctly
- [ ] Event handlers wired (comparison change, file select, actions)
- [ ] Loading states display during queries/mutations
- [ ] Error states handled with toast notifications
- [ ] TypeScript types fully defined

## Next Phase

Phase 3 will integrate SyncStatusTab into unified-entity-modal.tsx.
