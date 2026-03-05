---
type: progress
schema_version: 2
doc_type: progress
prd: repo-pattern-gap-closure
feature_slug: repo-pattern-gap-closure
phase: 6
phase_title: Router Migration — Medium
status: pending
created: 2026-03-04
updated: '2026-03-04'
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-6.1
  title: Migrate idp_integration.py (5 session calls)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 0.5 pts
- id: TASK-6.2
  title: Migrate marketplace.py (4 session calls)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 0.5 pts
- id: TASK-6.3
  title: Migrate deployment_sets.py + deployment_profiles.py
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 1 pt
- id: TASK-6.4
  title: Fix remaining concrete repo imports in all routers
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 1 pt
parallelization:
  batch_1:
  - TASK-6.1
  - TASK-6.2
  - TASK-6.3
  - TASK-6.4
---

# Phase 6: Router Migration — Medium

## Quality Gates
- Zero concrete repository class imports in any router file
- Zero `get_session()` / `session.query()` in any router file
- All tests pass
