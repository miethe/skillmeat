---
type: progress
schema_version: 2
doc_type: progress
prd: db-user-collection-repository
feature_slug: db-user-collection-repository
phase: 4
phase_title: Router Migration — Core CRUD
status: in_progress
created: 2026-03-05
updated: '2026-03-05'
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/refactors/db-user-collection-repository-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-4.1
  title: Migrate helper functions (collection_to_response, ensure_default, sentinel)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.4
  estimate: 1.5 pts
- id: TASK-4.2
  title: Migrate list/create/get/update/delete collection endpoints
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.1
  estimate: 2.5 pts
- id: TASK-4.3
  title: Remove direct session imports from migrated paths
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-4.2
  estimate: 1 pt
parallelization:
  batch_1:
  - TASK-4.1
  batch_2:
  - TASK-4.2
  batch_3:
  - TASK-4.3
total_tasks: 3
completed_tasks: 1
in_progress_tasks: 1
blocked_tasks: 0
progress: 33
---

# Phase 4: Router Migration — Core CRUD

## Quality Gates
- `grep -n "session.query\|session.add\|session.commit\|get_session\|DbSessionDep" skillmeat/api/routers/user_collections.py` returns only comment references for CRUD endpoints
- All CRUD endpoint tests pass
- OpenAPI spec unchanged
- 100% of migrated endpoints use only DI repo aliases

## Quick Reference

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/db-user-collection-repository/phase-4-progress.md \
  --updates "TASK-4.1:completed,TASK-4.2:completed,TASK-4.3:completed"
```
