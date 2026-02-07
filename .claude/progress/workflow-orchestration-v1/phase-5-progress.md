---
type: progress
prd: "workflow-orchestration-v1"
phase: 5
title: "Frontend -- Workflow Library & Builder"
status: "planning"
started: null
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 26
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: []
tasks:
  - id: "FE-5.1"
    description: "TypeScript types in types/workflow.ts (Workflow, WorkflowStage, WorkflowExecution, enums)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["API-3.14"]
    estimated_effort: "1 pt"
    priority: "critical"
  - id: "FE-5.2"
    description: "Workflow query hooks (useWorkflows, useWorkflow, useCreateWorkflow, etc.)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.1"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-5.3"
    description: "Execution query hooks (useWorkflowExecutions, useRunWorkflow, useExecutionStream SSE)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.1"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-5.4"
    description: "Hook barrel export in hooks/index.ts"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.2", "FE-5.3"]
    estimated_effort: "0.5 pts"
    priority: "medium"
  - id: "FE-5.5"
    description: "Navigation integration: add Workflows section to sidebar"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.1"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "FE-5.6"
    description: "Route structure: create all Next.js route pages as empty shells (7 routes)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.5"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "FE-5.7"
    description: "SlideOverPanel shared component (reusable right-side panel with animation)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.6"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "FE-5.8"
    description: "ArtifactPicker shared component (searchable popover with type filtering)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.6"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "FE-5.9"
    description: "ContextModulePicker shared component (multi-select popover for context modules)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.6"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "FE-5.10"
    description: "InlineEdit shared component (click-to-edit text field)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.6"]
    estimated_effort: "1 pt"
    priority: "medium"
  - id: "FE-5.11"
    description: "StatusDot shared component (colored status indicator with pulse)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.6"]
    estimated_effort: "0.5 pts"
    priority: "medium"
  - id: "FE-5.12"
    description: "WorkflowCard component (name, stage count, tags, actions)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.2"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "FE-5.13"
    description: "WorkflowListItem component (row layout for list view)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.12"]
    estimated_effort: "1 pt"
    priority: "medium"
  - id: "FE-5.14"
    description: "WorkflowToolbar component (search, filter, sort, view toggle)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.12"]
    estimated_effort: "1 pt"
    priority: "medium"
  - id: "FE-5.15"
    description: "Workflow Library page: PageHeader, toolbar, card grid/list, empty state"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.12", "FE-5.13", "FE-5.14"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-5.16"
    description: "StageCard component (edit + readonly modes, drag handle, badges)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.10"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-5.17"
    description: "StageConnector component (vertical line between stages, hover add button)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.16"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "FE-5.18"
    description: "StageEditor slide-over form (Basic Info, Roles, Context, Advanced sections)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.7", "FE-5.8", "FE-5.9"]
    estimated_effort: "3 pts"
    priority: "critical"
  - id: "FE-5.19"
    description: "Builder state management (useReducer with all BuilderAction types, isDirty tracking)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.16"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-5.20"
    description: "@dnd-kit integration: DndContext, SortableContext, useSortable, keyboard DnD, ARIA"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.16", "FE-5.19"]
    estimated_effort: "3 pts"
    priority: "critical"
  - id: "FE-5.21"
    description: "Builder top bar (back button, editable name, unsaved indicator, save buttons)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.19"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "FE-5.22"
    description: "Builder sidebar (metadata, tags, version, global context, settings)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.9", "FE-5.19"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "FE-5.23"
    description: "Builder page assembly: combine top bar, sidebar, canvas, DnD, add-stage"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.16", "FE-5.17", "FE-5.18", "FE-5.19", "FE-5.20", "FE-5.21", "FE-5.22"]
    estimated_effort: "3 pts"
    priority: "critical"
  - id: "FE-5.24"
    description: "Workflow Detail page: tabs (Stages, Executions, Settings), read-only stage timeline"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.16", "FE-5.2"]
    estimated_effort: "3 pts"
    priority: "high"
  - id: "FE-5.25"
    description: "RunWorkflowDialog: parameter inputs, override sections, Run button"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.3"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "TEST-5.26"
    description: "Component tests: WorkflowCard, StageCard, StageEditor, builder reducer, DnD"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.23"]
    estimated_effort: "3 pts"
    priority: "high"
parallelization:
  batch_1: ["FE-5.1"]
  batch_2: ["FE-5.2", "FE-5.3", "FE-5.5"]
  batch_3: ["FE-5.4", "FE-5.6"]
  batch_4: ["FE-5.7", "FE-5.8", "FE-5.9", "FE-5.10", "FE-5.11", "FE-5.12"]
  batch_5: ["FE-5.13", "FE-5.14", "FE-5.16"]
  batch_6: ["FE-5.15", "FE-5.17", "FE-5.18", "FE-5.19"]
  batch_7: ["FE-5.20", "FE-5.21", "FE-5.22", "FE-5.24", "FE-5.25"]
  batch_8: ["FE-5.23"]
  batch_9: ["TEST-5.26"]
  critical_path: ["FE-5.1", "FE-5.2", "FE-5.12", "FE-5.16", "FE-5.19", "FE-5.20", "FE-5.23", "TEST-5.26"]
  estimated_total_time: "10-14 days"
blockers: []
success_criteria:
  - { id: "SC-5.1", description: "Library page with grid/list toggle, search/filter/sort", status: "pending" }
  - { id: "SC-5.2", description: "Builder creates and saves workflows via API", status: "pending" }
  - { id: "SC-5.3", description: "DnD reorders stages with keyboard support", status: "pending" }
  - { id: "SC-5.4", description: "Stage editor edits all stage properties", status: "pending" }
  - { id: "SC-5.5", description: "Detail page with tabs (Stages, Executions, Settings)", status: "pending" }
  - { id: "SC-5.6", description: "Component test coverage >80%", status: "pending" }
  - { id: "SC-5.7", description: "WCAG 2.1 AA: ARIA roles, focus management, keyboard nav", status: "pending" }
files_modified:
  - "skillmeat/web/types/workflow.ts"
  - "skillmeat/web/hooks/use-workflows.ts"
  - "skillmeat/web/hooks/use-workflow-executions.ts"
  - "skillmeat/web/hooks/index.ts"
  - "skillmeat/web/components/navigation.tsx"
  - "skillmeat/web/components/shared/slide-over-panel.tsx"
  - "skillmeat/web/components/shared/artifact-picker.tsx"
  - "skillmeat/web/components/shared/context-module-picker.tsx"
  - "skillmeat/web/components/shared/inline-edit.tsx"
  - "skillmeat/web/components/shared/status-dot.tsx"
  - "skillmeat/web/components/workflow/workflow-card.tsx"
  - "skillmeat/web/components/workflow/workflow-list-item.tsx"
  - "skillmeat/web/components/workflow/workflow-toolbar.tsx"
  - "skillmeat/web/components/workflow/stage-card.tsx"
  - "skillmeat/web/components/workflow/stage-connector.tsx"
  - "skillmeat/web/components/workflow/stage-editor.tsx"
  - "skillmeat/web/components/workflow/run-workflow-dialog.tsx"
  - "skillmeat/web/app/workflows/page.tsx"
  - "skillmeat/web/app/workflows/new/page.tsx"
  - "skillmeat/web/app/workflows/[id]/page.tsx"
  - "skillmeat/web/app/workflows/[id]/edit/page.tsx"
---

# workflow-orchestration-v1 - Phase 5: Frontend -- Workflow Library & Builder

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

---

## Objective

Build the complete frontend for workflow management: Library page with search/filter, visual Builder with @dnd-kit drag-and-drop stage reordering, and Detail page with execution history tabs.

---

## Implementation Notes

### Design Reference
See `docs/project_plans/design/workflow-orchestration-ui-spec.md` for all wireframes, component specs, interaction patterns, and accessibility requirements.

### DnD Library
@dnd-kit with @dnd-kit/sortable for vertical stage list reordering. No freeform canvas — structured builder pattern.

### Parallel Branch Display
Parallel stages are displayed based on `depends_on` analysis, not manual drag-into-branch. Visual only in v1.
