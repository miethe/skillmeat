---
type: progress
schema_version: 2
doc_type: progress
prd: "universal-entity-picker-dialog"
feature_slug: "universal-entity-picker-dialog"
prd_ref: "docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md"
phase: 2
title: "Integrate into Workflow Stage Editor + Builder Sidebar"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: []

tasks:
  - id: "UEPD-3.1"
    description: "Replace Primary Agent ArtifactPicker with EntityPickerDialog (single-select, agent type)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UEPD-1.1", "UEPD-1.2", "UEPD-1.3"]
    estimated_effort: "2h"
    priority: "high"

  - id: "UEPD-3.2"
    description: "Replace Support Tools ArtifactPicker with EntityPickerDialog (multi-select, skill/command/mcp)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UEPD-1.1", "UEPD-1.2", "UEPD-1.3"]
    estimated_effort: "2h"
    priority: "high"

  - id: "UEPD-4.1"
    description: "Replace Global Modules ContextModulePicker with EntityPickerDialog (multi-select, context entities)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UEPD-1.1", "UEPD-1.2", "UEPD-2.1", "UEPD-2.2"]
    estimated_effort: "2h"
    priority: "high"

parallelization:
  batch_1: ["UEPD-3.1", "UEPD-3.2", "UEPD-4.1"]
  critical_path: ["UEPD-3.1"]
  estimated_total_time: "2h"

blockers: []

success_criteria:
  - { id: "SC-1", description: "Stage editor Primary Agent opens EntityPickerDialog with agent cards", status: "pending" }
  - { id: "SC-2", description: "Stage editor Support Tools opens EntityPickerDialog with tool cards", status: "pending" }
  - { id: "SC-3", description: "Builder sidebar Global Modules opens EntityPickerDialog with context entity cards", status: "pending" }
  - { id: "SC-4", description: "Form state roundtrip works correctly for all three fields", status: "pending" }

files_modified:
  - "skillmeat/web/components/workflow/stage-editor.tsx"
  - "skillmeat/web/components/workflow/builder-sidebar.tsx"
  - "skillmeat/web/__tests__/components/workflow/stage-editor.test.tsx"
  - "skillmeat/web/__tests__/components/workflow/builder-sidebar.test.tsx"
---

# Universal Entity Picker Dialog - Phase 2: Integration into Workflow UI

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
  --updates "UEPD-3.1:completed,UEPD-3.2:completed,UEPD-4.1:completed"
```

---

## Objective

Replace three compact popover pickers in workflow editing UI with the new `EntityPickerDialog` component: Primary Agent in Stage Editor (single-select), Supporting Tools in Stage Editor (multi-select), and Global Modules in Builder Sidebar (multi-select). All three integration points depend on Phase 1 completion and can run in parallel.

---

## Implementation Notes

### Architectural Decisions

- **Form State Preservation**: All form field shapes remain unchanged (`primaryAgentUuid: string`, `toolUuids: string[]`, `contextPolicy.modules: string[]`). EntityPickerDialog is a presentation layer replacement only.
- **Type Filtering**: Use `typeFilter` prop to constrain displayed entities—Primary Agent: `['agent']`, Supporting Tools: `['skill', 'command', 'mcp']`, Global Modules: all context entities.
- **Test Mock Updates**: Existing unit tests mock `ArtifactPicker` and `ContextModulePicker` imports. Phase 2 includes updating mocks to handle new `EntityPickerDialog` imports.

### Patterns and Best Practices

- **Trigger Button Sizing**: Ensure `EntityPickerTrigger` button matches existing form field button height (likely `h-10`) and styling for visual consistency.
- **Adapter Hook Reuse**: Use `useEntityPickerArtifacts` (Phase 1, UEPD-1.3) for Artifacts tabs in UEPD-3.1 and UEPD-3.2; use `useEntityPickerContextModules` (Phase 1, UEPD-2.2) for Context Entities tab in UEPD-4.1.
- **Selection Appearance**: Both single and multi-select should show a checkmark icon on selected cards; multi-select shows count of selected items in the trigger.

### Known Gotchas

- **Stage Editor Unit Tests**: Current mocks likely import `ArtifactPicker` directly. Update mock to allow `EntityPickerDialog` to be mocked or imported successfully.
- **Builder Sidebar Unit Tests**: Similarly, `ContextModulePicker` mock must be updated. If tests stub the component, verify stubbing still works with new props (`tabs`, `mode`, `value`, `onChange`).
- **Form Save/Load Verification**: After integration, test the form state roundtrip: select → save → reload the page → correct selection should be visible in the picker trigger.

### Development Setup

1. Ensure Phase 1 files exist and type-check passes:
   - `skillmeat/web/components/shared/entity-picker-dialog.tsx`
   - `skillmeat/web/components/shared/entity-picker-adapter-hooks.ts`
   - `skillmeat/web/components/context/mini-context-entity-card.tsx`
2. Inspect Stage Editor code at lines ~413-432 to understand existing `ArtifactPicker` usage patterns.
3. Inspect Builder Sidebar code at lines ~426-443 to understand existing `ContextModulePicker` usage patterns.
4. Run dev server and test form interactions: `skillmeat web dev`

---

## Completion Notes

*Fill in when phase is complete:*

- [ ] What was built
- [ ] Key learnings
- [ ] Unexpected challenges
- [ ] Recommendations for next phase
