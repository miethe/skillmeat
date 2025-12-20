---
type: progress
prd: "artifact-deletion-v1"
phase: 2
title: "Integration Points"
status: pending
progress: 0
total_tasks: 5
completed_tasks: 0
blocked_tasks: 0
created: "2025-12-20"
updated: "2025-12-20"

tasks:
  - id: "FE-009"
    title: "Modify EntityActions to use ArtifactDeletionDialog"
    status: "pending"
    priority: "high"
    estimate: "1pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    file_targets:
      - "skillmeat/web/components/entity/entity-actions.tsx"
    notes: "Replace simple delete dialog with ArtifactDeletionDialog component"

  - id: "FE-010"
    title: "Add Delete button to UnifiedEntityModal Overview tab"
    status: "pending"
    priority: "high"
    estimate: "0.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    file_targets:
      - "skillmeat/web/components/entity/unified-entity-modal.tsx"
    notes: "Add Delete button beside Edit Parameters button in Overview tab"

  - id: "FE-011"
    title: "Integration tests for deletion flow"
    status: "pending"
    priority: "medium"
    estimate: "1.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-009", "FE-010"]
    file_targets:
      - "skillmeat/web/__tests__/integration/artifact-deletion.test.tsx"
    notes: "Test full flow from card menu through dialog to API calls"

  - id: "FE-012"
    title: "E2E test for artifact deletion"
    status: "pending"
    priority: "medium"
    estimate: "1.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-011"]
    file_targets:
      - "skillmeat/web/tests/artifact-deletion.spec.ts"
    notes: "Playwright E2E test for deletion from collection and project pages"

  - id: "FE-013"
    title: "Verify error handling across integration points"
    status: "pending"
    priority: "low"
    estimate: "0.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-011"]
    file_targets: []
    notes: "Verify toast notifications, error states, and recovery paths"

parallelization:
  batch_1: ["FE-009", "FE-010"]
  batch_2: ["FE-011"]
  batch_3: ["FE-012", "FE-013"]

blockers: []

phase_dependencies:
  - phase: 1
    required_tasks: ["FE-003", "FE-005"]

references:
  prd: "docs/project_plans/PRDs/features/artifact-deletion-v1.md"
  implementation_plan: "docs/project_plans/implementation_plans/features/artifact-deletion-v1.md"
---

# Phase 2: Integration Points

## Summary

Phase 2 integrates the ArtifactDeletionDialog into existing components (EntityActions and UnifiedEntityModal) and adds comprehensive integration and E2E tests.

**Estimated Effort**: 5 story points (2-3 days)
**Dependencies**: Phase 1 completion (FE-003, FE-005)
**Assigned Agents**: ui-engineer-enhanced

## Orchestration Quick Reference

### Batch 1 (Parallel - FE-009 and FE-010)

**FE-009** → `ui-engineer-enhanced` (1pt)

```
Task("ui-engineer-enhanced", "FE-009: Modify EntityActions to use ArtifactDeletionDialog.

File: skillmeat/web/components/entity/entity-actions.tsx

Changes:
1. Import ArtifactDeletionDialog from './artifact-deletion-dialog'
2. Add state: showDeletionDialog: boolean
3. Replace onClick={() => setShowDeleteDialog(true)} with setShowDeletionDialog(true)
4. Remove the existing simple Dialog for delete confirmation (lines ~177-199)
5. Add ArtifactDeletionDialog component at end of component:
   <ArtifactDeletionDialog
     entity={entity}
     open={showDeletionDialog}
     onOpenChange={setShowDeletionDialog}
     context={entity.projectPath ? 'project' : 'collection'}
     projectPath={entity.projectPath}
     onSuccess={() => {
       onDelete?.();
       setShowDeletionDialog(false);
     }}
   />

Preserve existing dropdown menu structure - only change what happens on delete click.")
```

**FE-010** → `ui-engineer-enhanced` (0.5pt)

```
Task("ui-engineer-enhanced", "FE-010: Add Delete button to UnifiedEntityModal Overview tab.

File: skillmeat/web/components/entity/unified-entity-modal.tsx

Changes:
1. Import ArtifactDeletionDialog from './artifact-deletion-dialog'
2. Add state: showDeletionDialog: boolean (near line 288)
3. In Overview tab header (around line 1324-1334), add Delete button:
   <div className='flex justify-end gap-2'>
     <Button
       variant='outline'
       size='sm'
       className='text-destructive hover:text-destructive hover:bg-destructive/10'
       onClick={() => setShowDeletionDialog(true)}
     >
       <Trash2 className='mr-2 h-4 w-4' />
       Delete
     </Button>
     <Button variant='outline' size='sm' onClick={() => setShowParameterEditor(true)}>
       <Pencil className='mr-2 h-4 w-4' />
       Edit Parameters
     </Button>
   </div>
4. Add ArtifactDeletionDialog at end of component (before closing fragments)

Import Trash2 from lucide-react.")
```

### Batch 2 (Sequential - Depends on Batch 1)

**FE-011** → `ui-engineer-enhanced` (1.5pt)

```
Task("ui-engineer-enhanced", "FE-011: Integration tests for deletion flow.

File: skillmeat/web/__tests__/integration/artifact-deletion.test.tsx

Test cases:
1. EntityActions: Click delete → dialog opens with correct context
2. EntityActions: Collection context → shows 'Delete from Projects' toggle
3. EntityActions: Project context → shows 'Delete from Collection' toggle
4. UnifiedEntityModal: Delete button in Overview opens dialog
5. Full flow: Toggle on → expand section → select items → delete → API called
6. Cache invalidation: After delete, queries refetch
7. Dialog closes on success
8. Error toast on failure

Setup:
- Mock useArtifactDeletion hook
- Mock useDeploymentList for expansion sections
- Render components with QueryClient wrapper

Use @testing-library/react with userEvent for interactions.")
```

### Batch 3 (Parallel - FE-012 and FE-013)

**FE-012** → `ui-engineer-enhanced` (1.5pt)

```
Task("ui-engineer-enhanced", "FE-012: E2E test for artifact deletion.

File: skillmeat/web/tests/artifact-deletion.spec.ts

Playwright E2E tests:

1. Delete from Collection page:
   - Navigate to /collection
   - Click artifact card menu (...)
   - Click Delete
   - Verify dialog shows with 'Delete from Collection' context
   - Toggle 'Also delete from Projects' → verify expansion
   - Click Delete → verify API call made
   - Verify artifact removed from list

2. Delete from Project page:
   - Navigate to /projects/[id]
   - Click artifact card menu
   - Click Delete
   - Verify 'Delete from Project' context
   - Complete deletion
   - Verify removed from project view

3. Delete from Modal:
   - Open artifact modal
   - Go to Overview tab
   - Click Delete button
   - Complete flow

Setup: Use test API with mock data or real local API.
Consider test fixtures for consistent state.")
```

**FE-013** → `ui-engineer-enhanced` (0.5pt)

```
Task("ui-engineer-enhanced", "FE-013: Verify error handling across integration points.

Manual verification and test review:

1. Network failure during deletion:
   - API returns 500 → error toast shown
   - Dialog remains open for retry

2. Partial failure (multiple undeployments):
   - Some succeed, some fail
   - Error message lists what failed
   - User can retry

3. 404 artifact not found:
   - Artifact deleted elsewhere
   - Clear message, dialog closes

4. Validation error (400):
   - Invalid request format
   - Clear error message

Verify toast notifications use correct variant (destructive for errors).
Verify dialog loading states during operations.")
```

## Key Files

| File | Purpose | Changes |
|------|---------|---------|
| `components/entity/entity-actions.tsx` | Card menu | +40 LOC |
| `components/entity/unified-entity-modal.tsx` | Modal overview | +30 LOC |
| `__tests__/integration/artifact-deletion.test.tsx` | Integration tests | ~200 LOC |
| `tests/artifact-deletion.spec.ts` | E2E tests | ~150 LOC |

## Acceptance Criteria

- [ ] EntityActions Delete opens new dialog (not simple confirmation)
- [ ] Modal Overview tab has Delete button beside Edit Parameters
- [ ] Context correctly detected (collection vs project)
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Error handling works across all entry points
- [ ] Cache invalidation triggers UI updates

## Notes

- EntityActions already has onDelete prop - just change what dialog is shown
- UnifiedEntityModal has pattern for parameter editor modal to follow
- Both entry points should use same ArtifactDeletionDialog component
