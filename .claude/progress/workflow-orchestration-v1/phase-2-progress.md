---
type: progress
prd: workflow-orchestration-v1
phase: 2
title: Database + Repository Layer
status: pending
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 8
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- data-layer-expert
- python-backend-engineer
contributors: []
tasks:
- id: DB-2.1
  description: Alembic migration for workflows, workflow_stages, workflow_executions,
    execution_steps tables
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - PREP-0.2
  estimated_effort: 3 pts
  priority: critical
- id: DB-2.2
  description: 'SQLAlchemy ORM models: Workflow, WorkflowStage, WorkflowExecution,
    ExecutionStep'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-2.1
  estimated_effort: 2 pts
  priority: critical
- id: DB-2.3
  description: Indexes and constraints (status+updated_at, workflow_id+status, UNIQUE
    name, CHECK enums)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-2.2
  estimated_effort: 1 pt
  priority: high
- id: REPO-2.4
  description: 'WorkflowRepository: CRUD + list with filters (status, tags, search),
    cursor pagination, find_by_name'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-2.3
  estimated_effort: 3 pts
  priority: critical
- id: REPO-2.5
  description: 'WorkflowExecutionRepository: CRUD + list with filters (workflow_id,
    status, date range), cursor pagination'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-2.3
  estimated_effort: 2 pts
  priority: critical
- id: REPO-2.6
  description: 'ExecutionStepRepository: CRUD + list by execution_id, update status/outputs/logs,
    bulk updates'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DB-2.3
  estimated_effort: 1 pt
  priority: high
- id: REPO-2.7
  description: 'Transaction handling: rollback/error handling, atomic state changes,
    optimistic locking'
  status: pending
  assigned_to:
  - data-layer-expert
  dependencies:
  - REPO-2.4
  estimated_effort: 1 pt
  priority: high
- id: TEST-2.8
  description: 'Repository tests: all CRUD ops, pagination edge cases, filter combinations,
    concurrent access'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-2.7
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - DB-2.1
  batch_2:
  - DB-2.2
  batch_3:
  - DB-2.3
  batch_4:
  - REPO-2.4
  - REPO-2.5
  - REPO-2.6
  batch_5:
  - REPO-2.7
  batch_6:
  - TEST-2.8
  critical_path:
  - DB-2.1
  - DB-2.2
  - DB-2.3
  - REPO-2.4
  - REPO-2.7
  - TEST-2.8
  estimated_total_time: 5-7 days
blockers: []
success_criteria:
- id: SC-2.1
  description: Alembic migration passes forward/backward
  status: pending
- id: SC-2.2
  description: All 4 ORM models with relationships working
  status: pending
- id: SC-2.3
  description: All 3 repositories with CRUD + pagination
  status: pending
- id: SC-2.4
  description: Transaction handling prevents partial writes
  status: pending
- id: SC-2.5
  description: Test coverage >85% on repository layer
  status: pending
files_modified:
- skillmeat/cache/migrations/versions/YYYYMMDD_add_workflow_tables.py
- skillmeat/cache/models.py
- skillmeat/cache/workflow_repositories.py
- tests/test_workflow_repositories.py
schema_version: 2
doc_type: progress
feature_slug: workflow-orchestration-v1
updated: '2026-02-27'
progress: 75
---

# workflow-orchestration-v1 - Phase 2: Database + Repository Layer

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/workflow-orchestration-v1/phase-2-progress.md \
  --updates "DB-2.1:completed,DB-2.2:completed"
```

---

## Objective

Create the database schema for workflow persistence and execution tracking, implement ORM models, and build repository layer with cursor pagination following existing patterns.

---

## Implementation Notes

### Tables
1. **workflows** - Core workflow definition storage (YAML + decomposed metadata)
2. **workflow_stages** - Per-stage configuration (linked to workflow)
3. **workflow_executions** - Run instances (snapshots workflow version at start)
4. **execution_steps** - Per-stage execution state within a run

### Patterns to Follow
- Reference: `skillmeat/cache/memory_repositories.py` (cursor pagination pattern)
- Reference: `skillmeat/cache/models.py` (ORM model patterns, JSON column handling)
- Pagination: Cursor-based with base64-encoded `{id}:{sort_field_value}`
