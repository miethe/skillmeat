---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-router-migration
feature_slug: enterprise-router-migration
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-router-migration-v1.md
phase: 4
title: Validation & Cleanup
status: pending
started: '2026-03-12'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 3
completed_tasks: 1
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- refactoring-expert
- documentation-writer
tasks:
- id: TASK-4.1
  description: 'Enterprise smoke test: start enterprise docker-compose, hit all major
    API endpoints. Verify no 400/500 from filesystem errors.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.3
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  - TASK-3.5
  - TASK-3.6
  estimated_effort: 1 pt
  priority: high
- id: TASK-4.2
  description: Clean up unused CollectionManagerDep/ArtifactManagerDep imports from
    migrated routers. Run flake8 to verify.
  status: pending
  assigned_to:
  - refactoring-expert
  dependencies:
  - TASK-4.1
  estimated_effort: 1 pt
  priority: medium
- id: TASK-4.3
  description: Update enterprise_router_miswiring.md gotcha doc to mark issue as resolved.
    Note which routers still use managers for writes.
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - TASK-4.2
  estimated_effort: 1 pt
  priority: low
parallelization:
  batch_1:
  - TASK-4.1
  batch_2:
  - TASK-4.2
  - TASK-4.3
  critical_path:
  - TASK-4.1
  - TASK-4.2
  estimated_total_time: 2 pts
blockers: []
success_criteria:
- id: SC-1
  description: All endpoints return valid responses in enterprise (200/201/204/501)
  status: pending
- id: SC-2
  description: No unused imports (flake8 clean)
  status: pending
- id: SC-3
  description: Gotcha doc updated with resolution
  status: pending
- id: SC-4
  description: Existing pytest suite passes in local mode (no regression)
  status: pending
files_modified:
- .claude/agent-memory/codebase-explorer/enterprise_router_miswiring.md
progress: 33
updated: '2026-03-12'
---

# enterprise-router-migration - Phase 4: Validation & Cleanup

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/enterprise-router-migration/phase-4-progress.md -t TASK-4.1 -s completed
```

---

## Objective

Verify all changes work end-to-end in enterprise mode, clean up unused code, and update documentation.

---

## Implementation Notes

### Smoke Test Checklist

1. `docker compose --profile enterprise up --build`
2. Hit endpoints: GET /health, GET /health/detailed, GET /health/ready
3. GET /api/v1/artifacts - list artifacts
4. GET /api/v1/user-collections - list collections
5. GET /api/v1/tags - list tags
6. POST /api/v1/match - match artifact
7. GET /api/v1/marketplace-sources - list sources
8. Verify no 400/500 errors in container logs

### Cleanup

Run `flake8 skillmeat/api/routers/ --select=F401` to find unused imports.
