---
type: progress
schema_version: 2
doc_type: progress
prd: repo-pattern-refactor
feature_slug: repo-pattern-refactor
phase: 2
phase_title: Local Repository Implementations
status: in_progress
created: 2026-03-01
updated: '2026-03-04'
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- data-layer-expert
contributors: []
tasks:
- id: TASK-2.1
  title: Implement ProjectPathResolver
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 2 pts
- id: TASK-2.2
  title: Implement LocalArtifactRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimate: 3 pts
- id: TASK-2.3
  title: Implement LocalProjectRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimate: 2 pts
- id: TASK-2.4
  title: Implement LocalCollectionRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimate: 2 pts
- id: TASK-2.5
  title: Implement remaining local repos (Deployment, Tag, Settings)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  estimate: 2 pts
- id: TASK-2.6
  title: Write-through integration tests
  status: in_progress
  assigned_to:
  - data-layer-expert
  dependencies:
  - TASK-2.2
  - TASK-2.3
  - TASK-2.4
  - TASK-2.5
  estimate: 1 pt
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  - TASK-2.3
  - TASK-2.4
  - TASK-2.5
  batch_3:
  - TASK-2.6
total_tasks: 6
completed_tasks: 5
in_progress_tasks: 1
blocked_tasks: 0
progress: 83
---

# Phase 2: Local Repository Implementations — Progress

## Orchestration Quick Reference

```bash
# Batch 1 (sequential — path resolver first)
Task("python-backend-engineer", "Implement ProjectPathResolver in skillmeat/core/path_resolver.py. Consolidate all duplicated path resolution from routers (resolve_project_path, _normalize_artifact_path, _get_possible_artifact_paths). Reference: skillmeat/api/routers/artifacts.py for existing patterns.")

# Batch 2 (parallel — all local repos can be done simultaneously)
Task("python-backend-engineer", "Implement LocalArtifactRepository in skillmeat/cache/repositories/artifact_repository.py. Delegate to ArtifactManager where possible. Must satisfy IArtifactRepository interface. Write-through: FS first, then DB sync via refresh_single_artifact_cache().")
Task("python-backend-engineer", "Implement LocalProjectRepository in skillmeat/cache/repositories/project_repository.py satisfying IProjectRepository.")
Task("python-backend-engineer", "Implement LocalCollectionRepository in skillmeat/cache/repositories/collection_repository.py satisfying ICollectionRepository.")
Task("python-backend-engineer", "Implement LocalDeploymentRepository, LocalTagRepository, LocalSettingsRepository in skillmeat/cache/repositories/. Satisfy respective interfaces.")

# Batch 3 (sequential — needs all repos)
Task("data-layer-expert", "Write integration tests verifying FS+DB state consistency for every mutation type (create, update, delete) across all 6 local repositories.")
```

## Quality Gates

- [ ] All local repos pass integration tests
- [ ] Write-through behavior verified for every mutation type
- [ ] No direct filesystem access outside repository layer
- [ ] ProjectPathResolver replaces all duplicated path helpers

## Notes

_Phase notes will be added during execution._
