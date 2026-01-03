---
type: progress
prd: "marketplace-source-enhancements-v1"
phase: 3
title: "Frontend Exclusions"
status: pending
progress: 0
total_tasks: 8
completed_tasks: 0
story_points: 8

tasks:
  - id: "TASK-3.1"
    title: "Update marketplace types with excluded status"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: []
    estimate: "0.5h"
  - id: "TASK-3.2"
    title: "Add exclude/restore mutations to hooks"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.1"]
    estimate: "1h"
  - id: "TASK-3.3"
    title: "Create ExcludeArtifactDialog component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    estimate: "2h"
  - id: "TASK-3.4"
    title: "Add exclude button to CatalogCard"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.2", "TASK-3.3"]
    estimate: "1h"
  - id: "TASK-3.5"
    title: "Create ExcludedArtifactsList component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.2"]
    estimate: "2h"
  - id: "TASK-3.6"
    title: "Integrate excluded list into source page"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.5"]
    estimate: "1h"
  - id: "TASK-3.7"
    title: "Update Select All logic"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.4"]
    estimate: "0.5h"
  - id: "TASK-3.8"
    title: "Frontend integration tests"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.6", "TASK-3.7"]
    estimate: "2h"

parallelization:
  batch_1: ["TASK-3.1"]
  batch_2: ["TASK-3.2", "TASK-3.3"]
  batch_3: ["TASK-3.4", "TASK-3.5"]
  batch_4: ["TASK-3.6", "TASK-3.7"]
  batch_5: ["TASK-3.8"]

blockers: []
---

# Phase 3: Frontend Exclusions

## Overview

Frontend implementation of the "Not an Artifact" marking feature. Requires Phase 2 backend to be complete.

## Dependencies
- Phase 2 complete (backend API ready)

## Orchestration Quick Reference

### Batch 1 (No Dependencies)
```
Task("ui-engineer", "TASK-3.1: Update marketplace types.
     File: skillmeat/web/types/marketplace.ts
     - Add 'excluded' to CatalogStatus type
     - Add excluded_at?: string to CatalogEntry
     - Add excluded_reason?: string to CatalogEntry
     - Update statusConfig with excluded styling (gray)")
```

### Batch 2 (After Batch 1)
```
Task("ui-engineer", "TASK-3.2: Add exclude/restore mutations.
     File: skillmeat/web/hooks/useMarketplaceSources.ts
     - useExcludeArtifact mutation (PATCH)
     - useRestoreArtifact mutation (DELETE)
     - Invalidate catalog cache on success
     - Handle optimistic updates")

Task("ui-engineer-enhanced", "TASK-3.3: Create ExcludeArtifactDialog.
     File: skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx
     - Confirmation dialog with optional reason input
     - 'Are you sure?' warning text
     - Cancel and Confirm buttons
     - Loading state during mutation")
```

### Batch 3 (After Batch 2)
```
Task("ui-engineer-enhanced", "TASK-3.4: Add exclude button to CatalogCard.
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx
     - Add 'Not an Artifact' button/link next to Import
     - Only show for non-excluded entries
     - Opens ExcludeArtifactDialog on click
     - Disabled state while mutation pending")

Task("ui-engineer-enhanced", "TASK-3.5: Create ExcludedArtifactsList.
     File: skillmeat/web/components/marketplace/excluded-artifacts-list.tsx
     - Collapsible section 'Excluded Artifacts (N)'
     - List excluded entries with restore button
     - Show exclusion reason and date
     - Empty state when none excluded")
```

### Batch 4 (After Batch 3)
```
Task("ui-engineer", "TASK-3.6: Integrate excluded list.
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx
     - Add ExcludedArtifactsList below main catalog
     - Query with include_excluded=true for this section
     - Collapsed by default")

Task("ui-engineer", "TASK-3.7: Update Select All logic.
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx
     - Ensure excluded entries not in filteredEntries
     - Select All only selects visible non-excluded
     - Already correct since excluded filtered server-side")
```

### Batch 5 (After Batch 4)
```
Task("ui-engineer", "TASK-3.8: Frontend integration tests.
     File: skillmeat/web/app/marketplace/sources/[id]/__tests__/page.test.tsx
     - Test exclude button visibility
     - Test dialog confirmation flow
     - Test excluded list rendering
     - Test restore functionality
     - Test Select All excludes excluded")
```

## Quality Gates
- [ ] All 8 tasks complete
- [ ] Integration tests passing
- [ ] Exclude flow <500ms total
- [ ] Restore flow <500ms total
- [ ] No console errors
- [ ] Accessible dialogs (focus trap, ARIA)
