---
type: progress
prd: sync-diff-modal-standardization-v1
phase: 4
title: Wire Up Missing Mutations
status: completed
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: TASK-4.1
  description: Implement keepLocalMutation - dismiss drift via local state
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2 pts
  priority: medium
  model: opus
- id: TASK-4.2
  description: Implement batch actions with context-sync endpoints
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 3 pts
  priority: medium
  model: opus
- id: TASK-4.3
  description: Implement push-to-collection mutation with context-sync/pull
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2 pts
  priority: medium
  model: opus
- id: TASK-4.4
  description: Verify all mutations work end-to-end on both pages
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-4.1
  - TASK-4.2
  - TASK-4.3
  estimated_effort: 1 pt
  priority: high
  model: opus
parallelization:
  batch_1:
  - TASK-4.1
  - TASK-4.2
  - TASK-4.3
  batch_2:
  - TASK-4.4
  critical_path:
  - TASK-4.2
  - TASK-4.4
  estimated_total_time: 8 pts
blockers: []
success_criteria:
- id: SC-1
  description: No 'coming soon' or 'not yet implemented' toasts
  status: pending
- id: SC-2
  description: All mutations call correct endpoints
  status: pending
- id: SC-3
  description: Cache invalidation follows data-flow-patterns graph
  status: pending
- id: SC-4
  description: Mutations work on both /manage and /projects pages
  status: pending
files_modified:
- web/components/sync-status/sync-status-tab.tsx
progress: 100
updated: '2026-02-04'
schema_version: 2
doc_type: progress
feature_slug: sync-diff-modal-standardization-v1
---

# sync-diff-modal-standardization-v1 - Phase 4: Wire Up Missing Mutations

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/sync-diff-modal-standardization/phase-4-progress.md -t TASK-4.1 -s completed
```

---

## Objective

Wire up all stubbed/missing sync mutations: keep-local, batch actions, and push-to-collection. All API endpoints already exist.

---

## Implementation Notes

### Cache Invalidation Reference

| Mutation | Must Invalidate |
|----------|----------------|
| Deploy/Undeploy | `['deployments']`, `['artifacts']`, `['projects']` |
| Context sync push/pull | `['context-sync-status']`, `['artifact-files']`, `['context-entities']`, `['deployments']` |

### Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| Push to project | `POST /context-sync/push` | `{ project_path, entity_ids, overwrite }` |
| Pull from project | `POST /context-sync/pull` | `{ project_path, entity_ids }` |
| Sync from upstream | `POST /artifacts/{id}/sync` | Body varies |

### Known Gotchas

- `keepLocalMutation` should NOT call an API -- it's purely local state (dismiss drift)
- Batch actions need to distinguish push vs pull based on comparison scope
- Push-to-collection requires `projectPath` from Phase 2
- Use hooks from `@/hooks`: `usePushContextChanges`, `usePullContextChanges`
- Verify TanStack Query `onSuccess` callbacks invalidate correct keys

---

## Completion Notes

_(fill in when phase is complete)_
