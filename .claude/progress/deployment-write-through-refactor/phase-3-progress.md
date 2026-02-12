---
phase: 3
title: Frontend — Revert to /artifacts Endpoint
status: completed
plan_ref: docs/project_plans/implementation_plans/features/deployment-write-through-refactor-v1.md
parallelization:
  batch_1:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
tasks:
- id: TASK-3.1
  title: Revert fetchCollectionEntities endpoint
  status: completed
  assigned_to: ui-engineer-enhanced
  files:
  - skillmeat/web/hooks/useEntityLifecycle.tsx
- id: TASK-3.2
  title: Update frontend DeploymentSummary type
  status: completed
  assigned_to: ui-engineer-enhanced
  files:
  - skillmeat/web/types/artifact.ts
- id: TASK-3.3
  title: Verify query key invalidation
  status: completed
  assigned_to: ui-engineer-enhanced
  files:
  - skillmeat/web/hooks/useDeploy.ts
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-11'
---

## Phase 3: Frontend — Revert to /artifacts Endpoint

### Batch 1: All parallel
- [ ] TASK-3.1: Revert fetchCollectionEntities to use /artifacts
- [ ] TASK-3.2: Update DeploymentSummary TS type with enriched fields
- [ ] TASK-3.3: Verify deploy/undeploy invalidate ['artifacts'] query key
