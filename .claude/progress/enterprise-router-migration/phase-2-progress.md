---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-router-migration
feature_slug: enterprise-router-migration
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-router-migration-v1.md
phase: 2
title: P0 Router Migration - Broken in Enterprise
status: completed
started: '2026-03-12'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: TASK-2.1
  description: 'Migrate artifacts.py utilities: resolve_collection_name (~L369), _find_artifact_in_collections
    (~L465), build_version_graph (~L679). Replace manager reads with CollectionRepoDep/ArtifactRepoDep/DbArtifactHistoryRepoDep.
    Gate discover() and discover_in_project() with edition check (501).'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 3 pts
  priority: critical
- id: TASK-2.2
  description: 'Migrate marketplace_sources.py: get_collection_artifact_keys helper
    (~L612) uses ArtifactManager.enumerate_all(). Replace with ArtifactRepoDep.list_by_collection()
    or equivalent DB query. Cascades to ~6 endpoints.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 3 pts
  priority: critical
- id: TASK-2.3
  description: 'Migrate match.py: single endpoint (~L65) uses artifact_mgr.match().
    Replace with ArtifactRepoDep.search() or simple DB name-matching query. Add search
    method to repository if missing.'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.2
  estimated_effort: 2 pts
  priority: critical
parallelization:
  batch_1:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.3
  critical_path:
  - TASK-2.1
  estimated_total_time: 3 pts (parallel)
blockers: []
success_criteria:
- id: SC-1
  description: artifacts.py utilities work with repo DI in enterprise
  status: pending
- id: SC-2
  description: Discovery endpoints return 501 in enterprise
  status: pending
- id: SC-3
  description: marketplace_sources helper returns correct data from DB
  status: pending
- id: SC-4
  description: match endpoint returns results from DB in enterprise
  status: pending
files_modified:
- skillmeat/api/routers/artifacts.py
- skillmeat/api/routers/marketplace_sources.py
- skillmeat/api/routers/match.py
- skillmeat/core/interfaces/repositories.py
- skillmeat/core/repositories/local_artifact_repository.py
- skillmeat/cache/enterprise_repositories.py
updated: '2026-03-12'
progress: 100
---

# enterprise-router-migration - Phase 2: P0 Router Migration

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/enterprise-router-migration/phase-2-progress.md --updates "TASK-2.1:completed,TASK-2.2:completed"
```

---

## Objective

Migrate the 3 routers completely broken in enterprise mode to use repository DI for reads.

---

## Implementation Notes

### Migration Pattern

```python
# BEFORE:
collection_mgr.list_collections()  # filesystem read
collection_mgr.load_collection(name)  # filesystem read
artifact = coll.find_artifact(name, type)  # in-memory from filesystem

# AFTER:
collections = collection_repo.list()  # DB query
artifact = artifact_repo.get(type, name)  # DB query
```

### For Discovery (filesystem-only features)

```python
if settings.edition == "enterprise":
    raise HTTPException(501, "Discovery is not available in enterprise edition")
```

### Known Gotchas

- Some write paths in artifacts.py use managers for write-through. Keep those but wrap in edition check.
- marketplace_sources.py helper is used by 6 endpoints - test all after fix.
- match.py may need a new `search()` method on IArtifactRepository - add to both local and enterprise implementations.
