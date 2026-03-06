---
type: progress
schema_version: 2
doc_type: progress
prd: "enterprise-db-storage"
feature_slug: "enterprise-db-storage"
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
phase: 1
title: "Enterprise Schema & Database Foundation"
status: "planning"
started: "2026-03-06"
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 12
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["data-layer-expert"]
contributors: ["backend-architect", "python-backend-engineer"]

tasks:
  - id: "ENT-1.1"
    description: "PostgreSQL schema design document: tenant-aware schema DDL for all 4 enterprise tables, indexes, constraints, tenant isolation strategy"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "3h"
    priority: "critical"

  - id: "ENT-1.6"
    description: "Design tenant scoping strategy: WHERE tenant_id = ? filtering pattern, context propagation, RLS migration path"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["ENT-1.1"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ENT-1.2"
    description: "Create enterprise_artifacts table with tenant_id isolation, JSONB tags/custom_fields, composite unique constraint"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.1"]
    estimated_effort: "3h"
    priority: "high"

  - id: "ENT-1.4"
    description: "Create enterprise_collections table with tenant_id index, is_default flag, unique constraint on (tenant_id, name)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.1"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ENT-1.9"
    description: "Database connection factory: env-based PostgreSQL/SQLite selection via DATABASE_URL / SKILLMEAT_DATABASE_URL"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.1"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ENT-1.3"
    description: "Create artifact_versions table with content_hash (SHA256), markdown_payload, commit_sha, FK to enterprise_artifacts"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.2"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ENT-1.5"
    description: "Create enterprise_collection_artifacts junction table with order_index, composite FK, unique(collection_id, artifact_id)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.4", "ENT-1.2"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ENT-1.7"
    description: "Alembic migration: create enterprise schema (all 4 tables, indexes, FK constraints, reversible upgrade/downgrade)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.2", "ENT-1.3", "ENT-1.4", "ENT-1.5"]
    estimated_effort: "4h"
    priority: "high"

  - id: "ENT-1.8"
    description: "Alembic migration: add tenant_id columns to existing shared tables with nullable backfill strategy"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.7"]
    estimated_effort: "3h"
    priority: "high"

  - id: "ENT-1.10"
    description: "Docker-compose PostgreSQL for testing: postgres:15-alpine with auto-migration, healthcheck, CI/CD integration"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["ENT-1.7", "ENT-1.8", "ENT-1.9"]
    estimated_effort: "3h"
    priority: "medium"

  - id: "ENT-1.12"
    description: "Migration rollback testing: upgrade/downgrade idempotency, data preservation, no dangling FKs (tests/integration/test_migrations.py)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.7", "ENT-1.8"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ENT-1.11"
    description: "Schema integration tests: tenant isolation, content_hash deduplication, collection nesting, edge cases (tests/integration/test_enterprise_schema.py)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT-1.10"]
    estimated_effort: "3h"
    priority: "high"

parallelization:
  batch_1: ["ENT-1.1"]
  batch_2: ["ENT-1.2", "ENT-1.4", "ENT-1.6", "ENT-1.9"]
  batch_3: ["ENT-1.3", "ENT-1.5"]
  batch_4: ["ENT-1.7"]
  batch_5: ["ENT-1.8"]
  batch_6: ["ENT-1.10", "ENT-1.12"]
  batch_7: ["ENT-1.11"]
  critical_path: ["ENT-1.1", "ENT-1.2", "ENT-1.3", "ENT-1.7", "ENT-1.8", "ENT-1.10", "ENT-1.11"]
  estimated_total_time: "22h"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "All 12 tasks marked complete"
    status: "pending"
  - id: "SC-2"
    description: "All 4 enterprise tables created with proper indexes and constraints"
    status: "pending"
  - id: "SC-3"
    description: "artifact_versions table with content_hash and markdown_payload columns verified"
    status: "pending"
  - id: "SC-4"
    description: "Alembic migrations created, tested, and fully reversible"
    status: "pending"
  - id: "SC-5"
    description: "Docker-compose PostgreSQL functional and integrated with CI"
    status: "pending"
  - id: "SC-6"
    description: "Integration tests passing: tenant isolation, versioning, constraints"
    status: "pending"
  - id: "SC-7"
    description: "Zero breaking changes to existing SQLite schema"
    status: "pending"
  - id: "SC-8"
    description: "Migration rollback testing passing (upgrade/downgrade leaves clean state)"
    status: "pending"
  - id: "SC-9"
    description: "Schema document and tenant scoping strategy reviewed and approved by backend-architect"
    status: "pending"

files_modified:
  - "skillmeat/cache/migrations/versions/20260306_XXXX_create_enterprise_schema.py"
  - "skillmeat/cache/migrations/versions/20260306_XXXX_add_tenant_isolation.py"
  - "skillmeat/cache/config.py"
  - "docker-compose.test.yml"
  - "tests/integration/test_enterprise_schema.py"
  - "tests/integration/test_migrations.py"
---

# enterprise-db-storage - Phase 1: Enterprise Schema & Database Foundation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Update progress via CLI:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-db-storage/phase-1-progress.md -t ENT-1.1 -s completed

# Batch update:
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/enterprise-db-storage/phase-1-progress.md \
  --updates "ENT-1.1:completed,ENT-1.2:completed"
```

---

## Objective

Establish the PostgreSQL database foundation for the Enterprise Edition storage backend by creating tenant-isolated schema tables, Alembic migrations with rollback support, and environment-based database switching. This phase delivers the schema infrastructure that Phase 2 repositories will build upon.

---

## Orchestration Quick Reference

Execute batches in parallel within each batch; wait for prior batch to complete before starting the next.

### Batch 1 — Schema Design (no dependencies)

```python
Task("data-layer-expert",
     "ENT-1.1: Write PostgreSQL schema design document covering all 4 enterprise tables "
     "(enterprise_artifacts, artifact_versions, enterprise_collections, enterprise_collection_artifacts). "
     "Include column definitions, indexes, FK constraints, tenant_id isolation strategy, and data migration "
     "path from SQLite. Output as a markdown doc reviewed by backend-architect. "
     "Phase plan: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-1-schema.md")
```

### Batch 2 — Core Tables + Factory + Strategy (depends on ENT-1.1)

Run all four in parallel:

```python
Task("data-layer-expert",
     "ENT-1.2: Create enterprise_artifacts SQLAlchemy ORM model and Alembic table definition. "
     "Schema: id (UUID PK), tenant_id (UUID NOT NULL), name, type, description, tags (JSONB), "
     "custom_fields (JSONB), source_url, scope, created_at, updated_at. "
     "Indexes on tenant_id and created_at. Unique on (tenant_id, name, type). "
     "File: skillmeat/cache/models/enterprise_artifacts.py. "
     "Follow existing model patterns in skillmeat/cache/models/.")

Task("data-layer-expert",
     "ENT-1.4: Create enterprise_collections SQLAlchemy ORM model and Alembic table definition. "
     "Schema: id (UUID PK), tenant_id (UUID NOT NULL), name, description, is_default (bool), "
     "created_at, updated_at, created_by. Unique on (tenant_id, name). Index on tenant_id. "
     "File: skillmeat/cache/models/enterprise_collections.py.")

Task("data-layer-expert",
     "ENT-1.9: Implement database connection factory in skillmeat/cache/config.py (or db_factory.py). "
     "get_engine() checks SKILLMEAT_DATABASE_URL then DATABASE_URL for PostgreSQL; falls back to SQLite. "
     "is_enterprise_mode() helper. Connection pooling (pool_size, max_overflow, pool_recycle). "
     "Startup log: 'Using SQLite' or 'Using PostgreSQL at <host>'. "
     "All existing code paths must use get_engine() instead of hardcoded db paths.")

Task("backend-architect",
     "ENT-1.6: Write tenant scoping strategy document. "
     "Cover: WHERE tenant_id = ? filtering pattern, RequestContext threading (API -> repository), "
     "repository enforcement, correct vs incorrect query examples, multi-tenant test scenarios, "
     "future RLS migration path. Embed summary as comments in ENT-1.7 migration. "
     "Output as a markdown doc (e.g., docs/architecture/tenant-scoping-strategy.md).")
```

### Batch 3 — Dependent Tables (depends on ENT-1.2, ENT-1.4)

Run both in parallel:

```python
Task("data-layer-expert",
     "ENT-1.3: Create artifact_versions SQLAlchemy ORM model. "
     "Schema: id (UUID PK), artifact_id (FK -> enterprise_artifacts.id), tenant_id, "
     "content_hash (VARCHAR 64, SHA256), markdown_payload (TEXT), version_label, commit_sha, "
     "created_at, created_by. Indexes on (artifact_id, created_at) and content_hash. "
     "File: skillmeat/cache/models/artifact_versions.py.")

Task("data-layer-expert",
     "ENT-1.5: Create enterprise_collection_artifacts junction ORM model. "
     "Schema: id (UUID PK), collection_id (FK -> enterprise_collections.id), "
     "artifact_id (FK -> enterprise_artifacts.id), tenant_id, order_index (INT), added_at. "
     "Unique on (collection_id, artifact_id). Index on (collection_id, tenant_id). "
     "File: skillmeat/cache/models/enterprise_collection_artifacts.py.")
```

### Batch 4 — Schema Creation Migration (depends on ENT-1.2, ENT-1.3, ENT-1.4, ENT-1.5)

```python
Task("data-layer-expert",
     "ENT-1.7: Write Alembic migration for enterprise schema creation. "
     "File: skillmeat/cache/migrations/versions/20260306_XXXX_create_enterprise_schema.py. "
     "Creates all 4 tables with IF NOT EXISTS guards (idempotent). "
     "Includes all indexes (idx_<table>_<column> naming), FK constraints with ON DELETE CASCADE. "
     "upgrade() and downgrade() both fully implemented (reverse dependency order for downgrade). "
     "Embed tenant scoping strategy comments from ENT-1.6. "
     "Test with: alembic upgrade head && alembic downgrade -1 && alembic upgrade head.")
```

### Batch 5 — Tenant Columns Migration (depends on ENT-1.7)

```python
Task("data-layer-expert",
     "ENT-1.8: Write Alembic migration to add tenant_id to existing shared tables. "
     "File: skillmeat/cache/migrations/versions/20260306_XXXX_add_tenant_isolation.py. "
     "Add tenant_id as nullable VARCHAR(36) to shared tables (preserves SQLite compatibility). "
     "Include data backfill strategy (UPDATE ... SET tenant_id = DEFAULT_TENANT_ID WHERE tenant_id IS NULL). "
     "Downgrade removes tenant_id columns cleanly. No data loss on downgrade.")
```

### Batch 6 — Docker Compose + Rollback Tests (depends on ENT-1.7, ENT-1.8, ENT-1.9)

Run both in parallel:

```python
Task("backend-architect",
     "ENT-1.10: Create docker-compose.test.yml with postgres:15-alpine. "
     "Services: postgres (healthcheck: pg_isready), migrate (alembic upgrade head on startup). "
     "Environment: DATABASE_URL=postgresql://skillmeat:skillmeat-dev@postgres/skillmeat_test. "
     "Ports: 5432:8432. Teardown removes data between runs (-v flag). "
     "Document usage in README.md. Verify it works on macOS/Linux.")

Task("data-layer-expert",
     "ENT-1.12: Write migration rollback test suite at tests/integration/test_migrations.py. "
     "Cover: upgrade->downgrade idempotency, data preservation through migration cycles, "
     "FK constraint integrity after rollback, index consistency. "
     "All ENT-1.7 and ENT-1.8 migrations must survive alembic upgrade head; alembic downgrade -1; alembic upgrade head. "
     "Run against docker-compose PostgreSQL (DATABASE_URL env var).")
```

### Batch 7 — Integration Tests (depends on ENT-1.10)

```python
Task("data-layer-expert",
     "ENT-1.11: Write schema integration tests at tests/integration/test_enterprise_schema.py. "
     "Cover: tenant isolation (tenant B cannot see tenant A data), artifact_versions content_hash "
     "deduplication, collection_artifacts linking, constraint enforcement (unique/FK violations), "
     "large collections (1000+ artifacts), concurrent version creation. "
     "Use pytest fixtures seeding the docker-compose PostgreSQL instance. "
     "All tests must pass with READ_COMMITTED isolation level. "
     "Reference: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-1-schema.md")
```

---

## Implementation Notes

### Architectural Decisions

- Enterprise tables are PostgreSQL-only (new tables); shared tables get nullable tenant_id columns for SQLite compatibility (ENT-1.8).
- JSONB for tags and custom_fields avoids schema migrations for MVP-phase flexibility (per ENT-1.2 design).
- Application-enforced tenant filtering (not PostgreSQL RLS) for this phase — documented in ENT-1.6 with RLS migration path.
- Connection factory in `skillmeat/cache/config.py` is the single seam for database backend switching.

### Known Gotchas

- Alembic `op.create_unique_constraint()` fails on SQLite after table creation — use inline `sa.UniqueConstraint()` inside `op.create_table()` (see MEMORY.md: "Alembic Migration Table Existence Checks").
- `op.get_bind()` must be used inside migration functions to get the live connection (no separate session).
- `sqlalchemy.inspect()` pattern needed before `op.create_table()` for idempotency (see MEMORY.md).
- SQLite does not support `PRAGMA foreign_keys` by default — integration tests must use `@event.listens_for(engine, "connect")` to enable FK enforcement.

### Development Setup

```bash
# Start PostgreSQL for local testing
docker-compose -f docker-compose.test.yml up -d

# Run enterprise schema migrations
DATABASE_URL=postgresql://skillmeat:skillmeat-dev@localhost:8432/skillmeat_test alembic upgrade head

# Run integration tests
DATABASE_URL=postgresql://skillmeat:skillmeat-dev@localhost:8432/skillmeat_test pytest tests/integration/

# Tear down
docker-compose -f docker-compose.test.yml down -v
```

---

## Completion Notes

_Fill in when phase is complete._
