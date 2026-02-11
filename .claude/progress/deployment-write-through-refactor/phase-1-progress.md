---
phase: 1
title: Backend — Write-Through Deployment Cache (Core Fix)
status: completed
plan_ref: docs/project_plans/implementation_plans/features/deployment-write-through-refactor-v1.md
parallelization:
  batch_1:
  - TASK-1.1
  batch_2:
  - TASK-1.2
  - TASK-1.3
  - TASK-1.4
tasks:
- id: TASK-1.1
  title: Create surgical deployment cache helpers
  status: completed
  assigned_to: python-backend-engineer
  files:
  - skillmeat/api/services/artifact_cache_service.py
- id: TASK-1.2
  title: Fix refresh_single_artifact_cache() to preserve deployments
  status: completed
  assigned_to: python-backend-engineer
  files:
  - skillmeat/api/services/artifact_cache_service.py
- id: TASK-1.3
  title: Wire deploy endpoint to update DB
  status: completed
  assigned_to: python-backend-engineer
  files:
  - skillmeat/api/routers/deployments.py
- id: TASK-1.4
  title: Wire undeploy endpoint to update DB
  status: completed
  assigned_to: python-backend-engineer
  files:
  - skillmeat/api/routers/deployments.py
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-11'
---

## Phase 1: Backend — Write-Through Deployment Cache

### Batch 1: Foundation
- [ ] TASK-1.1: Create `add_deployment_to_cache()` and `remove_deployment_from_cache()` helpers

### Batch 2: Wire-up (parallel after batch 1)
- [ ] TASK-1.2: Remove `deployments_json: None` from refresh_single_artifact_cache()
- [ ] TASK-1.3: Call add_deployment_to_cache() after deploy succeeds
- [ ] TASK-1.4: Call remove_deployment_from_cache() after undeploy succeeds
