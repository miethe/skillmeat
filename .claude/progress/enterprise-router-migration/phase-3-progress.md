---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-router-migration
feature_slug: enterprise-router-migration
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-router-migration-v1.md
phase: 3
title: P1/P2 Router Migration - Degraded in Enterprise
status: completed
started: '2026-03-12'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-3.1
  description: 'Migrate tags.py: ~4 READ ops use CollectionManagerDep for tag lookups
    -> TagRepoDep. ~2 WRITE ops: wrap FS write-through in edition check (skip in enterprise).'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 2 pts
  priority: high
- id: TASK-3.2
  description: 'Migrate user_collections.py: ~3 READ ops use managers -> DbUserCollectionRepoDep/DbCollectionArtifactRepoDep.
    ~5 WRITE ops: edition-conditional FS write-through.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 2 pts
  priority: high
- id: TASK-3.3
  description: 'Migrate deployment_sets.py: audit and replace any CollectionManagerDep/ArtifactManagerDep
    reads with DeploymentRepoDep or appropriate repo.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 1 pt
  priority: medium
- id: TASK-3.4
  description: 'Migrate deployments.py: audit and replace any manager reads with DeploymentRepoDep.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 1 pt
  priority: medium
- id: TASK-3.5
  description: 'Clean up health.py: remove CollectionManagerDep from readiness check
    signature (already edition-aware in detailed health). Ensure no FS access in enterprise.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 0.5 pts
  priority: low
- id: TASK-3.6
  description: 'Migrate mcp.py: ~3 READ ops -> ArtifactRepoDep. ~3 WRITE ops: gate
    behind edition check (MCP is FS-native, return 501 for write ops in enterprise).'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 0.5 pts
  priority: low
parallelization:
  batch_1:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  - TASK-3.5
  - TASK-3.6
  critical_path:
  - TASK-3.1
  estimated_total_time: 2 pts (parallel)
blockers: []
success_criteria:
- id: SC-1
  description: Tag CRUD works in enterprise
  status: pending
- id: SC-2
  description: Collection operations work in enterprise
  status: pending
- id: SC-3
  description: Health endpoints dont trigger FS access in enterprise
  status: pending
- id: SC-4
  description: No CollectionManagerDep/ArtifactManagerDep in READ paths
  status: pending
files_modified:
- skillmeat/api/routers/tags.py
- skillmeat/api/routers/user_collections.py
- skillmeat/api/routers/deployment_sets.py
- skillmeat/api/routers/deployments.py
- skillmeat/api/routers/health.py
- skillmeat/api/routers/mcp.py
updated: '2026-03-12'
progress: 100
---

# enterprise-router-migration - Phase 3: P1/P2 Router Migration

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/enterprise-router-migration/phase-3-progress.md --updates "TASK-3.1:completed,TASK-3.2:completed"
```

---

## Objective

Migrate remaining 6 routers that are partially working or degraded in enterprise mode.

---

## Implementation Notes

### Tags Migration

Tags router uses `CollectionManagerDep` for lookups that should go through `TagRepoDep`. Write-through to filesystem should be skipped in enterprise.

### User Collections Migration

Already partially migrated (TASK-4.1/4.2 from a previous effort). Remaining reads use managers. Phase 5 work (TASK-5.1/5.2) covers non-CRUD endpoints.

### MCP Decision

MCP (Model Context Protocol) servers are inherently filesystem-based. In enterprise mode, MCP management should return 501. Enterprise users manage MCP configuration through other means.

### Known Gotchas

- deployment_sets.py and deployments.py may have fewer manager usages than expected - audit first.
- health.py already has edition checks but still injects CollectionManagerDep unnecessarily.
- Some routers may import managers but not use them in READ paths - just clean up imports.
