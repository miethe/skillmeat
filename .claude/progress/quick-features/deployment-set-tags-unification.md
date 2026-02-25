---
feature: deployment-set-tags-unification
status: completed
created: 2026-02-25
branch: feat/deployment-sets
scope: cross-cutting (backend + frontend)
estimated_files: 10
---

# Deployment Set Tags Unification

## Goal
Refactor deployment sets to use the shared `tags` table (relational) instead of a denormalized `tags_json` column, enabling unified tag management across artifacts and deployment sets.

## Tasks

### Batch 1: Backend Model + Migration
- [x] TASK-1.1: Add `DeploymentSetTag` junction table to `cache/models.py`
- [x] TASK-1.2: Update `Tag` model with `deployment_sets` relationship
- [x] TASK-1.3: Update `DeploymentSet` model: add `tags` relationship, keep `tags_json` temporarily
- [x] TASK-1.4: Create Alembic migration (create junction table, migrate data, drop `tags_json`)

### Batch 2: Backend Repository + Router
- [x] TASK-2.1: Update `DeploymentSetRepository` tag operations (create, update, list, count)
- [x] TASK-2.2: Update `deployment_sets.py` router (`_ds_to_response`, create/update handlers)
- [x] TASK-2.3: Update `TagResponse` schema to include `deployment_set_count`
- [x] TASK-2.4: Update `TagService.list_tags` to include deployment set counts

### Batch 3: Frontend
- [ ] TASK-3.1: Update frontend components to use tags API for tag selection
- [ ] TASK-3.2: Update frontend types if needed

### Quality Gates
- [ ] Backend tests pass
- [ ] Frontend type-check passes
- [ ] Frontend lint passes
