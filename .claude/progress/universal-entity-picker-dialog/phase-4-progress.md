---
type: progress
schema_version: 2
doc_type: progress
prd: universal-entity-picker-dialog
feature_slug: universal-entity-picker-dialog
prd_ref: docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md
phase: 4
title: Integrate into Workflow Builder Sidebar
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 1
completed_tasks: 1
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: UEPD-4.1
  description: Replace Global Modules ContextModulePicker with EntityPickerDialog
    (multi-select, context entities)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - UEPD-1.1
  - UEPD-1.2
  - UEPD-2.1
  - UEPD-2.2
  estimated_effort: 2h
  priority: high
parallelization:
  batch_1:
  - UEPD-4.1
  critical_path:
  - UEPD-4.1
  estimated_total_time: 2h
blockers: []
success_criteria:
- id: SC-1
  description: Builder sidebar Global Modules opens EntityPickerDialog with context
    entity cards
  status: pending
- id: SC-2
  description: Form state roundtrip works correctly
  status: pending
files_modified:
- skillmeat/web/components/workflow/builder-sidebar.tsx
- skillmeat/web/__tests__/components/workflow/builder-sidebar.test.tsx
progress: 100
updated: '2026-03-11'
---

# Universal Entity Picker Dialog - Phase 4: Integrate into Workflow Builder Sidebar

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-4-progress.md \
  -t TASK-ID -s completed
```

Batch update when phase complete:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-4-progress.md \
  --updates "UEPD-4.1:completed"
```

---

## Objective

Replace ContextModulePicker in Builder Sidebar Global Modules field with EntityPickerDialog (multi-select, context entities displayed as MiniContextEntityCard). This task depends on Phase 1 (EntityPickerDialog) and Phase 2 (MiniContextEntityCard) completion.

---

## Implementation Notes

### Architectural Decisions

- **Form State Preservation**: Form field shape `contextPolicy.modules: string[]` remains unchanged. EntityPickerDialog is a presentation layer replacement only.
- **Context Entity Display**: Uses `useEntityPickerContextModules` adapter hook from Phase 2 to display context modules, with each item rendered as a `MiniContextEntityCard` for visual consistency.
- **Multi-Select**: Dialog remains open until user explicitly clicks "Done" button for multi-selection workflow.

### Patterns and Best Practices

- **Adapter Hook Reuse**: Use `useEntityPickerContextModules` (Phase 2, UEPD-2.2) as the data source for the context entities tab.
- **Mini Card Display**: Each selected or available context module is displayed as a `MiniContextEntityCard` (Phase 2, UEPD-2.1) for visual consistency.
- **Trigger Button Sizing**: Ensure `EntityPickerTrigger` button matches existing form field button height and styling.

### Known Gotchas

- **Builder Sidebar Unit Tests**: Current mocks likely import `ContextModulePicker` directly. Update mock to allow `EntityPickerDialog` to be mocked or imported successfully.
- **Form Save/Load Verification**: After integration, test the form state roundtrip: select → save → reload the page → correct selection should be visible in the picker trigger.

### Development Setup

1. Ensure Phases 1 and 2 files exist and type-check passes:
   - `skillmeat/web/components/shared/entity-picker-dialog.tsx`
   - `skillmeat/web/components/shared/entity-picker-adapter-hooks.ts`
   - `skillmeat/web/components/context/mini-context-entity-card.tsx`
2. Inspect Builder Sidebar code at lines ~426-443 to understand existing `ContextModulePicker` usage patterns.
3. Run dev server and test form interactions: `skillmeat web dev`
4. Type-check frequently: `pnpm type-check`

---

## Completion Notes

*Fill in when phase is complete:*

- [ ] What was built
- [ ] Key learnings
- [ ] Unexpected challenges
- [ ] Recommendations for next phase
