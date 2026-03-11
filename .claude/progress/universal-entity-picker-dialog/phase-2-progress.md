---
type: progress
schema_version: 2
doc_type: progress
prd: universal-entity-picker-dialog
feature_slug: universal-entity-picker-dialog
prd_ref: docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md
phase: 2
title: Context Entity Mini Card
status: in_progress
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 2
completed_tasks: 0
in_progress_tasks: 2
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: UEPD-2.1
  description: Create MiniContextEntityCard component following mini-artifact-card
    pattern
  status: in_progress
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2h
  priority: medium
- id: UEPD-2.2
  description: Create useEntityPickerContextModules adapter hook wrapping useContextModules
  status: in_progress
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 1h
  priority: medium
parallelization:
  batch_1:
  - UEPD-2.1
  - UEPD-2.2
  critical_path:
  - UEPD-2.1
  estimated_total_time: 2h
blockers: []
success_criteria:
- id: SC-1
  description: MiniContextEntityCard matches visual pattern of MiniArtifactCard
  status: pending
- id: SC-2
  description: pnpm type-check passes
  status: pending
files_modified:
- skillmeat/web/components/context/mini-context-entity-card.tsx
- skillmeat/web/components/shared/entity-picker-adapter-hooks.ts
progress: 0
updated: '2026-03-11'
---

# Universal Entity Picker Dialog - Phase 2: Context Entity Mini Card

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-2-progress.md \
  -t TASK-ID -s completed
```

Batch update when phase complete:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-2-progress.md \
  --updates "UEPD-2.1:completed,UEPD-2.2:completed"
```

---

## Objective

Create `MiniContextEntityCard` as a compact context entity display following the visual pattern of `MiniArtifactCard`, and the `useEntityPickerContextModules` adapter hook wrapping `useContextModules` to match the EntityPickerDialog contract. These components enable context entity selection in the Builder Sidebar integration (Phase 4) and can run in parallel with Phase 1 (no inter-phase dependencies).

---

## Implementation Notes

### Architectural Decisions

- **Mini Card Scale**: `MiniContextEntityCard` derives its visual pattern from `MiniArtifactCard` at `skillmeat/web/components/collection/mini-artifact-card.tsx` to maintain visual consistency across the UI.
- **Adapter Hook Pattern**: `useEntityPickerContextModules` wraps existing `useContextModules` hook to match the dialog's contract, avoiding code duplication and maintaining consistent hook signatures across Phase 1 and Phase 2.
- **Inherited Module Handling**: The `useContextModules` hook may return inherited modules—inspect hook return signature before implementation to confirm display expectations.

### Patterns and Best Practices

- **Reuse Mini Card Pattern**: Study `skillmeat/web/components/collection/mini-artifact-card.tsx` (~436 lines) for layout, icon placement, text truncation, and hover states.
- **Adapter Hook Consistency**: Ensure `useEntityPickerContextModules` has the same return signature as `useEntityPickerArtifacts` (from Phase 1, UEPD-1.3) so both adapt to the same EntityPickerTab contract.
- **Type Safety**: Maintain full TypeScript types matching context entity domain; verify against `useContextModules` hook signature.

### Known Gotchas

- **Inherited Module Handling**: The `useContextModules` hook may return inherited modules—inspect hook return signature before implementation to determine how to display them (e.g., badge, different styling).
- **Visual Consistency**: Ensure card dimensions, padding, and icon sizes match `MiniArtifactCard` exactly for visual consistency in the dialog.

### Development Setup

1. Read mini card reference pattern: `skillmeat/web/components/collection/mini-artifact-card.tsx` (~436 lines)
2. Inspect context modules hook: Find `useContextModules` in codebase to understand return signature
3. Run dev server: `skillmeat web dev`
4. Type-check during development: `pnpm type-check`

---

## Completion Notes

*Fill in when phase is complete:*

- [ ] What was built
- [ ] Key learnings
- [ ] Unexpected challenges
- [ ] Recommendations for next phase
