---
type: progress
schema_version: 2
doc_type: progress
prd: repo-pattern-gap-closure
feature_slug: repo-pattern-gap-closure
phase: 4
phase_title: "Router Migration \u2014 Critical"
status: in_progress
created: 2026-03-04
updated: '2026-03-04'
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- refactoring-expert
contributors: []
tasks:
- id: TASK-4.1
  title: Migrate user_collections.py (180+ session calls, 16 endpoints)
  status: pending
  assigned_to:
  - refactoring-expert
  dependencies:
  - TASK-3.3
  estimate: 4 pts
- id: TASK-4.2
  title: Migrate groups.py (70+ session calls, 11 endpoints)
  status: pending
  assigned_to:
  - refactoring-expert
  dependencies:
  - TASK-3.3
  estimate: 3 pts
- id: TASK-4.3
  title: Migrate artifacts.py fallbacks (31 session queries)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 3 pts
parallelization:
  batch_1:
  - TASK-4.1
  - TASK-4.2
  - TASK-4.3
---

# Phase 4: Router Migration — Critical

## Quality Gates
- Zero `session.query`/`session.add`/`session.commit`/`get_session` in user_collections.py and groups.py
- Zero `db_session.query`/`tag_db_session`/`skill_uuid_session` in artifacts.py
- Full pytest suite passes after each migration
- OpenAPI spec unchanged
