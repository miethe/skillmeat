---
schema_version: 2
doc_type: phase_plan
title: 'Phase 3: Import Flow Wiring'
status: inferred_complete
created: 2026-02-19
updated: 2026-02-19
feature_slug: composite-artifact-ux-v2
feature_version: v2
phase: 3
phase_title: Import Flow Wiring
prd_ref: /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
entry_criteria:
- Phase 1 complete (type system, CRUD API)
- Phase 2 complete (marketplace discovery working)
- CompositePreview and ConflictResolutionDialog components exist (from v1)
- useArtifactAssociations hook exists and is functional
exit_criteria:
- CompositePreview renders in import modal for composite sources
- ConflictResolutionDialog appears on hash mismatch
- Import transaction creates composite + children atomically
- Mutation hooks handle errors with rollback
- Core import flow E2E test passes
related_documents:
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
---
# Phase 3: Import Flow Wiring

**Duration**: 2-3 days
**Dependencies**: Phase 1 + Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

## Overview

Connect pre-built components from v1 (`CompositePreview`, `ConflictResolutionDialog`, `useArtifactAssociations`) into the marketplace and collection import flows. This phase is mostly wiring and conditional rendering — no major new components.

## Tasks

### CUX-P3-01: Wire CompositePreview (Marketplace)
Import `CompositePreview` component into the marketplace import dialog and conditionally render when `source.artifact_type === 'composite'`. Component should show parent composite + child breakdown (New/Existing/Conflict buckets).

**AC**: Preview renders for composite sources; shows correct breakdown; user can confirm/cancel
**Est**: 2 pts
**Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P1-01, CUX-P2-06

---

### CUX-P3-02: Wire CompositePreview (Collection)
Import `CompositePreview` into collection `skillmeat add` flow. Same conditional rendering as CUX-P3-01.

**AC**: Preview available in add flow; conditional on source type; consistent with marketplace flow
**Est**: 1 pt
**Subagent**: frontend-developer
**Depends on**: CUX-P3-01

---

### CUX-P3-03: Wire ConflictResolutionDialog
Trigger `ConflictResolutionDialog` when hash mismatch detected during import. Dialog should show version conflict details and resolution options (keep local, use remote, skip). Wire to backend API.

**AC**: Dialog appears on conflict; resolution options work; backend receives selection; no stubs
**Est**: 2 pts
**Subagent**: frontend-developer
**Depends on**: CUX-P1-01

---

### CUX-P3-04: Import Mutation Hooks
Create TanStack Query `useMutation` hooks for composite import. Hooks should handle loading/error/success states and implement optimistic updates with rollback on error.

Hooks needed:
- `useImportComposite`
- `useMutateComposite` (for resolving conflicts)

**AC**: Hooks call correct endpoints; handle all states; optimistic updates roll back on error; errors display as toasts
**Est**: 2 pts
**Subagent**: frontend-developer
**Depends on**: CUX-P1-08

---

### CUX-P3-05: Transaction Verification
Verify import calls correct backend endpoint (atomic transaction for composite + children). No stubs or sequential calls.

**AC**: Import succeeds atomically; partial failure rolls back; single transaction in backend logs
**Est**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-08

---

### CUX-P3-06: Marketplace Import E2E
Playwright E2E test for marketplace plugin import flow: filter → view → preview → confirm → collection updated.

**AC**: Test passes: all steps complete; plugin appears in collection; members imported
**Est**: 2 pts
**Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P3-01

---

### CUX-P3-07: Conflict Resolution E2E
Playwright E2E test for conflict resolution during import: detect conflict → show dialog → resolve → import succeeds.

**AC**: Test passes: conflict detected; resolution works; import completes
**Est**: 2 pts
**Subagent**: frontend-developer
**Depends on**: CUX-P3-03

---

## Quality Gates

- [ ] CompositePreview renders in import modal for composite sources
- [ ] ConflictResolutionDialog appears on hash mismatch
- [ ] Import transaction creates composite + children atomically
- [ ] Mutation hooks handle all states correctly
- [ ] No regression in existing atomic artifact imports
- [ ] Core import flow E2E test passes
- [ ] Conflict resolution E2E test passes

---

## Files Modified/Created

### Frontend
- **Modified**: `skillmeat/web/components/import/import-modal.tsx` (wire CompositePreview)
- **Modified**: `skillmeat/web/components/deployment/conflict-resolution-dialog.tsx` (wire to API)
- **Created**: `skillmeat/web/hooks/useImportComposite.ts`
- **Created**: `skillmeat/web/tests/e2e/marketplace-composite-import.spec.ts`
- **Created**: `skillmeat/web/tests/e2e/conflict-resolution.spec.ts`

---

## Implementation Notes

1. **Conditional Rendering**: Use `source.artifact_type === 'composite'` to decide which import flow to show.
2. **Backward Compatibility**: Ensure atomic artifact imports are unchanged and still work.
3. **Error Handling**: Both components should follow existing error toast patterns.
4. **Loading States**: Show spinners during import; disable buttons appropriately.
5. **Accessibility**: Ensure dialogs trap focus, announce completion, and support keyboard navigation.

---

**Phase 3 Version**: 1.0
**Last Updated**: 2026-02-19
