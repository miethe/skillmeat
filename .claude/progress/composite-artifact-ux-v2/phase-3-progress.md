---
type: progress
schema_version: 2
doc_type: progress
prd: composite-artifact-ux-v2
feature_slug: composite-artifact-ux-v2
phase: 3
title: Import Flow Wiring
status: completed
created: '2026-02-19'
updated: '2026-02-19'
prd_ref: docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
overall_progress: 0
completion_estimate: on-track
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
- frontend-developer
- python-backend-engineer
contributors: []
tasks:
- id: CUX-P3-01
  description: Wire CompositePreview into marketplace import dialog; conditionally
    render for composite sources
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P1-01
  - CUX-P2-06
  estimated_effort: 2pt
  priority: high
- id: CUX-P3-02
  description: Wire CompositePreview into collection add flow; conditional on source
    type
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P3-01
  estimated_effort: 1pt
  priority: medium
- id: CUX-P3-03
  description: Wire ConflictResolutionDialog to trigger on hash mismatch during import;
    connect to backend API
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-01
  estimated_effort: 2pt
  priority: high
- id: CUX-P3-04
  description: Create useImportComposite and useMutateComposite mutation hooks with
    optimistic updates and rollback
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-08
  estimated_effort: 2pt
  priority: high
- id: CUX-P3-05
  description: Verify import calls correct backend endpoint for atomic composite +
    children transaction
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CUX-P1-08
  estimated_effort: 1pt
  priority: high
- id: CUX-P3-06
  description: 'Playwright E2E test for marketplace plugin import flow: filter ->
    view -> preview -> confirm -> collection updated'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P3-01
  estimated_effort: 2pt
  priority: medium
- id: CUX-P3-07
  description: 'Playwright E2E test for conflict resolution during import: detect
    -> dialog -> resolve -> import succeeds'
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P3-03
  estimated_effort: 2pt
  priority: medium
parallelization:
  batch_1:
  - CUX-P3-01
  - CUX-P3-03
  - CUX-P3-04
  - CUX-P3-05
  batch_2:
  - CUX-P3-02
  - CUX-P3-06
  - CUX-P3-07
  critical_path:
  - CUX-P3-01
  - CUX-P3-02
  estimated_total_time: 2-3 days
blockers: []
success_criteria:
- id: SC-P3-1
  description: CompositePreview renders in import modal for composite sources
  status: pending
- id: SC-P3-2
  description: ConflictResolutionDialog appears on hash mismatch
  status: pending
- id: SC-P3-3
  description: Import transaction creates composite + children atomically
  status: pending
- id: SC-P3-4
  description: Mutation hooks handle all states correctly
  status: pending
- id: SC-P3-5
  description: No regression in existing atomic artifact imports
  status: pending
- id: SC-P3-6
  description: Core import flow E2E test passes
  status: pending
- id: SC-P3-7
  description: Conflict resolution E2E test passes
  status: pending
files_modified: []
progress: 100
---
# Phase 3: Import Flow Wiring

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-3-progress.md -t CUX-P3-01 -s completed

python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-3-progress.md \
  --updates "CUX-P3-01:completed,CUX-P3-03:completed"
```

---

## Objective

Connect pre-built v1 components (`CompositePreview`, `ConflictResolutionDialog`, `useArtifactAssociations`) into the marketplace and collection import flows. Mostly wiring and conditional rendering -- no major new components.

---

## Orchestration Quick Reference

### Batch 1 (Cross-phase dependencies met — launch in parallel)

```
Task("ui-engineer-enhanced", "CUX-P3-01: Wire CompositePreview into marketplace import dialog.
  File: skillmeat/web/components/import/import-modal.tsx
  Conditionally render when source.artifact_type === 'composite'. Show parent + child breakdown.")

Task("frontend-developer", "CUX-P3-03: Wire ConflictResolutionDialog for hash mismatch during import.
  File: skillmeat/web/components/deployment/conflict-resolution-dialog.tsx
  Trigger on conflict detection. Wire resolution options to backend API. No stubs.")

Task("frontend-developer", "CUX-P3-04: Create useImportComposite and useMutateComposite mutation hooks.
  File: skillmeat/web/hooks/useImportComposite.ts
  TanStack Query mutations with optimistic updates and rollback on error. Error toasts.")

Task("python-backend-engineer", "CUX-P3-05: Verify import endpoint handles atomic composite + children transaction.
  Confirm single transaction in backend. Partial failure must roll back.")
```

### Batch 2 (After Batch 1)

```
Task("frontend-developer", "CUX-P3-02: Wire CompositePreview into collection add flow.
  Conditional on source type. Consistent with marketplace flow from CUX-P3-01.")

Task("ui-engineer-enhanced", "CUX-P3-06: Playwright E2E for marketplace plugin import.
  File: skillmeat/web/tests/e2e/marketplace-composite-import.spec.ts
  Filter -> view -> preview -> confirm -> collection updated.")

Task("frontend-developer", "CUX-P3-07: Playwright E2E for conflict resolution.
  File: skillmeat/web/tests/e2e/conflict-resolution.spec.ts
  Detect conflict -> show dialog -> resolve -> import succeeds.")
```

---

## Known Gotchas

- Phase 1 (type system, CRUD API) and Phase 2 (marketplace discovery) must be complete.
- `CompositePreview` and `ConflictResolutionDialog` are v1 components -- verify they exist before wiring.
- Use `source.artifact_type === 'composite'` for conditional rendering.
- Ensure atomic artifact imports remain unchanged (backward compatibility).
- Dialogs must trap focus, announce completion, and support keyboard navigation (a11y).
