---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-router-migration
feature_slug: enterprise-router-migration
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-router-migration-v1.md
phase: 1
title: AppState Edition-Awareness
status: completed
started: '2026-03-12'
completed: null
commit_refs:
- e91c3f87
- 0d1e3baf
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 2
completed_tasks: 2
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-1.1
  description: Make AppState managers optional in enterprise mode - wrap collection_manager,
    artifact_manager, sync_manager, context_sync_service init in edition check
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2 pts
  priority: high
- id: TASK-1.2
  description: Guard manager dependency getters - raise HTTPException(501) when manager
    is None in enterprise mode
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
  estimated_effort: 1 pt
  priority: high
parallelization:
  batch_1:
  - TASK-1.1
  batch_2:
  - TASK-1.2
  critical_path:
  - TASK-1.1
  - TASK-1.2
  estimated_total_time: 3 pts
blockers: []
success_criteria:
- id: SC-1
  description: Enterprise container starts without PermissionError
  status: pending
- id: SC-2
  description: app_state.collection_manager is None in enterprise
  status: pending
- id: SC-3
  description: ManagerDep endpoints return 501 in enterprise (not crash)
  status: pending
files_modified:
- skillmeat/api/dependencies.py
progress: 100
updated: '2026-03-12'
---

# enterprise-router-migration - Phase 1: AppState Edition-Awareness

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/enterprise-router-migration/phase-1-progress.md -t TASK-1.1 -s completed
```

---

## Objective

Make filesystem manager initialization conditional on edition. Enterprise mode should not initialize CollectionManager, ArtifactManager, or SyncManager since all data lives in PostgreSQL.

---

## Implementation Notes

### Key File

`skillmeat/api/dependencies.py` - AppState.initialize() (line ~86) and get_*_manager() functions.

### Pattern

```python
# In AppState.initialize():
if settings.edition != "enterprise":
    self.collection_manager = CollectionManager(config=self.config_manager)
    self.artifact_manager = ArtifactManager(collection_mgr=self.collection_manager)
    self.sync_manager = SyncManager(...)
    self.context_sync_service = ContextSyncService(...)

# In get_collection_manager():
def get_collection_manager(...):
    if state.collection_manager is None:
        raise HTTPException(501, "Collection manager not available in enterprise edition")
    return state.collection_manager
```

### Existing Reference

`require_local_edition()` at line ~506 already implements the edition guard pattern - reuse this approach.

### Known Gotchas

- ConfigManager is still needed in enterprise (reads config.toml for settings). Don't skip it.
- CacheManager is needed in both modes (it manages the DB session). Don't skip it.
- Only skip: CollectionManager, ArtifactManager, SyncManager, ContextSyncService.
