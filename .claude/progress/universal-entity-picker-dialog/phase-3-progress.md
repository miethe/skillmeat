---
type: progress
schema_version: 2
doc_type: progress
prd: universal-entity-picker-dialog
feature_slug: universal-entity-picker-dialog
prd_ref: docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md
phase: 3
title: Integrate into Workflow Stage Editor
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 2
completed_tasks: 2
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: UEPD-3.1
  description: Replace Primary Agent ArtifactPicker with EntityPickerDialog (single-select,
    agent type)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - UEPD-1.1
  - UEPD-1.2
  - UEPD-1.3
  estimated_effort: 2h
  priority: high
- id: UEPD-3.2
  description: Replace Support Tools ArtifactPicker with EntityPickerDialog (multi-select,
    skill/command/mcp)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - UEPD-1.1
  - UEPD-1.2
  - UEPD-1.3
  estimated_effort: 2h
  priority: high
parallelization:
  batch_1:
  - UEPD-3.1
  - UEPD-3.2
  critical_path:
  - UEPD-3.1
  estimated_total_time: 2h
blockers: []
success_criteria:
- id: SC-1
  description: Stage editor Primary Agent opens EntityPickerDialog
  status: pending
- id: SC-2
  description: Stage editor Support Tools opens EntityPickerDialog
  status: pending
- id: SC-3
  description: Form state roundtrip works correctly
  status: pending
files_modified:
- skillmeat/web/components/workflow/stage-editor.tsx
- skillmeat/web/__tests__/components/workflow/stage-editor.test.tsx
progress: 100
updated: '2026-03-11'
---

# Universal Entity Picker Dialog - Phase 3: Integrate into Workflow Stage Editor

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-3-progress.md \
  -t TASK-ID -s completed
```

Batch update when phase complete:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-3-progress.md \
  --updates "UEPD-3.1:completed,UEPD-3.2:completed"
```

---

## Objective

Replace two compact ArtifactPicker fields in Stage Editor with EntityPickerDialog: Primary Agent (single-select, agent type only) and Support Tools (multi-select, skill/command/mcp types). Both tasks depend on Phase 1 completion and can run in parallel.

---

## Implementation Notes

### Architectural Decisions

- **Form State Preservation**: Form field shapes remain unchanged (`primaryAgentUuid: string`, `toolUuids: string[]`). EntityPickerDialog is a presentation layer replacement only.
- **Type Filtering**: Primary Agent: `['agent']` type filter; Supporting Tools: `['skill', 'command', 'mcp']` type filter. Note: `'workflow'` type intentionally excluded from Supporting Tools.
- **Test Mock Updates**: Existing unit tests mock `ArtifactPicker` imports. Phase 3 includes updating mocks to handle new `EntityPickerDialog` imports.

### Patterns and Best Practices

- **Trigger Button Sizing**: Ensure `EntityPickerTrigger` button matches existing form field button height (likely `h-10`) and styling for visual consistency.
- **Adapter Hook Reuse**: Use `useEntityPickerArtifacts` (Phase 1, UEPD-1.3) for both UEPD-3.1 and UEPD-3.2, varying only the `typeFilter` prop.
- **Selection Appearance**: Both single and multi-select should show a checkmark icon on selected cards; multi-select shows count of selected items in the trigger.

### Known Gotchas

- **Stage Editor Unit Tests**: Current mocks likely import `ArtifactPicker` directly. Update mock to allow `EntityPickerDialog` to be mocked or imported successfully.
- **Form Save/Load Verification**: After integration, test the form state roundtrip: select → save → reload the page → correct selection should be visible in the picker trigger.
- **Prerequisite**: MiniArtifactCard needs workflow color fix (border-l-cyan-500) before this phase runs, to ensure visual consistency in the dialog.

### Development Setup

1. Ensure Phase 1 files exist and type-check passes:
   - `skillmeat/web/components/shared/entity-picker-dialog.tsx`
   - `skillmeat/web/components/shared/entity-picker-adapter-hooks.ts`
2. Inspect Stage Editor code at lines ~413-432 to understand existing `ArtifactPicker` usage patterns.
3. Run dev server and test form interactions: `skillmeat web dev`
4. Type-check frequently: `pnpm type-check`

---

## Completion Notes

*Fill in when phase is complete:*

- [ ] What was built
- [ ] Key learnings
- [ ] Unexpected challenges
- [ ] Recommendations for next phase
