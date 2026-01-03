---
type: progress
prd: "marketplace-source-enhancements"
phase: 3
title: "Frontend Exclusions"
status: completed
progress: 100
total_tasks: 8
completed_tasks: 8
created_at: "2025-12-31"
updated_at: "2025-12-31"

tasks:
  - id: "TASK-3.1"
    title: "Add exclusion hooks"
    description: "Create useExcludeCatalogEntry, useRestoreCatalogEntry mutations"
    status: "completed"
    assigned_to: ["ui-engineer"]
    dependencies: []
    estimated_time: "2h"
    files:
      - "skillmeat/web/hooks/useMarketplaceSources.ts"

  - id: "TASK-3.2"
    title: "Create ExcludeArtifactDialog component"
    description: "Confirmation dialog with Radix Dialog for marking artifacts as excluded"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_time: "2h"
    files:
      - "skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx"

  - id: "TASK-3.3"
    title: "Add 'Not an Artifact' link to CatalogCard"
    description: "Integrate exclusion trigger into catalog card UI"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1", "TASK-3.2"]
    estimated_time: "1h"
    files:
      - "skillmeat/web/app/marketplace/sources/[id]/components/"

  - id: "TASK-3.4"
    title: "Create ExcludedArtifactsList component"
    description: "Collapsible table showing excluded entries with restore action"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimated_time: "2h"
    files:
      - "skillmeat/web/app/marketplace/sources/[id]/components/excluded-list.tsx"

  - id: "TASK-3.5"
    title: "Integrate excluded list into source page"
    description: "Add collapsible section below catalog grid"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.4"]
    estimated_time: "1h"
    files:
      - "skillmeat/web/app/marketplace/sources/[id]/page.tsx"

  - id: "TASK-3.6"
    title: "Update Select All to skip excluded"
    description: "Filter excluded entries from bulk selection"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimated_time: "1h"
    files:
      - "skillmeat/web/app/marketplace/sources/[id]/page.tsx"

  - id: "TASK-3.7"
    title: "Add excluded status badge"
    description: "Visual indicator for excluded entries in cards and lists"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_time: "0.5h"
    files:
      - "skillmeat/web/components/marketplace/"

  - id: "TASK-3.8"
    title: "E2E test for exclusion workflow"
    description: "Test mark -> disappear -> restore -> reappear flow"
    status: "completed"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.3", "TASK-3.5"]
    estimated_time: "1.5h"
    files:
      - "skillmeat/web/tests/e2e/marketplace-exclusion.spec.ts"

parallelization:
  batch_1: ["TASK-3.1", "TASK-3.2", "TASK-3.7"]
  batch_2: ["TASK-3.3", "TASK-3.4"]
  batch_3: ["TASK-3.5", "TASK-3.6", "TASK-3.8"]
  critical_path: ["TASK-3.1", "TASK-3.4", "TASK-3.5"]
  estimated_total_time: "11h"

blockers: []
---

# Phase 3: Frontend Exclusions

Build UI for marking, viewing, and restoring excluded artifacts.

## Deliverables

- Exclusion dialog component
- "Not an Artifact" link on catalog cards
- Excluded artifacts list section
- TanStack Query mutations

## Orchestration Quick Reference

**Batch 1** (Parallel - No dependencies):
- TASK-3.1 → `ui-engineer` (2h)
- TASK-3.2 → `ui-engineer-enhanced` (2h)
- TASK-3.7 → `ui-engineer-enhanced` (0.5h)

### Task Delegation Commands - Batch 1

```
Task("ui-engineer", "TASK-3.1: Add exclusion hooks
     File: skillmeat/web/hooks/useMarketplaceSources.ts
     - useExcludeCatalogEntry: useMutation, PATCH /marketplace/sources/{sourceId}/artifacts/{entryId}/exclude with excluded=true
     - useRestoreCatalogEntry: useMutation, PATCH same endpoint with excluded=false
     - onSuccess: invalidate catalog query (marketplaceSourceKeys)
     - onError: show toast with error message
     - Follow existing mutation patterns in the file")

Task("ui-engineer-enhanced", "TASK-3.2: Create ExcludeArtifactDialog
     File: skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx
     - Use Radix Dialog primitive (AlertDialog)
     - Props: entry (CatalogEntry), open (bool), onOpenChange, onConfirm
     - Message: 'Mark this as not an artifact?'
     - Show entry name, note about Excluded list recovery
     - Buttons: Cancel (variant='outline'), Mark as Excluded (variant='destructive')
     - Call onConfirm when confirmed")

Task("ui-engineer-enhanced", "TASK-3.7: Add excluded status badge
     - Find status badge component/logic in catalog card or create reusable
     - Add case: status === 'excluded' -> Badge with 'Excluded' text
     - Styling: className='border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-800'
     - Should work in catalog card and excluded list table")
```

**Batch 2** (Depends on Batch 1):
- TASK-3.3 → `ui-engineer-enhanced` (1h) - depends: [TASK-3.1, TASK-3.2]
- TASK-3.4 → `ui-engineer-enhanced` (2h) - depends: [TASK-3.1]

### Task Delegation Commands - Batch 2

```
Task("ui-engineer-enhanced", "TASK-3.3: Add 'Not an Artifact' link to CatalogCard
     - Find CatalogCard or catalog entry component: grep 'CatalogCard' or look in app/marketplace/sources/[id]/components/
     - Add link below Import button: 'Not an artifact'
     - Styling: text-sm text-muted-foreground hover:underline cursor-pointer
     - Opens ExcludeArtifactDialog with entry prop
     - Only render if entry.status !== 'excluded'
     - Use useExcludeCatalogEntry hook on confirm")

Task("ui-engineer-enhanced", "TASK-3.4: Create ExcludedArtifactsList component
     File: skillmeat/web/app/marketplace/sources/[id]/components/excluded-list.tsx
     - Use Radix Collapsible for section
     - Header: 'Show Excluded Artifacts ({excludedCount})' with ChevronDown/Up icon
     - Table columns: Name, Path, Excluded At (formatted with date-fns), Actions
     - Restore button in Actions: calls useRestoreCatalogEntry
     - Empty state: 'No excluded artifacts found'
     - Props: excludedEntries (CatalogEntry[]), sourceId (string)")
```

**Batch 3** (Depends on Batch 2):
- TASK-3.5 → `ui-engineer-enhanced` (1h) - depends: [TASK-3.4]
- TASK-3.6 → `ui-engineer-enhanced` (1h) - depends: [TASK-3.1]
- TASK-3.8 → `ui-engineer` (1.5h) - depends: [TASK-3.3, TASK-3.5]

### Task Delegation Commands - Batch 3

```
Task("ui-engineer-enhanced", "TASK-3.5: Integrate excluded list into source page
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx
     - Import ExcludedArtifactsList component
     - Filter excluded entries from catalog query result: entries.filter(e => e.status === 'excluded')
     - Render ExcludedArtifactsList below catalog grid
     - Pass excludedEntries and sourceId props
     - Default collapsed, show count in header")

Task("ui-engineer-enhanced", "TASK-3.6: Update Select All to skip excluded
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx
     - Find bulk import/select all logic
     - Filter: const importableEntries = entries.filter(e => e.status !== 'excluded')
     - Update Select All button: use importableEntries.length
     - Show excluded count separately if > 0: 'X excluded entries skipped'")

Task("ui-engineer", "TASK-3.8: E2E test for exclusion workflow
     File: skillmeat/web/tests/e2e/marketplace-exclusion.spec.ts (or appropriate test directory)
     - Setup: navigate to marketplace source detail page with catalog entries
     - Action 1: click 'Not an artifact' on first card -> confirm dialog
     - Assert 1: card disappears from grid
     - Action 2: open 'Show Excluded Artifacts' -> click Restore
     - Assert 2: card reappears in grid
     - Assert 3: counts update correctly (excluded count decreases)")
```

## Quality Gates

- [ ] Exclusion mutation <500ms round-trip
- [ ] Excluded entries disappear from grid immediately (optimistic update)
- [ ] Excluded list updates on restore
- [ ] Select All count excludes excluded entries
- [ ] E2E test passes on CI
- [ ] No flickering or layout shift during mutations
- [ ] Accessibility: dialog keyboard-navigable, focus management

## Work Log

| Date | Task | Status | Notes |
|------|------|--------|-------|
| 2025-12-31 | Phase 3 initialized | Started | Progress file created |
| 2025-12-31 | Batch 1 completed | Done | Exclusion hooks, dialog, status badge |
| 2025-12-31 | Batch 2 completed | Done | CatalogCard link, ExcludedArtifactsList |
| 2025-12-31 | Batch 3 completed | Done | Integration, Select All, E2E tests |
| 2025-12-31 | Phase 3 completed | Done | All 8 tasks complete, commit 92f4189 |
