---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-db-storage
feature_slug: enterprise-db-storage
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
phase: 8
title: SQLite-PostgreSQL Migration Compatibility
status: completed
started: null
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
request_ref: REQ-20260309-skillmeat-01
owners:
- python-backend-engineer
contributors:
- data-layer-expert
parallelization:
  strategy: batched
  max_concurrent: 3
  batch_1:
  - MIG-8.1
  batch_2:
  - MIG-8.2
  - MIG-8.3
  batch_3:
  - MIG-8.4
  - MIG-8.5
  batch_4:
  - MIG-8.6
tasks:
- id: MIG-8.1
  description: Create shared dialect helper module in migrations package
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1sp
  priority: critical
  files:
  - skillmeat/cache/migrations/dialect_helpers.py
  notes: 'Create a shared helper module with:

    - `is_sqlite() -> bool` — returns True when running against SQLite

    - `is_postgresql() -> bool` — returns True when running against PostgreSQL

    - `create_updated_at_trigger(table_name, column="updated_at")` — creates dialect-appropriate
    trigger

    - `drop_updated_at_trigger(table_name)` — drops trigger (dialect-aware)

    Pattern: Use `op.get_bind().dialect.name` (already used in enterprise migrations).

    For PostgreSQL triggers: CREATE OR REPLACE FUNCTION + CREATE TRIGGER.

    For SQLite triggers: existing BEGIN...END syntax.

    '
- id: MIG-8.2
  description: Add dialect guards to updated_at trigger migrations
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MIG-8.1
  estimated_effort: 2sp
  priority: critical
  files:
  - skillmeat/cache/migrations/versions/001_initial_schema.py
  - skillmeat/cache/migrations/versions/20251212_1600_create_collections_schema.py
  - skillmeat/cache/migrations/versions/20251215_1200_add_project_templates_and_template_entities.py
  notes: 'For each file:

    1. Import dialect helpers

    2. Replace raw SQLite trigger SQL with helper calls

    3. Helper creates PG trigger function + trigger, or SQLite BEGIN...END trigger

    Triggers affected:

    - 001: projects_updated_at, artifacts_updated_at, cache_metadata_updated_at

    - 20251212: collections_updated_at, collection_artifacts_updated_at

    - 20251215: project_templates_updated_at

    '
- id: MIG-8.3
  description: Add dialect guards to FTS5 migrations (skip on PostgreSQL)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MIG-8.1
  estimated_effort: 2sp
  priority: critical
  files:
  - skillmeat/cache/migrations/versions/20260124_1200_add_fts5_catalog_search.py
  - skillmeat/cache/migrations/versions/20260124_1400_update_fts5_with_deep_search.py
  - skillmeat/cache/migrations/versions/20260226_1000_add_similarity_cache_schema.py
  - skillmeat/cache/migrations/versions/20260226_1900_fix_artifact_fts_triggers.py
  notes: 'Strategy: FTS5 is SQLite-only. Skip all FTS5 operations on PostgreSQL.

    PostgreSQL full-text search (tsvector/GIN) would be a separate future feature.

    For each file:

    1. Import `is_sqlite` from dialect_helpers

    2. Wrap FTS5 virtual table creation and trigger creation in `if is_sqlite():`
    guard

    3. Keep the non-FTS parts (regular table columns, indexes) running on all dialects

    4. Downgrade: also guard FTS5 drops with `if is_sqlite():`

    Note: 20260226_1000 also adds regular columns (fingerprint etc.) — those must
    run on both dialects.

    '
- id: MIG-8.4
  description: Add dialect guards to PRAGMA-based migrations
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MIG-8.1
  estimated_effort: 1sp
  priority: high
  files:
  - skillmeat/cache/migrations/versions/20260219_1100_fix_collection_artifacts_pk.py
  - skillmeat/cache/migrations/versions/20260303_1100_add_workflow_to_artifact_type_check.py
  notes: '20260219 (PK rebuild): Uses PRAGMA table_info() and raw SQL table recreation.

    - On PG: Use standard ALTER TABLE ... ADD/DROP CONSTRAINT (PG supports proper
    PK changes)

    - Guard PRAGMA calls with is_sqlite()

    20260303 (CHECK constraint): Uses sqlite_master inspection.

    - On PG: Use information_schema or pg_constraint to check existing constraints

    - Guard sqlite_master queries with is_sqlite()

    '
- id: MIG-8.5
  description: Add integration tests for PostgreSQL migration path
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MIG-8.2
  - MIG-8.3
  - MIG-8.4
  estimated_effort: 2sp
  priority: high
  files:
  - skillmeat/cache/tests/test_pg_migrations.py
  notes: 'Test that all migrations run cleanly against PostgreSQL.

    Mark as @pytest.mark.integration (requires running PG instance).

    Test both upgrade and downgrade paths.

    Verify updated_at triggers fire correctly on PG.

    Verify FTS5 migrations are cleanly skipped on PG.

    '
- id: MIG-8.6
  description: Validate full migration chain on both SQLite and PostgreSQL
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MIG-8.5
  estimated_effort: 1sp
  priority: high
  files: []
  notes: 'Run `alembic upgrade head` against both SQLite and PostgreSQL.

    Verify no errors, all tables created, triggers working.

    Smoke test: insert rows, verify updated_at triggers fire.

    This is a manual validation step, not automated tests.

    '
progress: 100
updated: '2026-03-09'
---

# Phase 8: SQLite-PostgreSQL Migration Compatibility

## Context

All 7+ Alembic migration files use SQLite-specific SQL (triggers with BEGIN...END syntax, FTS5 virtual tables, PRAGMA statements) that fails when running against PostgreSQL. This blocks enterprise deployment which requires PostgreSQL.

**Linked to**: REQ-20260309-skillmeat-01, enterprise-db-storage-v1

## Approach

1. **Shared dialect helper** — centralize `is_sqlite()`/`is_postgresql()` and trigger creation helpers
2. **Updated_at triggers** — use helper to emit dialect-appropriate trigger SQL (PG uses functions, SQLite uses BEGIN...END)
3. **FTS5** — skip entirely on PostgreSQL (future: add tsvector-based search separately)
4. **PRAGMA-based migrations** — guard with `is_sqlite()`, add PG-native equivalents where needed

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Skip FTS5 on PG (don't add tsvector) | FTS is a cache optimization; PG full-text search is a separate feature |
| Shared helper module (not inline) | 9 files need the same pattern; DRY |
| PG trigger functions for updated_at | Standard PG pattern; clean and maintainable |
| Guard PRAGMAs, add PG equivalents | PRAGMAs are SQLite-only; PG has standard SQL alternatives |

## Orchestration Quick Reference

```bash
# Single task update
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-db-storage/phase-8-progress.md -t MIG-8.1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/enterprise-db-storage/phase-8-progress.md \
  --updates "MIG-8.1:completed,MIG-8.2:completed"
```
