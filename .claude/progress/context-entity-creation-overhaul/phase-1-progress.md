---
type: progress
schema_version: 2
doc_type: progress
prd: context-entity-creation-overhaul
feature_slug: context-entity-creation-overhaul
prd_ref: docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md
plan_ref: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md
phase: 1
title: Entity Type Configuration Backend
status: in_progress
started: '2026-02-28'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 1
blocked_tasks: 0
at_risk_tasks: 0
owners:
- data-layer-expert
- python-backend-engineer
contributors: []
tasks:
- id: CECO-1.1
  description: Add EntityTypeConfig SQLAlchemy model, Alembic migration creating entity_type_configs
    table, and idempotent seeding logic for 5 built-in rows from platform_defaults.py
    and context_entity.py
  status: in_progress
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 3 pts
  priority: critical
- id: CECO-1.2
  description: Refactor validate_context_entity() to load type config from DB with
    60s in-memory TTL; preserve hardcoded dispatch map as fallback when entity_type_config_enabled=false
    or DB unavailable
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CECO-1.1
  estimated_effort: 3 pts
  priority: critical
- id: CECO-1.3
  description: Add GET /api/v1/settings/entity-type-configs returning all EntityTypeConfig
    rows as DTOs with EntityTypeConfigResponse Pydantic schema; register sub-route
    in settings.py
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CECO-1.1
  estimated_effort: 2 pts
  priority: high
- id: CECO-1.4
  description: Update POST /context-entities and PUT /context-entities/{id} validation
    error responses to include field and hint keys in 400 detail payload
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CECO-1.2
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - CECO-1.1
  batch_2:
  - CECO-1.2
  - CECO-1.3
  batch_3:
  - CECO-1.4
  critical_path:
  - CECO-1.1
  - CECO-1.2
  - CECO-1.4
  estimated_total_time: 5-7 days
blockers: []
success_criteria:
- id: SC-1.1
  description: entity_type_configs table exists in DB after migration
  status: pending
- id: SC-1.2
  description: 5 built-in type rows seeded; seeding is idempotent (run twice → still
    5 rows)
  status: pending
- id: SC-1.3
  description: Existing Artifact rows with context entity types survive migration
    unchanged
  status: pending
- id: SC-1.4
  description: validate_context_entity() uses DB config when flag enabled; hardcoded
    dispatch map when disabled
  status: pending
- id: SC-1.5
  description: GET /settings/entity-type-configs returns 200 with all 5 configs
  status: pending
- id: SC-1.6
  description: 400 errors from POST /context-entities include field + hint keys
  status: pending
- id: SC-1.7
  description: 'Unit tests: seeding idempotency, cache TTL, fallback path, error hint
    shapes'
  status: pending
files_modified:
- skillmeat/cache/models.py
- skillmeat/cache/migrations/versions/
- skillmeat/core/validators/context_entity.py
- skillmeat/api/routers/settings.py
- skillmeat/api/schemas/context_entity.py
progress: 0
updated: '2026-02-28'
---

# Context Entity Creation Overhaul - Phase 1: Entity Type Configuration Backend

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/context-entity-creation-overhaul/phase-1-progress.md \
  -t CECO-1.1 -s completed
```

---

## Objective

Migrate the 5 hardcoded entity type definitions into a DB-backed `EntityTypeConfig` table. The validator reads from DB with in-memory cache and a hardcoded fallback behind a feature flag. A single read-only API endpoint exposes configs to the frontend.

---

## Orchestration Quick Reference

```python
# Batch 1 — standalone
Task("data-layer-expert",
     "Implement CECO-1.1: EntityTypeConfig DB model + Alembic migration.\n"
     "File: skillmeat/cache/models.py\n"
     "File: skillmeat/cache/migrations/versions/YYYYMMDD_HHMM_add_entity_type_configs.py\n"
     "Add EntityTypeConfig SQLAlchemy model with columns: slug, display_name, path_prefix,\n"
     "required_frontmatter_keys (JSON), content_template (Text), is_builtin (bool).\n"
     "Write additive Alembic migration creating entity_type_configs table.\n"
     "Write idempotent seeding logic populating 5 built-in rows.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 2 — after CECO-1.1
Task("python-backend-engineer",
     "Implement CECO-1.2: DB-backed validator refactor.\n"
     "File: skillmeat/core/validators/context_entity.py\n"
     "Refactor validate_context_entity() to load from DB with 60s TTL.\n"
     "Feature flag: entity_type_config_enabled.\n"
     "Fallback to hardcoded dispatch map when flag off or DB unavailable.\n"
     "Update POST/PUT /context-entities to use refactored validator.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

Task("python-backend-engineer",
     "Implement CECO-1.3: Config list endpoint.\n"
     "File: skillmeat/api/routers/settings.py\n"
     "File: skillmeat/api/schemas/context_entity.py (add EntityTypeConfigResponse)\n"
     "Add GET /api/v1/settings/entity-type-configs returning all EntityTypeConfig rows.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 3 — after CECO-1.2
Task("python-backend-engineer",
     "Implement CECO-1.4: Enhanced error hints.\n"
     "File: skillmeat/api/routers/context_entities.py\n"
     "Update 400 responses for POST/PUT /context-entities to include field + hint keys.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")
```

---

## Implementation Notes

### Architectural Decisions

- Feature flag `entity_type_config_enabled` (default `false`) gates the DB validator switch — existing behavior preserved until Phase 1 fully validated.
- All migrations are additive; no drops on `artifacts` table.
- 60s in-memory TTL on entity type config cache avoids per-request DB hits.

### Known Gotchas

- Seeding logic must be idempotent — use `INSERT OR IGNORE` / upsert pattern, not plain INSERT.
- Alembic migration naming convention: `YYYYMMDD_HHMM_add_entity_type_configs.py`.
- Cache invalidation must happen within 1s of config write (important for Phase 2 CRUD endpoints).

---

## Completion Notes

*(Fill in when phase is complete)*
