---
type: progress
schema_version: 2
doc_type: progress
prd: repo-pattern-gap-closure
feature_slug: repo-pattern-gap-closure
phase: 5
phase_title: Router Migration — High
status: completed
created: 2026-03-04
updated: '2026-03-05'
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md
commit_refs:
- 40a3403a
- 2a2aaaa4
- e4e709d3
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-5.1
  title: Migrate context_entities.py (25+ session calls, 7 endpoints)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 1.5 pts
- id: TASK-5.2
  title: Migrate settings.py entity type config (25+ session calls)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 1.5 pts
- id: TASK-5.3
  title: Migrate marketplace_sources.py (30+ session calls)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 1.5 pts
- id: TASK-5.4
  title: Migrate project_templates.py (20+ session calls, 6 endpoints)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 0.5 pts
parallelization:
  batch_1:
  - TASK-5.1
  - TASK-5.2
  - TASK-5.3
  - TASK-5.4
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 5: Router Migration — High

## Quality Gates
- Zero `session.query` / `get_session` in all 4 migrated routers
- All router test files pass
- OpenAPI spec unchanged
