---
type: progress
schema_version: 2
doc_type: progress
prd: "universal-entity-picker-dialog"
feature_slug: "universal-entity-picker-dialog"
prd_ref: "docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md"
phase: 1
title: "Extract EntityPickerDialog + Context Entity Mini Card"
status: "planning"
started: "2026-03-06"
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: []

tasks:
  - id: "UEPD-1.1"
    description: "Create EntityPickerDialog component with configurable tabs, search, infinite scroll, type filters, selection state"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "4h"
    priority: "high"

  - id: "UEPD-1.2"
    description: "Create EntityPickerTrigger component showing selection summary, badges for multi-select"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "medium"

  - id: "UEPD-1.3"
    description: "Create useEntityPickerArtifacts adapter hook wrapping useInfiniteArtifacts"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"

  - id: "UEPD-2.1"
    description: "Create MiniContextEntityCard component following mini-artifact-card pattern"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "medium"

  - id: "UEPD-2.2"
    description: "Create useEntityPickerContextModules adapter hook wrapping useContextModules"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1h"
    priority: "medium"

parallelization:
  batch_1: ["UEPD-1.1", "UEPD-1.2", "UEPD-1.3", "UEPD-2.1", "UEPD-2.2"]
  critical_path: ["UEPD-1.1"]
  estimated_total_time: "4h"

blockers: []

success_criteria:
  - { id: "SC-1", description: "EntityPickerDialog renders tabs with search and infinite scroll", status: "pending" }
  - { id: "SC-2", description: "MiniContextEntityCard matches visual pattern of MiniArtifactCard", status: "pending" }
  - { id: "SC-3", description: "pnpm type-check passes", status: "pending" }

files_modified:
  - "skillmeat/web/components/shared/entity-picker-dialog.tsx"
  - "skillmeat/web/components/shared/entity-picker-adapter-hooks.ts"
  - "skillmeat/web/components/context/mini-context-entity-card.tsx"
---

# Universal Entity Picker Dialog - Phase 1: Component Extraction

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-1-progress.md \
  -t TASK-ID -s completed
```

Batch update when phase complete:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-1-progress.md \
  --updates "UEPD-1.1:completed,UEPD-1.2:completed,UEPD-1.3:completed,UEPD-2.1:completed,UEPD-2.2:completed"
```

---

## Objective

Extract the rich dialog-based entity browsing patterns from `AddMemberDialog` into a reusable, generic `EntityPickerDialog` component, and create `MiniContextEntityCard` as a compact context entity display. These components form the foundation for integrating browsable entity selection into workflow stage editor and builder sidebar in Phases 3-4.

Both phases run in parallel with no inter-phase dependencies.

---

## Implementation Notes

### Architectural Decisions

- **Generic Configuration via EntityPickerTab[]**: Instead of hardcoding data sources, the dialog accepts a `tabs` prop with configurable `useData` hooks and `renderCard` functions. This keeps the dialog domain-agnostic.
- **No Mutation Coupling**: EntityPickerDialog only concerns itself with selection state; it does not trigger mutations. Parent components handle form state and persistence.
- **Adapter Hooks Pattern**: `useEntityPickerArtifacts` and `useEntityPickerContextModules` wrap existing hooks (`useInfiniteArtifacts`, `useContextModules`) to match the dialog's contract, avoiding code duplication.
- **Mini Card Scale**: `MiniContextEntityCard` derives its visual pattern from `MiniArtifactCard` at `skillmeat/web/components/collection/mini-artifact-card.tsx` to maintain visual consistency across the UI.

### Patterns and Best Practices

- **Infinite Scroll**: Reuse `useIntersectionObserver` hook pattern from `AddMemberDialog` for sentinel-based pagination.
- **Search + Debounce**: Adopt search filtering pattern with 300ms debounce from `AddMemberDialog`.
- **Type Filter Pills**: Extract type filter UI pattern from `AddMemberDialog` for configurable filtering.
- **Radix Primitives**: Use existing `Dialog` + `Command` from Radix UI (already in project) for consistency.
- **Selection State Management**: Single-select closes dialog on item click; multi-select toggles state and requires explicit "Done" confirmation.

### Known Gotchas

- **Tab Content Flash**: Ensure skeleton loaders appear immediately on tab activation before first data fetch completes.
- **Type Filter Visibility**: Only show filter pills if `EntityPickerTab.typeFilters` is configured; no pills = no filtering UI.
- **Inherited Module Handling**: The `useContextModules` hook may return inherited modules—inspect hook return signature before Phase 2 implementation to confirm display expectations.
- **Focus Management**: Dialog must trap focus and return focus to trigger on close for accessibility.

### Development Setup

1. Read source component patterns: `skillmeat/web/components/deployment-sets/add-member-dialog.tsx` (~742 lines)
2. Reference mini card pattern: `skillmeat/web/components/collection/mini-artifact-card.tsx` (~436 lines)
3. Run dev server: `skillmeat web dev`
4. Type-check during development: `pnpm type-check`

---

## Completion Notes

*Fill in when phase is complete:*

- [ ] What was built
- [ ] Key learnings
- [ ] Unexpected challenges
- [ ] Recommendations for next phase
