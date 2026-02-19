---
type: progress
prd: marketplace-source-detection-improvements
phase: 4
phase_name: Frontend UI
status: not_started
progress: 0
total_tasks: 17
completed_tasks: 0
effort: 20-28 pts
created: 2026-01-05
updated: 2026-01-05
assigned_to:
- ui-engineer-enhanced
dependencies:
- 3
tasks:
- id: P4.1a
  name: Create DirectoryMapModal component
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P3.4b
  effort: 4 pts
- id: P4.1b
  name: Implement file tree rendering
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.1a
  effort: 3 pts
- id: P4.1c
  name: Implement type dropdown
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.1a
  effort: 3 pts
- id: P4.1d
  name: Implement hierarchical logic
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.1b
  - P4.1c
  effort: 3 pts
- id: P4.1e
  name: Add save/cancel/rescan buttons
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.1d
  effort: 2 pts
- id: P4.1f
  name: Unit tests for modal
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.1e
  effort: 3 pts
- id: P4.2a
  name: Add Map Directories button
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.1f
  effort: 2 pts
- id: P4.2b
  name: Wire button to modal
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.2a
  effort: 1 pt
- id: P4.2c
  name: Test toolbar integration
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.2b
  effort: 1 pt
- id: P4.3a
  name: Display current mappings
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.2c
  effort: 2 pts
- id: P4.3b
  name: Show dedup counts in scan results
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.3a
  effort: 2 pts
- id: P4.3c
  name: Add duplicate badge to entries
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.3b
  effort: 2 pts
- id: P4.3d
  name: Update marketplace.ts types
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.3c
  effort: 2 pts
- id: P4.3e
  name: Test source detail updates
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.3d
  effort: 2 pts
- id: P4.4a
  name: Add dedup count to scan toast
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.3e
  effort: 2 pts
- id: P4.4b
  name: Add filter for duplicates in excluded list
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.4a
  effort: 2 pts
- id: P4.4c
  name: Test notifications
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4.4b
  effort: 1 pt
parallelization:
  batch_1:
  - P4.1a
  batch_2:
  - P4.1b
  - P4.1c
  batch_3:
  - P4.1d
  batch_4:
  - P4.1e
  batch_5:
  - P4.1f
  batch_6:
  - P4.2a
  batch_7:
  - P4.2b
  batch_8:
  - P4.2c
  batch_9:
  - P4.3a
  batch_10:
  - P4.3b
  batch_11:
  - P4.3c
  batch_12:
  - P4.3d
  batch_13:
  - P4.3e
  batch_14:
  - P4.4a
  batch_15:
  - P4.4b
  batch_16:
  - P4.4c
schema_version: 2
doc_type: progress
feature_slug: marketplace-source-detection-improvements
---

# Phase 4: Frontend UI

## Overview

Build directory mapping modal, integrate with toolbar, and display deduplication results.

**Duration**: 5-7 days
**Effort**: 20-28 pts
**Assigned**: ui-engineer-enhanced
**Dependencies**: Phase 3 complete

## Orchestration Quick Reference

**Batch 4.1** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1a: Create DirectoryMapModal component in skillmeat/web/components/marketplace/DirectoryMapModal.tsx with Radix Dialog")
```

**Batch 4.2** (Parallel - 2 tasks):
```
Task("ui-engineer-enhanced", "P4.1b: Implement file tree rendering in modal using source.tree_data from GitHub API")
Task("ui-engineer-enhanced", "P4.1c: Implement artifact type dropdown for each directory (skill, command, agent, mcp_server, hook)")
```

**Batch 4.3** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1d: Implement hierarchical logic - selecting parent directory auto-selects children")
```

**Batch 4.4** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1e: Add Save, Cancel, and Rescan buttons to modal with proper state management")
```

**Batch 4.5** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1f: Unit tests for DirectoryMapModal component using Jest and React Testing Library")
```

**Batch 4.6** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.2a: Add Map Directories button to source-toolbar.tsx in marketplace source detail page", model="sonnet")
```

**Batch 4.7** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.2b: Wire Map Directories button to open DirectoryMapModal", model="sonnet")
```

**Batch 4.8** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.2c: Test toolbar integration - button opens modal correctly", model="sonnet")
```

**Batch 4.9** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3a: Display current manual_map mappings in source detail page", model="sonnet")
```

**Batch 4.10** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3b: Show dedup counts in scan results notification (X duplicates removed, Y cross-source)", model="sonnet")
```

**Batch 4.11** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3c: Add duplicate badge to catalog entries that were marked as duplicates", model="sonnet")
```

**Batch 4.12** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3d: Update skillmeat/web/types/marketplace.ts to include manual_map and dedup fields", model="sonnet")
```

**Batch 4.13** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3e: Test source detail page displays manual_map and dedup counts correctly", model="sonnet")
```

**Batch 4.14** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.4a: Add dedup count to scan toast notification message", model="sonnet")
```

**Batch 4.15** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.4b: Add filter option to show only duplicates in excluded entries list", model="sonnet")
```

**Batch 4.16** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.4c: Test notifications display dedup counts and filter works correctly", model="sonnet")
```

## Quality Gates

- [ ] DirectoryMapModal renders file tree correctly
- [ ] Hierarchical selection works (parent → children)
- [ ] Save persists mappings via PATCH endpoint
- [ ] Rescan triggers scan with new mappings
- [ ] Dedup counts displayed in UI correctly
- [ ] All UI components tested with unit tests

## Key Files

- `skillmeat/web/components/marketplace/DirectoryMapModal.tsx` - New modal component
- `skillmeat/web/components/marketplace/source-toolbar.tsx` - Add Map Directories button
- `skillmeat/web/types/marketplace.ts` - Add manual_map and dedup types
- `skillmeat/web/hooks/use-marketplace.ts` - PATCH mutation for manual_map

## UI Components

| Component | Purpose |
|-----------|---------|
| DirectoryMapModal | Modal for mapping directories to artifact types |
| Map Directories button | Toolbar button to open modal |
| Mapping display | Show current mappings in source detail |
| Duplicate badge | Visual indicator on excluded duplicates |
| Toast notification | Show dedup counts after scan |

## Notes

- **UI Library**: Radix UI for modal/dialog components
- **Tree Rendering**: Use source.tree_data from GitHub API
- **Artifact Types**: skill, command, agent, mcp_server, hook
- **Hierarchical Logic**: Parent selection cascades to children
- **State Management**: React hooks + TanStack Query
