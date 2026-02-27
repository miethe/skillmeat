---
type: progress
prd: workflow-orchestration-v1
phase: 3
title: Service + API Layer
status: completed
started: null
completed: null
overall_progress: 100
completion_estimate: on-track
total_tasks: 17
completed_tasks: 17
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- backend-architect
contributors: []
tasks:
- id: SVC-3.1
  description: 'WorkflowService CRUD: create (from YAML), get, list, update, delete,
    duplicate'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - REPO-2.4
  - SCHEMA-1.2
  estimated_effort: 3 pts
  priority: critical
- id: SVC-3.2
  description: 'WorkflowService validate: schema + expression + DAG + artifact resolution'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-3.1
  - EXPR-1.6
  - DAG-1.8
  estimated_effort: 2 pts
  priority: critical
- id: SVC-3.3
  description: 'WorkflowService plan: resolve params, build DAG, compute batches,
    resolve artifacts'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-3.2
  - DAG-1.10
  estimated_effort: 2 pts
  priority: critical
- id: SVC-3.4
  description: 'WorkflowExecutionService run: create execution record, snapshot workflow,
    start loop'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.3
  - REPO-2.5
  estimated_effort: 3 pts
  priority: critical
- id: SVC-3.5
  description: 'WorkflowExecutionService stage executor: batch processing, parallel
    stages, retries, timeouts, conditionals, gates'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-3.4
  - EXPR-1.4
  estimated_effort: 5 pts
  priority: critical
- id: SVC-3.6
  description: 'WorkflowExecutionService controls: pause, resume, cancel operations'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.5
  estimated_effort: 2 pts
  priority: high
- id: SVC-3.7
  description: 'WorkflowExecutionService handoff: output validation, serialization,
    summary prompts'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-3.5
  estimated_effort: 2 pts
  priority: high
- id: SVC-3.8
  description: 'WorkflowContextService: integrate ContextModuleService and ContextPackerService
    for per-stage context injection'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.5
  estimated_effort: 2 pts
  priority: high
- id: API-3.9
  description: 'Workflow CRUD router: GET list, POST create, GET/{id}, PUT/{id}, DELETE/{id},
    POST/{id}/duplicate'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.1
  estimated_effort: 3 pts
  priority: critical
- id: API-3.10
  description: 'Workflow operations router: POST/{id}/validate, POST/{id}/plan'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.2
  - SVC-3.3
  estimated_effort: 2 pts
  priority: critical
- id: API-3.11
  description: 'Execution CRUD router: POST run, GET list all, GET by workflow_id,
    GET/{run_id}'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.4
  estimated_effort: 2 pts
  priority: critical
- id: API-3.12
  description: 'Execution controls router: POST pause/resume/cancel, POST gates/{stage_id}/approve|reject'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-3.6
  estimated_effort: 2 pts
  priority: high
- id: API-3.13
  description: 'SSE streaming endpoint: GET /workflows/{id}/executions/{run_id}/stream'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-3.5
  estimated_effort: 2 pts
  priority: high
- id: API-3.14
  description: Pydantic request/response schemas in api/schemas/workflow.py
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-3.9
  estimated_effort: 2 pts
  priority: high
- id: API-3.15
  description: 'OpenAPI documentation: update openapi.json with all endpoints and
    examples'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-3.14
  estimated_effort: 1 pt
  priority: medium
- id: TEST-3.16
  description: API integration tests for all endpoints (CRUD, validate, plan, run,
    controls, SSE)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-3.15
  estimated_effort: 3 pts
  priority: high
- id: TEST-3.17
  description: 'E2E service test: create -> validate -> plan -> run -> complete (mock
    dispatch)'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-3.16
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - SVC-3.1
  batch_2:
  - SVC-3.2
  - SVC-3.3
  - API-3.9
  batch_3:
  - SVC-3.4
  - API-3.10
  batch_4:
  - SVC-3.5
  - API-3.11
  batch_5:
  - SVC-3.6
  - SVC-3.7
  - SVC-3.8
  - API-3.13
  batch_6:
  - API-3.12
  - API-3.14
  batch_7:
  - API-3.15
  batch_8:
  - TEST-3.16
  - TEST-3.17
  critical_path:
  - SVC-3.1
  - SVC-3.3
  - SVC-3.4
  - SVC-3.5
  - API-3.13
  - TEST-3.16
  - TEST-3.17
  estimated_total_time: 7-10 days
blockers: []
success_criteria:
- id: SC-3.1
  description: All services passing unit tests (80%+ coverage)
  status: pending
- id: SC-3.2
  description: All 14+ API endpoints returning correct responses
  status: pending
- id: SC-3.3
  description: SSE streaming delivers real-time events
  status: pending
- id: SC-3.4
  description: Execution engine processes sequential and parallel batches
  status: pending
- id: SC-3.5
  description: Retry, timeout, and error policies working
  status: pending
- id: SC-3.6
  description: Context injection via ContextPackerService working
  status: pending
- id: SC-3.7
  description: E2E lifecycle test passing
  status: pending
files_modified:
- skillmeat/core/workflow/service.py
- skillmeat/core/workflow/execution_service.py
- skillmeat/core/workflow/context_service.py
- skillmeat/api/routers/workflows.py
- skillmeat/api/routers/workflow_executions.py
- skillmeat/api/schemas/workflow.py
- skillmeat/api/openapi.json
- tests/test_workflow_service.py
- tests/test_workflow_api.py
schema_version: 2
doc_type: progress
feature_slug: workflow-orchestration-v1
progress: 100
updated: '2026-02-27'
commit_refs:
- 4b95fa44
---

# workflow-orchestration-v1 - Phase 3: Service + API Layer

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/workflow-orchestration-v1/phase-3-progress.md \
  --updates "SVC-3.1:completed,API-3.9:completed"
```

---

## Objective

Build the complete service layer (WorkflowService, WorkflowExecutionService, WorkflowContextService) and FastAPI routers for 14+ workflow endpoints, including SSE streaming for real-time execution monitoring.

---

## Implementation Notes

### Key Design Decision: StageDispatcher Interface
v1 uses a pluggable `StageDispatcher` interface. Real agent invocation (Claude CLI/SDK) is a separate integration task. The execution engine calls the dispatcher interface, which can be mocked for development.

### SSE Implementation
- Use `sse-starlette` or native `StreamingResponse` with event-stream content type
- Events: `stage_started`, `stage_completed`, `stage_failed`, `log_line`, `execution_completed`
- Auto-reconnect with exponential backoff on client side
- Polling fallback at 30s interval
