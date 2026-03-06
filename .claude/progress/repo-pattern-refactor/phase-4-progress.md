---
type: progress
schema_version: 2
doc_type: progress
prd: repo-pattern-refactor
feature_slug: repo-pattern-refactor
phase: 4
phase_title: Router Migration
status: completed
created: 2026-03-01
updated: '2026-03-04'
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- refactoring-expert
contributors: []
tasks:
- id: TASK-4.1
  title: Migrate artifacts.py (largest router, 9400+ lines)
  status: completed
  assigned_to:
  - refactoring-expert
  dependencies: []
  estimate: 3 pts
- id: TASK-4.2
  title: Migrate projects.py
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 1 pt
- id: TASK-4.3
  title: Migrate collections + deployments routers
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-4.4
  title: Migrate context + remaining 9 routers
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
parallelization:
  batch_1:
  - TASK-4.1
  - TASK-4.2
  batch_2:
  - TASK-4.3
  - TASK-4.4
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 4: Router Migration — Progress

## Orchestration Quick Reference

```bash
# Batch 1 (parallel — independent routers)
Task("refactoring-expert", "Migrate skillmeat/api/routers/artifacts.py to use repository DI. Replace all direct os/pathlib/filesystem access with injected ArtifactRepoDep. This is the largest router (9400+ lines) — migrate by endpoint group. Run pytest after each group. Must preserve all API contracts unchanged.")
Task("python-backend-engineer", "Migrate skillmeat/api/routers/projects.py to use ProjectRepoDep. Remove all direct os/pathlib imports. Run pytest tests/test_api_projects.py after migration.")

# Batch 2 (parallel — remaining routers)
Task("python-backend-engineer", "Migrate these routers to use repository DI: user_collections.py, deployments.py, deployment_sets.py, deployment_profiles.py. Remove all direct filesystem access. Run pytest after each.")
Task("python-backend-engineer", "Migrate remaining routers: context_entities.py, context_sync.py, marketplace_sources.py, marketplace.py, mcp.py, icon_packs.py, versions.py, artifact_history.py, bundles.py. Run pytest after each.")
```

## Quality Gates

- [ ] `grep -r "import os\|from pathlib\|import sqlite3" skillmeat/api/routers/` returns zero matches
- [ ] Full pytest suite passes
- [ ] All API contracts unchanged (OpenAPI spec identical)

## Notes

_Phase notes will be added during execution._
