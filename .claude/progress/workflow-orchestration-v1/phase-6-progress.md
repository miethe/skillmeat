---
type: progress
prd: "workflow-orchestration-v1"
phase: 6
title: "Frontend -- Execution Dashboard"
status: "planning"
started: null
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 10
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: []
tasks:
  - id: "FE-6.1"
    description: "StageTimeline component (vertical timeline with selectable status nodes)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-5.11"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-6.2"
    description: "ExecutionHeader component (workflow name, run ID, status badge, control buttons)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.11"]
    estimated_effort: "1 pt"
    priority: "high"
  - id: "FE-6.3"
    description: "ExecutionProgress component (progress bar, N of M stages complete)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-6.2"]
    estimated_effort: "1 pt"
    priority: "medium"
  - id: "FE-6.4"
    description: "ExecutionDetail right panel (stage detail, agent info, timing, context consumed)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-6.1"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-6.5"
    description: "LogViewer component (monospace, auto-scroll, error highlights, role=log)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-6.4"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "FE-6.6"
    description: "Execution Dashboard page: header, progress, split layout (timeline + detail)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-6.1", "FE-6.2", "FE-6.3", "FE-6.4", "FE-6.5", "FE-5.3"]
    estimated_effort: "3 pts"
    priority: "critical"
  - id: "FE-6.7"
    description: "SSE integration: useExecutionStream updates timeline and logs in real-time"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-6.6", "API-3.13"]
    estimated_effort: "2 pts"
    priority: "critical"
  - id: "FE-6.8"
    description: "Execution List pages: all executions and per-workflow filtered list"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-5.3"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "FE-6.9"
    description: "Optimistic updates for pause/resume/cancel controls"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-6.6"]
    estimated_effort: "1 pt"
    priority: "medium"
  - id: "TEST-6.10"
    description: "Component tests: timeline, log viewer, SSE integration, execution controls"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-6.9"]
    estimated_effort: "2 pts"
    priority: "high"
parallelization:
  batch_1: ["FE-6.1", "FE-6.2", "FE-6.8"]
  batch_2: ["FE-6.3", "FE-6.4"]
  batch_3: ["FE-6.5"]
  batch_4: ["FE-6.6"]
  batch_5: ["FE-6.7", "FE-6.9"]
  batch_6: ["TEST-6.10"]
  critical_path: ["FE-6.1", "FE-6.4", "FE-6.5", "FE-6.6", "FE-6.7", "TEST-6.10"]
  estimated_total_time: "7-10 days"
blockers: []
success_criteria:
  - { id: "SC-6.1", description: "Dashboard renders with split layout (timeline + detail)", status: "pending" }
  - { id: "SC-6.2", description: "SSE events update dashboard in real-time", status: "pending" }
  - { id: "SC-6.3", description: "Log viewer auto-scrolls and highlights errors", status: "pending" }
  - { id: "SC-6.4", description: "Controls work with optimistic updates", status: "pending" }
  - { id: "SC-6.5", description: "Mobile responsive (stacked layout)", status: "pending" }
  - { id: "SC-6.6", description: "Component test coverage >80%", status: "pending" }
files_modified:
  - "skillmeat/web/components/workflow/stage-timeline.tsx"
  - "skillmeat/web/components/workflow/execution-header.tsx"
  - "skillmeat/web/components/workflow/execution-progress.tsx"
  - "skillmeat/web/components/workflow/execution-detail.tsx"
  - "skillmeat/web/components/workflow/log-viewer.tsx"
  - "skillmeat/web/app/workflows/[id]/executions/[runId]/page.tsx"
  - "skillmeat/web/app/workflows/executions/page.tsx"
  - "skillmeat/web/app/workflows/[id]/executions/page.tsx"
---

# workflow-orchestration-v1 - Phase 6: Frontend -- Execution Dashboard

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

---

## Objective

Build the Execution Dashboard with real-time SSE updates, vertical stage timeline, log viewer, and execution controls (pause/resume/cancel).

---

## Implementation Notes

### SSE with Polling Fallback
- Primary: EventSource connection to GET /workflows/{id}/executions/{runId}/stream
- Fallback: 30s polling of GET /workflow-executions/{runId}
- Auto-reconnect with exponential backoff
