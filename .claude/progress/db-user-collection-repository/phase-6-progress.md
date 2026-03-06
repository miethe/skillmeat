---
type: progress
schema_version: 2
doc_type: progress
prd: db-user-collection-repository
feature_slug: db-user-collection-repository
phase: 6
phase_title: Residual Router Cleanup
status: completed
created: 2026-03-05
updated: '2026-03-05'
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/refactors/db-user-collection-repository-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- task-completion-validator
contributors: []
tasks:
- id: TASK-6.1
  title: Migrate artifacts.py residual calls (15 session.query calls)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 1.5 pts
- id: TASK-6.2
  title: Migrate artifact_history.py (2 session.query calls)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 0.5 pts
- id: TASK-6.3
  title: Migrate deployment_profiles.py, projects.py, tags.py (4 calls total)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  estimate: 0.5 pts
- id: TASK-6.4
  title: Cross-router validation audit (zero session.query across ALL routers)
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies:
  - TASK-6.1
  - TASK-6.2
  - TASK-6.3
  estimate: 0.5 pts
parallelization:
  batch_1:
  - TASK-6.1
  - TASK-6.2
  - TASK-6.3
  batch_2:
  - TASK-6.4
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

## Phase 6: Residual Router Cleanup

Clean up 21 residual session.query() calls in 5 routers discovered during Phase 7 validation of the parent gap-closure plan. These calls were over-claimed as complete in gap-closure Phases 4-6.

### Residual Call Inventory

| Router | Calls | Domains |
|--------|-------|---------|
| artifacts.py | 15 | Collection, Artifact, CollectionArtifact, DuplicatePair |
| artifact_history.py | 2 | ArtifactVersion, CacheArtifact |
| deployment_profiles.py | 2 | Project |
| projects.py | 1 | Project |
| tags.py | 1 | Collection |

### Notes
- Phase 6 tasks can run in parallel with Phases 4-5 (different routers)
- TASK-6.4 cross-router validation should run after both Phase 5 and TASK-6.1-6.3 complete
- All DI infrastructure already exists from gap-closure plan — work is replacing direct calls with repo methods
