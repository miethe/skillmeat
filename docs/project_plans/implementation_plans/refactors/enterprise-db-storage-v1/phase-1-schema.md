---
title: "Phase 1: Enterprise Schema & Database Foundation"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-06
updated: 2026-03-06
feature_slug: "enterprise-db-storage"
phase: 1
phase_title: "Enterprise Schema & Database Foundation"
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
entry_criteria:
  - "PRD 1 (Repository Pattern Refactor) >90% complete"
  - "PostgreSQL development/test instance available"
  - "Data-layer-expert and backend-architect allocated"
exit_criteria:
  - "All enterprise schema tables created and migrated"
  - "artifact_versions table with content_hash and markdown_payload"
  - "Tenant isolation via tenant_id columns verified"
  - "Alembic migrations documented"
  - "Zero breaking changes to existing SQLite schema"
  - "Schema integration tests passing with docker-compose PostgreSQL"
---

# Phase 1: Enterprise Schema & Database Foundation

## Overview

Phase 1 establishes the PostgreSQL database foundation for the Enterprise Edition storage backend. This phase creates new enterprise-specific tables, extends existing tables with `tenant_id` columns for multi-tenant isolation, and provides the schema versioning infrastructure via Alembic migrations.

**Duration:** 2-3 weeks | **Effort:** 18-22 story points | **Subagents:** data-layer-expert, backend-architect

**Key Outputs:**
- PostgreSQL schema with enterprise artifacts, collections, versions tables
- Alembic migrations with proper versioning and rollback support
- Environment-based database switching (SQLite local, PostgreSQL enterprise)
- Schema documentation and migration runbooks

---

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| ENT-1.1 | PostgreSQL schema design document | Document tenant-aware schema: artifacts, artifact_versions, collections, collection_artifacts with tenant_id, indexes, constraints | Schema DDL documented, reviewed by backend-architect, ready for code | 3 | data-layer-expert | None |
| ENT-1.2 | Create enterprise_artifacts table | Implement artifacts table: id, tenant_id, name, type, description, tags (JSONB), created_at, updated_at, source_url, scope, custom_fields (JSONB) | Table created with proper indexes (tenant_id, created_at), PK on (tenant_id, id) | 3 | data-layer-expert | ENT-1.1 |
| ENT-1.3 | Create artifact_versions table | Implement versioning: id, artifact_id, tenant_id, content_hash (SHA256), markdown_payload (text), created_at, version_label, commit_sha | Table created with indexes on (artifact_id, created_at), FK to artifacts | 2 | data-layer-expert | ENT-1.2 |
| ENT-1.4 | Create enterprise_collections table | Extend collections: id, tenant_id, name, description, created_at, updated_at, is_default (bool) | Table created with tenant_id index, preserves existing collection structure | 2 | data-layer-expert | ENT-1.1 |
| ENT-1.5 | Create collection_artifacts junction | Map collections to artifacts: id, collection_id, artifact_id, tenant_id, order_index, added_at | Table created with FK constraints, composite index (collection_id, tenant_id) | 2 | data-layer-expert | ENT-1.4, ENT-1.2 |
| ENT-1.6 | Design tenant scoping strategy | Document WHERE tenant_id = ? filtering pattern, context propagation, multi-tenant test scenarios | Strategy doc written, reviewed, embedded in migration comments | 2 | backend-architect | ENT-1.1 |
| ENT-1.7 | Implement Alembic migration: schema creation | Write migration for Phase 1 tables: create_enterprise_schema_<timestamp>.py with upgrade/downgrade | Migration created, includes reversible DDL, version comment matches PR | 4 | data-layer-expert | ENT-1.2, ENT-1.3, ENT-1.4, ENT-1.5 |
| ENT-1.8 | Implement Alembic migration: tenant columns | Create add_tenant_isolation_<timestamp>.py for adding tenant_id to existing tables (preserve SQLite-only structure) | Migration separates enterprise-only from shared tables, includes data backfill strategy | 3 | data-layer-expert | ENT-1.7 |
| ENT-1.9 | Database connection factory | Implement env-based connection logic: use PostgreSQL when DATABASE_URL set, SQLite otherwise | Connection factory in skillmeat/cache/config.py, respects SKILLMEAT_DATABASE_URL or DATABASE_URL env vars | 2 | data-layer-expert | ENT-1.1 |
| ENT-1.10 | Docker-compose PostgreSQL for testing | Create docker-compose.test.yml with PostgreSQL 15, auto-migration on startup, seed data scripts | docker-compose runs `alembic upgrade head`, provides consistent test DB, docs in README | 3 | backend-architect | ENT-1.7, ENT-1.8, ENT-1.9 |
| ENT-1.11 | Schema integration tests | Write tests: verify tenant isolation (queries auto-filtered), artifact_versions content preservation, collection nesting | Tests run against docker-compose PostgreSQL, cover edge cases (empty tenant, large collections) | 3 | data-layer-expert | ENT-1.10 |
| ENT-1.12 | Migration rollback testing | Verify all migrations can safely downgrade, test idempotency (running same migration twice) | Test suite in tests/integration/test_migrations.py, all rollbacks succeed, no data loss | 2 | data-layer-expert | ENT-1.7, ENT-1.8 |

**Total: 31 hours / 18-22 story points**

---

## Detailed Task Descriptions

### ENT-1.1: PostgreSQL Schema Design Document

**Description:**

Document the complete PostgreSQL schema for the enterprise edition. This is the blueprint for all subsequent implementation and serves as the contract between data-layer and repository layers.

**Key Sections:**
1. Table Inventory: List all enterprise tables (artifacts, artifact_versions, collections, collection_artifacts)
2. Column Definitions: Type, nullability, constraints for each column
3. Indexes: Performance-critical indexes (tenant_id, artifact_id, created_at)
4. Constraints: Foreign keys, unique constraints, check constraints
5. Tenant Scoping: How tenant_id is used in all tables
6. Data Migration Path: How existing SQLite data maps to PostgreSQL
7. Rationale: Why each design choice was made

**Acceptance Criteria:**
- Complete DDL for all 4 enterprise tables documented
- Column descriptions include purpose and constraints
- Indexes documented with reason (performance, filtering, uniqueness)
- Foreign key relationships diagrammed
- Tenant isolation strategy documented with query examples
- Approved by backend-architect before code writing begins

**References:**
- PRD 3 schema section
- Existing skillmeat/cache/models/ structure
- Alembic conventions in codebase

---

### ENT-1.2: Create enterprise_artifacts Table

**Description:**

Implement the core enterprise artifacts table. This is the primary storage for all artifact metadata in the PostgreSQL backend.

**Schema:**
```sql
CREATE TABLE enterprise_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- skill, command, agent, etc.
    description TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    custom_fields JSONB DEFAULT '{}'::jsonb,
    source_url VARCHAR(512),
    scope VARCHAR(50) DEFAULT 'user',  -- user or local
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name, type),
    INDEX (tenant_id),
    INDEX (created_at),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

**Acceptance Criteria:**
- Table created with all columns as documented in ENT-1.1
- Composite primary key (tenant_id, name, type) enforces uniqueness per tenant
- Indexes on tenant_id (filtering), created_at (sorting), and (type, tenant_id) for type-based queries
- JSONB columns support tags and custom_fields without schema migrations
- Table creation idempotent (no errors on rerun)
- Schema matches Python models in skillmeat/cache/models/artifacts.py

**Notes:**
- source_url tracks GitHub origin (for sync/upstream updates)
- scope distinguishes user-scoped vs local-scoped artifacts (per ADR-009)
- JSONB tags allow flexible filtering without separate tag tables (for MVP)

---

### ENT-1.3: Create artifact_versions Table

**Description:**

Implement versioning support for artifacts, storing content snapshots and content hashes for deduplication.

**Schema:**
```sql
CREATE TABLE artifact_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    content_hash VARCHAR(64) NOT NULL,  -- SHA256
    markdown_payload TEXT NOT NULL,
    version_label VARCHAR(50),  -- v1.0, v1.1, tag, etc.
    commit_sha VARCHAR(40),  -- GitHub commit reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),  -- user ID or "system"
    FOREIGN KEY (artifact_id) REFERENCES enterprise_artifacts(id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    INDEX (artifact_id, created_at),
    INDEX (content_hash)
);
```

**Acceptance Criteria:**
- Table created with content_hash (SHA256) as primary identifier for deduplication
- markdown_payload stores full Markdown content (no size limit for MVP)
- version_label supports both semantic versioning (v1.2.3) and tags
- commit_sha references upstream GitHub for sync tracking
- Indexes on (artifact_id, created_at) for version history queries
- Indexes on content_hash for deduplication lookups

**Notes:**
- content_hash computed at repository layer (ENT-2.x), not here
- markdown_payload uses TEXT type (unlimited length, but consider BYTEA for compression in future)
- Versioning enables: artifact history, rollback, and CI/CD pin-to-hash

---

### ENT-1.4: Create enterprise_collections Table

**Description:**

Implement collections as named groupings of artifacts with tenant isolation.

**Schema:**
```sql
CREATE TABLE enterprise_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    UNIQUE(tenant_id, name),
    INDEX (tenant_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

**Acceptance Criteria:**
- Table created with tenant_id primary scoping
- is_default flag marks user's personal collection
- Unique constraint on (tenant_id, name) prevents duplicate collection names per tenant
- created_by tracks which user created the collection (for audit/blame)
- No direct artifacts in this table; uses collection_artifacts junction

**Notes:**
- is_default allows CLI to know which collection to default to for `skillmeat deploy`
- created_by is a string (user_id) to avoid circular dependency on users table (user management in PRD 2)

---

### ENT-1.5: Create collection_artifacts Junction

**Description:**

Implement the many-to-many relationship between collections and artifacts with ordering support.

**Schema:**
```sql
CREATE TABLE enterprise_collection_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL,
    artifact_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    order_index INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collection_id, artifact_id),
    FOREIGN KEY (collection_id) REFERENCES enterprise_collections(id),
    FOREIGN KEY (artifact_id) REFERENCES enterprise_artifacts(id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    INDEX (collection_id, tenant_id)
);
```

**Acceptance Criteria:**
- Table created with composite FK to both collections and artifacts
- order_index enables drag-and-drop reordering in UI
- Unique constraint prevents duplicate artifacts in same collection
- Indexes optimized for "list all artifacts in collection" queries
- tenant_id included for query filtering efficiency

**Notes:**
- order_index is a simple integer; UI handles gaps and renumbering
- added_at tracks audit info (when artifact was added to collection)

---

### ENT-1.6: Design Tenant Scoping Strategy

**Description:**

Document the application-enforced multi-tenant filtering strategy. This is critical for security and serves as implementation guidance for Phase 2 repositories.

**Single-Tenant Bootstrap**: In Phases 1-3, all `tenant_id` columns are populated from `DEFAULT_TENANT_ID` — a UUID constant read from the `SKILLMEAT_DEFAULT_TENANT_ID` env var (or a hardcoded fallback in config). The schema is designed for multi-tenancy but operates in single-tenant mode until PRD 2's AuthContext is available. This means Phase 1 can be implemented and tested without PRD 2.

**Key Sections:**
1. Filtering Pattern: WHERE tenant_id = ? in all queries
2. Bootstrap Mode: DEFAULT_TENANT_ID used when AuthContext is absent (Phases 1-3)
3. RequestContext Threading: How tenant_id flows from API → repository methods (Phase 4+, PRD 2)
4. Repository Enforcement: Automatic filtering in all CRUD operations
5. Query Construction: Examples of tenant-safe queries
6. Testing Strategy: How to test multi-tenant isolation (negative tests)
7. Future RLS: Migration path if we adopt PostgreSQL RLS later

**Acceptance Criteria:**
- Strategy document written and approved by backend-architect
- `DEFAULT_TENANT_ID` constant defined in config, readable from `SKILLMEAT_DEFAULT_TENANT_ID` env var
- `DEFAULT_TENANT_ID` populates all `tenant_id` columns when AuthContext is absent
- Includes code examples for correct and incorrect query patterns
- Documents why application-enforced (vs database RLS) for this phase
- Includes migration path to RLS for future phases
- Documents upgrade path: single-tenant (DEFAULT_TENANT_ID) → multi-tenant (AuthContext.tenant_id) when PRD 2 lands
- Embedded as comments in ENT-1.7 migration

**Example Query Pattern:**
```python
# CORRECT: Automatic tenant filtering
def get_artifact(artifact_id: str, ctx: RequestContext) -> ArtifactDTO:
    query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.tenant_id == ctx.tenant_id  # Always included
        )
    )
    return query.first()

# INCORRECT: Missing tenant check
def get_artifact_WRONG(artifact_id: str) -> ArtifactDTO:
    query = select(Artifact).where(Artifact.id == artifact_id)  # SECURITY BUG
    return query.first()
```

---

### ENT-1.7: Implement Alembic Migration: Schema Creation

**Description:**

Write the Alembic migration that creates all enterprise schema tables. This is the production deployment mechanism.

**File:** `skillmeat/cache/migrations/versions/20260306_XXXX_create_enterprise_schema.py`

**Structure:**
```python
"""Create enterprise schema tables.

Revision ID: 20260306xxxx
Revises: <previous-migration>
Create Date: 2026-03-06 12:00:00.000000

This migration creates the enterprise-edition PostgreSQL schema:
- enterprise_artifacts table with tenant_id isolation
- artifact_versions table with content_hash deduplication
- enterprise_collections and enterprise_collection_artifacts for grouping

All tables include tenant_id for multi-tenant filtering and proper
foreign key constraints for referential integrity.

This migration is idempotent and safe to rerun; it checks for
table existence before creating.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create enterprise_artifacts table
    # Create artifact_versions table
    # Create enterprise_collections table
    # Create enterprise_collection_artifacts table
    # Create indexes
    pass

def downgrade():
    # Drop all tables in reverse order
    # Drop all indexes
    pass
```

**Acceptance Criteria:**
- Migration file created with proper Alembic structure
- All CREATE TABLE statements include IF NOT EXISTS (idempotent)
- Indexes created with proper naming (idx_table_column)
- Foreign keys with ON DELETE CASCADE where appropriate
- Downgrade removes all tables in correct order (reverse dependency order)
- Migration is reversible: running upgrade then downgrade leaves clean state
- Comments document purpose and tenant isolation strategy
- Tested with `alembic upgrade head` and `alembic downgrade -1`

---

### ENT-1.8: Implement Alembic Migration: Tenant Columns

**Description:**

Create a follow-up migration that adds tenant_id columns to existing shared tables (if any) that need multi-tenant scoping. This ensures we don't break SQLite-only deployments.

**File:** `skillmeat/cache/migrations/versions/20260306_XXXX_add_tenant_isolation.py`

**Strategy:**
- Identify tables that must support both single-tenant (SQLite) and multi-tenant (PostgreSQL) operation
- Add tenant_id as nullable column (SQLite ignores it)
- Add conditional indexes (PostgreSQL only)
- Document which tables are "enterprise-only" (new) vs "shared" (updated)

**Acceptance Criteria:**
- Migration created only if needed (depends on ENT-1.1 review)
- tenant_id added as nullable VARCHAR(36) or UUID
- Existing SQLite tables unchanged in structure (new column added, not renamed)
- Migration includes data backfill strategy (e.g., `UPDATE table SET tenant_id = DEFAULT_TENANT_ID WHERE tenant_id IS NULL`)
- Downgrade removes tenant_id from shared tables
- No data loss on downgrade

---

### ENT-1.9: Database Connection Factory

**Description:**

Implement the runtime database selection logic that uses PostgreSQL when configured and SQLite otherwise.

**File:** `skillmeat/cache/config.py` (or new `skillmeat/cache/db_factory.py`)

**Key Features:**
```python
def get_engine():
    """Return SQLAlchemy engine based on environment configuration.

    Behavior:
    - If DATABASE_URL env var set (or SKILLMEAT_DATABASE_URL): Use PostgreSQL
    - If DATABASE_PATH env var set: Use SQLite at that path
    - Otherwise: Use default SQLite at ~/.skillmeat/cache.db

    Returns:
        sqlalchemy.engine.Engine configured for the detected backend.
    """

def is_enterprise_mode():
    """Return True if running in enterprise (PostgreSQL) mode."""
```

**Acceptance Criteria:**
- Function checks DATABASE_URL and SKILLMEAT_DATABASE_URL env vars
- Falls back to SQLite if PostgreSQL not configured
- Connection string validated before engine creation
- Connection pooling configured (max_overflow, pool_size)
- Pool recycle set appropriately (PostgreSQL idle timeout handling)
- Logging at startup: "Using SQLite" or "Using PostgreSQL at <host>"
- All existing code uses `get_engine()` instead of hardcoded paths

**Environment Variables:**
```bash
# Enterprise mode (PostgreSQL)
DATABASE_URL=postgresql://user:pass@host/skillmeat
# or
SKILLMEAT_DATABASE_URL=postgresql://user:pass@host/skillmeat

# Local mode (SQLite)
DATABASE_PATH=~/.skillmeat/cache.db
# or
SKILLMEAT_DATABASE_PATH=~/.skillmeat/cache.db
```

---

### ENT-1.10: Docker-Compose PostgreSQL for Testing

**Description:**

Create a docker-compose configuration for local development and CI testing, allowing developers to test enterprise features without managing PostgreSQL manually.

**File:** `docker-compose.test.yml`

**Structure:**
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: skillmeat_test
      POSTGRES_USER: skillmeat
      POSTGRES_PASSWORD: skillmeat-dev
    ports:
      - "5432:8432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U skillmeat"]
      interval: 5s
      timeout: 5s
      retries: 5

  migrate:
    build: .
    command: alembic upgrade head
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://skillmeat:skillmeat-dev@postgres/skillmeat_test
    volumes:
      - .:/app
```

**Acceptance Criteria:**
- docker-compose file created and tested on macOS/Linux/Windows
- PostgreSQL 15 (or latest stable) configured
- Automatic schema migration on startup (via `alembic upgrade head`)
- Seed data scripts for test fixtures (optional but useful)
- Documentation in README.md for running: `docker-compose -f docker-compose.test.yml up`
- Integration with CI/CD (GitHub Actions runs tests against this)
- Teardown removes data between test runs
- Health check waits for PostgreSQL readiness

**Usage:**
```bash
# Start PostgreSQL for local testing
docker-compose -f docker-compose.test.yml up -d

# Run tests against it
pytest tests/integration/

# Stop and clean up
docker-compose -f docker-compose.test.yml down -v
```

---

### ENT-1.11: Schema Integration Tests

**Description:**

Write comprehensive integration tests that verify the enterprise schema behaves correctly under realistic load and isolation scenarios.

**File:** `tests/integration/test_enterprise_schema.py`

**Test Cases:**
1. **Tenant Isolation:** Verify queries on one tenant do not see data from other tenants
2. **Artifact Versions:** Verify content_hash deduplication works (two identical artifact versions share hash)
3. **Collection Nesting:** Verify collection_artifacts properly links artifacts to collections
4. **Index Performance:** Verify queries use indexes (EXPLAIN ANALYZE)
5. **Constraint Enforcement:** Verify unique constraints and FKs work
6. **Large Collections:** Test with 1000+ artifacts in single collection
7. **Concurrent Writes:** Verify no race conditions in version creation

**Acceptance Criteria:**
- Test suite runs against docker-compose PostgreSQL
- All tests pass with isolation level set to READ_COMMITTED
- Tenant isolation verified with explicit multi-tenant test scenarios
- Performance benchmarks established (baseline for Phase 2)
- Edge cases covered: empty collections, single-artifact collections, null fields
- Test data seeding scripts included (fixtures)

**Example Test:**
```python
def test_tenant_isolation(postgres_session):
    """Verify queries on one tenant do not see data from another."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Create artifact in tenant A
    artifact_a = enterprise_artifacts.insert().values(
        tenant_id=tenant_a,
        name="skill-a",
        type="skill"
    )

    # Query from tenant B should return nothing
    result = postgres_session.execute(
        select(enterprise_artifacts).where(
            enterprise_artifacts.c.tenant_id == tenant_b
        )
    )
    assert len(result) == 0  # Tenant B sees no artifacts from tenant A
```

---

### ENT-1.12: Migration Rollback Testing

**Description:**

Verify that all Alembic migrations can be safely reversed without data loss or corruption.

**File:** `tests/integration/test_migrations.py`

**Test Cases:**
1. **Upgrade → Downgrade:** Run `alembic upgrade head` then `alembic downgrade -1` multiple times
2. **Idempotency:** Running the same migration twice produces the same schema
3. **Data Preservation:** Insert test data before migration, verify it survives upgrade and downgrade
4. **Constraint Integrity:** Foreign keys remain valid after migration
5. **Index Consistency:** Indexes can be rebuilt after migration

**Acceptance Criteria:**
- All migrations (ENT-1.7, ENT-1.8) can be reversed successfully
- Running `alembic upgrade head; alembic downgrade -1; alembic upgrade head` leaves clean state
- Test data inserted during migration is recovered after downgrade
- No dangling foreign keys or index inconsistencies
- Migration is safe to run in production (no breaking changes to existing SQLite schema)

---

## Quality Gates

**Phase 1 Complete When:**

- [ ] All 12 tasks marked complete
- [ ] All 4 enterprise tables created with proper indexes and constraints
- [ ] artifact_versions table with content_hash and markdown_payload columns ✓
- [ ] Alembic migrations created, tested, and reversible ✓
- [ ] Docker-compose PostgreSQL functional and integrated with CI
- [ ] Integration tests passing: tenant isolation, versioning, constraints ✓
- [ ] No breaking changes to existing SQLite schema ✓
- [ ] Migration rollback testing passing ✓
- [ ] Code reviewed by backend-architect and data-layer-expert ✓

**Review Checklist:**
- [ ] Schema document approved (ENT-1.1)
- [ ] Tenant scoping strategy document complete (ENT-1.6)
- [ ] All migrations are reversible (ENT-1.12)
- [ ] Integration tests cover edge cases (ENT-1.11)
- [ ] Connection factory handles all deployment scenarios (ENT-1.9)
- [ ] Docker-compose setup matches CI/CD environment (ENT-1.10)

---

## Dependencies & Blockers

**Entry Criteria Met When:**
- PRD 1 (Repository Pattern) >90% complete
- PostgreSQL development instance available
- Data-layer-expert and backend-architect available full-time

**Note: PRD 2 (AuthContext / Multi-Tenancy) is NOT required for Phase 1.** Phase 1 operates in single-tenant bootstrap mode using `DEFAULT_TENANT_ID`. PRD 2 is only needed when real per-user tenant isolation is introduced (Phase 4+).

**Blocking on:**
- PRD 1 completion (repository interfaces that Phase 2 will implement)

**Exit Blockers for Phase 2:**
- If any migration fails, Phase 2 cannot begin
- If tenant isolation tests fail, Phase 2 must restart design

---

## Architectural Notes

**Single-Tenant Bootstrap**: All `tenant_id` columns default to `DEFAULT_TENANT_ID` (configured via `SKILLMEAT_DEFAULT_TENANT_ID` env var or config). This enables the full enterprise schema to be implemented, tested, and deployed without requiring PRD 2's AuthContext. When PRD 2 lands, the DI layer substitutes `AuthContext.tenant_id` for `DEFAULT_TENANT_ID` — no schema changes required.

---

## References

- **PRD 3:** docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
- **PRD 1:** docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md (interfaces this phase depends on)
- **Existing Schema:** skillmeat/cache/models/ (models to extend or mirror)
- **Alembic Docs:** https://alembic.sqlalchemy.org/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/15/
- **Repository Pattern:** `.claude/context/key-context/repository-architecture.md`
- **Data Flow Patterns:** `.claude/context/key-context/data-flow-patterns.md`

---

## Success Metrics

- All 12 tasks completed on schedule
- Schema supports 100+ tenants without performance degradation
- All migrations reversible (zero data loss)
- Integration test suite runs in <30s against docker-compose
- Tenant isolation verified by security review
