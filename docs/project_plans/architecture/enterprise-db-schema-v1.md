---
title: "Enterprise DB Schema Design"
doc_type: architecture
status: draft
phase: 1
created: 2026-03-06
updated: 2026-03-06
feature_slug: enterprise-db-storage
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
phase_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-1-schema.md
reviewed_by: []
tasks_dependent:
  - ENT-1.2
  - ENT-1.3
  - ENT-1.4
  - ENT-1.5
  - ENT-1.6
  - ENT-1.7
  - ENT-1.8
---

# Enterprise DB Schema Design

## Document Purpose

This document is the single source of truth for the PostgreSQL schema introduced by the enterprise-db-storage feature (ENT phase 1). All 4 new enterprise tables are specified here with full DDL, indexes, constraints, tenant isolation strategy, and Alembic migration guidance. Tasks ENT-1.2 through ENT-1.8 implement exactly what is specified here; any deviation requires updating this document first.

**Target database:** PostgreSQL 15+
**Migration tooling:** Alembic (existing chain under `skillmeat/cache/migrations/`)
**Existing backend:** SQLite (`~/.skillmeat/cache/cache.db`) — unchanged and untouched by Phase 1

---

## Table of Contents

1. [Context: Existing Schema](#1-context-existing-schema)
2. [New Enterprise Tables](#2-new-enterprise-tables)
   - [enterprise_artifacts](#21-enterprise_artifacts)
   - [artifact_versions](#22-artifact_versions)
   - [enterprise_collections](#23-enterprise_collections)
   - [enterprise_collection_artifacts](#24-enterprise_collection_artifacts)
3. [Relationship Diagram](#3-relationship-diagram)
4. [Index Strategy](#4-index-strategy)
5. [Constraint Catalog](#5-constraint-catalog)
6. [Tenant Isolation Strategy](#6-tenant-isolation-strategy)
7. [Relationship to Existing Shared Tables](#7-relationship-to-existing-shared-tables)
8. [SQLAlchemy ORM Model Sketches](#8-sqlalchemy-orm-model-sketches)
9. [Alembic Migration Strategy](#9-alembic-migration-strategy)
10. [Design Decisions and Rationale](#10-design-decisions-and-rationale)

---

## 1. Context: Existing Schema

The current cache layer uses **SQLite** with a schema that has grown across 60+ Alembic migrations. The tables relevant to enterprise work are:

| Table | Purpose | Enterprise relevance |
|-------|---------|---------------------|
| `projects` | Filesystem project tracking | Not mirrored — enterprise stores cloud artifacts, not FS deployments |
| `artifacts` | Artifact metadata per project, string PK (`type:name`) | Shared table; `tenant_id` added in ENT-1.8 |
| `artifact_versions` | Version history with `content_hash`, `change_origin` | **Existing** — enterprise extends with `markdown_payload` and richer versioning in a new table |
| `collections` | Named artifact groupings | Shared table; enterprise counterpart is `enterprise_collections` |
| `collection_artifacts` | Collection-artifact M2M junction (uses `artifact_uuid`) | Shared table; enterprise counterpart is `enterprise_collection_artifacts` |
| `groups` | Subgroups within collections | Local-mode only; no enterprise counterpart in Phase 1 |

**Key distinction:** The enterprise tables are a parallel, PostgreSQL-native schema. They do not alter SQLite tables. Existing `artifacts`, `collections`, and `collection_artifacts` tables remain the local-mode source of truth. The enterprise tables are the cloud-mode source of truth.

The most recent migration in the SQLite chain (as of 2026-03-06) is:
`20260303_1100_add_workflow_to_artifact_type_check`

The enterprise Alembic branch diverges from this revision.

---

## 2. New Enterprise Tables

### 2.1 `enterprise_artifacts`

**Purpose:** Primary store for artifact metadata in enterprise (cloud/PostgreSQL) deployments. Each row represents one artifact belonging to one tenant.

#### DDL

```sql
CREATE TABLE enterprise_artifacts (
    -- Identity
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL,

    -- Core metadata
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(50)  NOT NULL,
    description     TEXT,
    source_url      VARCHAR(512),
    scope           VARCHAR(50)  NOT NULL DEFAULT 'user',

    -- Flexible storage
    tags            JSONB        NOT NULL DEFAULT '[]'::jsonb,
    custom_fields   JSONB        NOT NULL DEFAULT '{}'::jsonb,

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_by      VARCHAR(255),

    -- Constraints
    CONSTRAINT pk_enterprise_artifacts
        PRIMARY KEY (id),
    CONSTRAINT uq_enterprise_artifacts_tenant_name_type
        UNIQUE (tenant_id, name, type),
    CONSTRAINT ck_enterprise_artifacts_type
        CHECK (type IN (
            'skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook',
            'workflow', 'composite', 'project_config', 'spec_file',
            'rule_file', 'context_file', 'progress_template'
        )),
    CONSTRAINT ck_enterprise_artifacts_scope
        CHECK (scope IN ('user', 'local')),
    CONSTRAINT ck_enterprise_artifacts_name_length
        CHECK (length(name) > 0 AND length(name) <= 255)
);
```

#### Column Descriptions

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `id` | UUID | NO | `gen_random_uuid()` | Globally unique artifact identifier; used as FK target by `artifact_versions` and `enterprise_collection_artifacts` |
| `tenant_id` | UUID | NO | — | Tenant scope; every query MUST filter by this |
| `name` | VARCHAR(255) | NO | — | Human-readable artifact name (e.g., `canvas-design`, `dev-execution`) |
| `type` | VARCHAR(50) | NO | — | Artifact type; matches existing `check_artifact_type` constraint values |
| `description` | TEXT | YES | NULL | Optional human-readable description from frontmatter |
| `source_url` | VARCHAR(512) | YES | NULL | GitHub origin URL (`github:owner/repo/path`); used for upstream sync tracking |
| `scope` | VARCHAR(50) | NO | `'user'` | `user` = stored in user's global collection; `local` = project-scoped |
| `tags` | JSONB | NO | `'[]'` | Array of tag strings for filtering; JSONB allows GIN indexing |
| `custom_fields` | JSONB | NO | `'{}'` | Arbitrary key-value pairs for schema-less extensibility |
| `created_at` | TIMESTAMPTZ | NO | `now()` | Creation timestamp (timezone-aware) |
| `updated_at` | TIMESTAMPTZ | NO | `now()` | Last-modified timestamp; updated by application logic or trigger |
| `created_by` | VARCHAR(255) | YES | NULL | User ID or `"system"` for audit; NULL until PRD 2 AuthContext available |

#### Indexes

```sql
-- Primary tenant filter (used in every query)
CREATE INDEX idx_enterprise_artifacts_tenant_id
    ON enterprise_artifacts (tenant_id);

-- Tenant + type composite (type-filtered listing within a tenant)
CREATE INDEX idx_enterprise_artifacts_tenant_type
    ON enterprise_artifacts (tenant_id, type);

-- Sorting by recency
CREATE INDEX idx_enterprise_artifacts_tenant_created_at
    ON enterprise_artifacts (tenant_id, created_at DESC);

-- JSONB tag search (GIN allows efficient @> containment queries)
CREATE INDEX idx_enterprise_artifacts_tags_gin
    ON enterprise_artifacts USING GIN (tags jsonb_path_ops);

-- Source URL lookup (for upstream sync matching)
CREATE INDEX idx_enterprise_artifacts_source_url
    ON enterprise_artifacts (source_url)
    WHERE source_url IS NOT NULL;
```

---

### 2.2 `artifact_versions`

**Purpose:** Stores immutable content snapshots for enterprise artifacts. Each row captures one version of an artifact's Markdown payload with a SHA256 content hash for deduplication. The existing SQLite `artifact_versions` table (for change-origin tracking in local mode) is a separate, unrelated table; this is the enterprise counterpart.

**Note on naming:** The existing SQLite table is also named `artifact_versions`. The PostgreSQL enterprise table uses the same name but operates in a different database entirely. Alembic migrations must handle this via dialect-conditional guards (see Section 9).

#### DDL

```sql
CREATE TABLE artifact_versions (
    -- Identity
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),
    artifact_id     UUID        NOT NULL,
    tenant_id       UUID        NOT NULL,

    -- Content
    content_hash    VARCHAR(64)  NOT NULL,   -- SHA256 hex digest (64 chars)
    markdown_payload TEXT        NOT NULL,   -- Full artifact Markdown content

    -- Version labeling
    version_label   VARCHAR(50),             -- Semantic tag: v1.0.0, latest, etc.
    commit_sha      VARCHAR(40),             -- GitHub commit SHA (40 chars)
    created_by      VARCHAR(255),            -- User ID or "system"

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT pk_artifact_versions
        PRIMARY KEY (id),
    CONSTRAINT fk_artifact_versions_artifact_id
        FOREIGN KEY (artifact_id)
        REFERENCES enterprise_artifacts(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_artifact_versions_content_hash
        UNIQUE (content_hash),
    CONSTRAINT ck_artifact_versions_content_hash_length
        CHECK (length(content_hash) = 64),
    CONSTRAINT ck_artifact_versions_commit_sha_length
        CHECK (commit_sha IS NULL OR length(commit_sha) = 40)
);
```

#### Column Descriptions

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `id` | UUID | NO | `gen_random_uuid()` | Version record primary key |
| `artifact_id` | UUID | NO | — | FK to `enterprise_artifacts.id`; cascade-deletes when artifact is removed |
| `tenant_id` | UUID | NO | — | Denormalized for query efficiency; must equal the parent artifact's `tenant_id` |
| `content_hash` | VARCHAR(64) | NO | — | SHA256 of `markdown_payload`; globally unique — enables cross-tenant deduplication without sharing content |
| `markdown_payload` | TEXT | NO | — | Full Markdown content of the artifact at this version; no size cap for Phase 1 |
| `version_label` | VARCHAR(50) | YES | NULL | Human-readable label (`v1.0.0`, `latest`, `stable`); may be NULL for auto-captured snapshots |
| `commit_sha` | VARCHAR(40) | YES | NULL | GitHub commit SHA for the source of this version; enables git-provenance tracing |
| `created_by` | VARCHAR(255) | YES | NULL | User ID or `"system"`; NULL until PRD 2 |
| `created_at` | TIMESTAMPTZ | NO | `now()` | Immutable creation timestamp; versions are never updated |

**Immutability invariant:** Rows in `artifact_versions` are never updated. A new row is always inserted for each content change. The `content_hash` uniqueness constraint enforces deduplication: inserting an identical payload for the same or different artifact is an application-level no-op (look up by `content_hash` first).

#### Indexes

```sql
-- Primary lookup: all versions of a specific artifact, newest first
CREATE INDEX idx_artifact_versions_artifact_created
    ON artifact_versions (artifact_id, created_at DESC);

-- Content hash lookup (deduplication check before insert)
-- Note: The UNIQUE constraint already creates an index; this is explicit for clarity.
-- The UNIQUE constraint on content_hash covers this access pattern.

-- Tenant-scoped version queries (for listing recent versions across tenant's artifacts)
CREATE INDEX idx_artifact_versions_tenant_created
    ON artifact_versions (tenant_id, created_at DESC);

-- Commit SHA lookup (upstream sync: "do we already have this commit?")
CREATE INDEX idx_artifact_versions_commit_sha
    ON artifact_versions (commit_sha)
    WHERE commit_sha IS NOT NULL;
```

---

### 2.3 `enterprise_collections`

**Purpose:** Named groupings of enterprise artifacts per tenant. Mirrors the intent of the existing `collections` table but is PostgreSQL-native and tenant-scoped. Each tenant can have multiple collections; one may be designated as default.

#### DDL

```sql
CREATE TABLE enterprise_collections (
    -- Identity
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL,

    -- Core metadata
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    is_default      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_by      VARCHAR(255),

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT pk_enterprise_collections
        PRIMARY KEY (id),
    CONSTRAINT uq_enterprise_collections_tenant_name
        UNIQUE (tenant_id, name),
    CONSTRAINT ck_enterprise_collections_name_length
        CHECK (length(name) > 0 AND length(name) <= 255)
);
```

#### Column Descriptions

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `id` | UUID | NO | `gen_random_uuid()` | Collection primary key |
| `tenant_id` | UUID | NO | — | Tenant scope; every query MUST filter by this |
| `name` | VARCHAR(255) | NO | — | Human-readable collection name; unique per tenant |
| `description` | TEXT | YES | NULL | Optional description |
| `is_default` | BOOLEAN | NO | `FALSE` | When `TRUE`, the CLI uses this collection for `skillmeat deploy` without an explicit `--collection` flag |
| `created_by` | VARCHAR(255) | YES | NULL | User ID or `"system"`; NULL until PRD 2 |
| `created_at` | TIMESTAMPTZ | NO | `now()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NO | `now()` | Last-modified timestamp |

**`is_default` invariant:** At most one collection per tenant may have `is_default = TRUE`. This is enforced at the application layer (repository), not by a database constraint, to avoid complex partial-unique index semantics across PostgreSQL versions. The repository's `set_default` method sets `is_default = FALSE` on all other collections for the same tenant in the same transaction before setting the new one to `TRUE`.

#### Indexes

```sql
-- Primary tenant filter
CREATE INDEX idx_enterprise_collections_tenant_id
    ON enterprise_collections (tenant_id);

-- Default collection lookup (most common query: "which collection is default?")
CREATE INDEX idx_enterprise_collections_tenant_default
    ON enterprise_collections (tenant_id, is_default)
    WHERE is_default = TRUE;

-- Alphabetical listing within a tenant
CREATE INDEX idx_enterprise_collections_tenant_name
    ON enterprise_collections (tenant_id, name);
```

---

### 2.4 `enterprise_collection_artifacts`

**Purpose:** Many-to-many junction table linking enterprise artifacts to enterprise collections, with ordering support. One artifact may appear in multiple collections; order within each collection is tracked via `order_index`.

#### DDL

```sql
CREATE TABLE enterprise_collection_artifacts (
    -- Identity
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),

    -- Relationships
    collection_id   UUID        NOT NULL,
    artifact_id     UUID        NOT NULL,
    tenant_id       UUID        NOT NULL,

    -- Ordering
    order_index     INTEGER     NOT NULL DEFAULT 0,

    -- Audit
    added_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT pk_enterprise_collection_artifacts
        PRIMARY KEY (id),
    CONSTRAINT fk_eca_collection_id
        FOREIGN KEY (collection_id)
        REFERENCES enterprise_collections(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_eca_artifact_id
        FOREIGN KEY (artifact_id)
        REFERENCES enterprise_artifacts(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_eca_collection_artifact
        UNIQUE (collection_id, artifact_id),
    CONSTRAINT ck_eca_order_index
        CHECK (order_index >= 0)
);
```

#### Column Descriptions

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `id` | UUID | NO | `gen_random_uuid()` | Junction row primary key; UUID simplifies API referencing of membership records |
| `collection_id` | UUID | NO | — | FK to `enterprise_collections.id`; cascade-deletes when collection is removed |
| `artifact_id` | UUID | NO | — | FK to `enterprise_artifacts.id`; cascade-deletes when artifact is removed |
| `tenant_id` | UUID | NO | — | Denormalized for query efficiency; validated by application layer to match the parent collection's `tenant_id` |
| `order_index` | INTEGER | NO | `0` | Sort order within the collection; 0-based, gaps are allowed (UI handles renumbering) |
| `added_at` | TIMESTAMPTZ | NO | `now()` | Audit timestamp: when the artifact was added to the collection |

**Cascade behavior:** Deleting an `enterprise_artifacts` row cascades to remove all `enterprise_collection_artifacts` rows referencing it. Deleting an `enterprise_collections` row cascades similarly. The artifact itself is not deleted when removed from a collection.

#### Indexes

```sql
-- Primary access pattern: list all artifacts in a collection, ordered
CREATE INDEX idx_eca_collection_order
    ON enterprise_collection_artifacts (collection_id, order_index);

-- Reverse lookup: which collections contain this artifact?
CREATE INDEX idx_eca_artifact_id
    ON enterprise_collection_artifacts (artifact_id);

-- Tenant-scoped queries across junction table
CREATE INDEX idx_eca_tenant_id
    ON enterprise_collection_artifacts (tenant_id);

-- Composite for: "all artifacts in collection X for tenant Y" (with tenant guard)
CREATE INDEX idx_eca_collection_tenant_order
    ON enterprise_collection_artifacts (collection_id, tenant_id, order_index);
```

---

## 3. Relationship Diagram

```
enterprise_artifacts                    artifact_versions
+------------------+                   +------------------------+
| id (PK)          |<------------------| artifact_id (FK)       |
| tenant_id        |                   | id (PK)                |
| name             |                   | tenant_id              |
| type             |                   | content_hash (UNIQUE)  |
| description      |                   | markdown_payload       |
| source_url       |                   | version_label          |
| scope            |                   | commit_sha             |
| tags (JSONB)     |                   | created_by             |
| custom_fields    |                   | created_at             |
| created_at       |                   +------------------------+
| updated_at       |
| created_by       |
+------------------+
        ^
        |  (FK: artifact_id)
        |
enterprise_collection_artifacts         enterprise_collections
+---------------------------+           +------------------------+
| id (PK)                   |           | id (PK)                |
| collection_id (FK) --------+---------->| tenant_id              |
| artifact_id (FK)  --------+           | name                   |
| tenant_id                 |           | description            |
| order_index               |           | is_default             |
| added_at                  |           | created_by             |
+---------------------------+           | created_at             |
                                        | updated_at             |
                                        +------------------------+
```

**Cardinalities:**
- `enterprise_artifacts` 1 --- N `artifact_versions` (one artifact, many versions)
- `enterprise_artifacts` N --- M `enterprise_collections` via `enterprise_collection_artifacts`
- Each `tenant_id` scopes all four tables; cross-tenant joins are prohibited

---

## 4. Index Strategy

### Index Naming Convention

```
idx_{table_short}_{columns}[_{modifier}]

Examples:
  idx_enterprise_artifacts_tenant_id
  idx_enterprise_artifacts_tags_gin
  idx_artifact_versions_artifact_created
  idx_eca_collection_order
```

### Index Summary Table

| Index Name | Table | Columns | Type | Reason |
|------------|-------|---------|------|--------|
| `idx_enterprise_artifacts_tenant_id` | `enterprise_artifacts` | `(tenant_id)` | B-tree | All queries filter by tenant first |
| `idx_enterprise_artifacts_tenant_type` | `enterprise_artifacts` | `(tenant_id, type)` | B-tree | Type-filtered listing: `GET /artifacts?type=skill` |
| `idx_enterprise_artifacts_tenant_created_at` | `enterprise_artifacts` | `(tenant_id, created_at DESC)` | B-tree | Default sort: newest artifacts first |
| `idx_enterprise_artifacts_tags_gin` | `enterprise_artifacts` | `(tags)` | GIN (`jsonb_path_ops`) | Tag-based filtering: `tags @> '["frontend"]'` |
| `idx_enterprise_artifacts_source_url` | `enterprise_artifacts` | `(source_url)` WHERE NOT NULL | B-tree | Upstream sync matching by GitHub URL |
| `idx_artifact_versions_artifact_created` | `artifact_versions` | `(artifact_id, created_at DESC)` | B-tree | Version history pagination |
| `idx_artifact_versions_tenant_created` | `artifact_versions` | `(tenant_id, created_at DESC)` | B-tree | Cross-artifact recent-versions queries |
| `idx_artifact_versions_commit_sha` | `artifact_versions` | `(commit_sha)` WHERE NOT NULL | B-tree | Upstream sync: commit already ingested? |
| `idx_enterprise_collections_tenant_id` | `enterprise_collections` | `(tenant_id)` | B-tree | All collection queries filter by tenant |
| `idx_enterprise_collections_tenant_default` | `enterprise_collections` | `(tenant_id, is_default)` WHERE `is_default = TRUE` | Partial B-tree | Default collection lookup (single row) |
| `idx_enterprise_collections_tenant_name` | `enterprise_collections` | `(tenant_id, name)` | B-tree | Alphabetical collection listing |
| `idx_eca_collection_order` | `enterprise_collection_artifacts` | `(collection_id, order_index)` | B-tree | Ordered artifact list within a collection |
| `idx_eca_artifact_id` | `enterprise_collection_artifacts` | `(artifact_id)` | B-tree | Reverse: which collections contain this artifact? |
| `idx_eca_tenant_id` | `enterprise_collection_artifacts` | `(tenant_id)` | B-tree | Tenant-scoped junction queries |
| `idx_eca_collection_tenant_order` | `enterprise_collection_artifacts` | `(collection_id, tenant_id, order_index)` | B-tree | Guarded listing with tenant check |

### Why GIN for Tags

The `tags` column stores a JSONB array such as `["frontend", "design", "ui"]`. GIN with `jsonb_path_ops` supports efficient containment queries:

```sql
-- Find all artifacts tagged "frontend" for a tenant
SELECT * FROM enterprise_artifacts
WHERE tenant_id = $1
  AND tags @> '["frontend"]'::jsonb;
```

A B-tree index cannot accelerate JSONB containment queries. GIN index lookup is O(log N) per tag value. For the MVP tag volumes (<10K artifacts per tenant), this is more than sufficient.

### Production Index Creation

All indexes except the constraint-backing unique indexes should be created with `CONCURRENTLY` in the Alembic migration to avoid table locks during deployment:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enterprise_artifacts_tenant_id
    ON enterprise_artifacts (tenant_id);
```

The Alembic `create_index` call uses `postgresql_concurrently=True` for this purpose.

---

## 5. Constraint Catalog

### Primary Keys

| Table | PK Column | Type | Notes |
|-------|-----------|------|-------|
| `enterprise_artifacts` | `id` | UUID | `gen_random_uuid()` server-side default |
| `artifact_versions` | `id` | UUID | `gen_random_uuid()` server-side default |
| `enterprise_collections` | `id` | UUID | `gen_random_uuid()` server-side default |
| `enterprise_collection_artifacts` | `id` | UUID | `gen_random_uuid()` server-side default; not a composite PK to simplify API references to membership records |

### Unique Constraints

| Constraint Name | Table | Columns | Business Rule |
|----------------|-------|---------|---------------|
| `uq_enterprise_artifacts_tenant_name_type` | `enterprise_artifacts` | `(tenant_id, name, type)` | One artifact of a given type per name per tenant |
| `uq_artifact_versions_content_hash` | `artifact_versions` | `(content_hash)` | Global deduplication: identical content is stored once |
| `uq_enterprise_collections_tenant_name` | `enterprise_collections` | `(tenant_id, name)` | No duplicate collection names within a tenant |
| `uq_eca_collection_artifact` | `enterprise_collection_artifacts` | `(collection_id, artifact_id)` | Artifact appears at most once in a given collection |

### Foreign Keys

| Constraint Name | Table | Column | References | On Delete |
|----------------|-------|--------|------------|-----------|
| `fk_artifact_versions_artifact_id` | `artifact_versions` | `artifact_id` | `enterprise_artifacts(id)` | CASCADE |
| `fk_eca_collection_id` | `enterprise_collection_artifacts` | `collection_id` | `enterprise_collections(id)` | CASCADE |
| `fk_eca_artifact_id` | `enterprise_collection_artifacts` | `artifact_id` | `enterprise_artifacts(id)` | CASCADE |

**Note on `tenant_id` in FK-referencing tables:** The `tenant_id` columns in `artifact_versions` and `enterprise_collection_artifacts` are denormalized copies for query performance. They do not carry a foreign key to a `tenants` table (which does not exist in Phase 1). The application layer validates consistency (child `tenant_id` must equal parent `tenant_id`) at write time.

### Check Constraints

| Constraint Name | Table | Expression | Purpose |
|----------------|-------|-----------|---------|
| `ck_enterprise_artifacts_type` | `enterprise_artifacts` | `type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', 'workflow', 'composite', 'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')` | Mirrors existing `check_artifact_type`; keeps types in sync |
| `ck_enterprise_artifacts_scope` | `enterprise_artifacts` | `scope IN ('user', 'local')` | Restricts to valid scope values |
| `ck_enterprise_artifacts_name_length` | `enterprise_artifacts` | `length(name) > 0 AND length(name) <= 255` | Guards against empty names and oversized payloads |
| `ck_enterprise_collections_name_length` | `enterprise_collections` | `length(name) > 0 AND length(name) <= 255` | Mirrors artifact name constraint |
| `ck_artifact_versions_content_hash_length` | `artifact_versions` | `length(content_hash) = 64` | SHA256 hex digest is exactly 64 characters |
| `ck_artifact_versions_commit_sha_length` | `artifact_versions` | `commit_sha IS NULL OR length(commit_sha) = 40` | Full SHA1 is exactly 40 characters |
| `ck_eca_order_index` | `enterprise_collection_artifacts` | `order_index >= 0` | Non-negative ordering |

### NOT NULL Summary

All columns marked NOT NULL in the DDL are required at insert time. Columns marked nullable (YES in the column tables) accept NULL. Application-layer DTOs must enforce these rules before calling repositories; the database is the last line of defense.

---

## 6. Tenant Isolation Strategy

### 6.1 Phase 1 Bootstrap: Single-Tenant Mode

Phases 1-3 operate without PRD 2's AuthContext. A `DEFAULT_TENANT_ID` constant is used as the sole tenant ID for all data. This allows the full enterprise schema and repository layer to be built and tested before multi-tenant RBAC lands.

**Configuration:**

```python
# skillmeat/cache/enterprise_config.py  (created in ENT-1.9)
import os
import uuid

# Read from environment; fall back to a deterministic development UUID.
# This UUID is stable across restarts so test data is consistent in dev.
_FALLBACK_TENANT_ID = "00000000-0000-4000-a000-000000000001"

DEFAULT_TENANT_ID: uuid.UUID = uuid.UUID(
    os.environ.get("SKILLMEAT_DEFAULT_TENANT_ID", _FALLBACK_TENANT_ID)
)
```

**Env var priority:**
1. `SKILLMEAT_DEFAULT_TENANT_ID` — explicit override
2. Hardcoded fallback `00000000-0000-4000-a000-000000000001`

This UUID is inserted into every `tenant_id` column when no AuthContext is available.

### 6.2 Query Pattern: WHERE tenant_id = ?

Every enterprise repository method MUST include a `tenant_id` predicate. No query against an enterprise table may return rows across tenant boundaries.

**Correct pattern:**

```python
def get_artifact(
    session: Session,
    artifact_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> EnterpriseArtifact | None:
    return (
        session.query(EnterpriseArtifact)
        .filter(
            EnterpriseArtifact.id == artifact_id,
            EnterpriseArtifact.tenant_id == tenant_id,  # MANDATORY
        )
        .one_or_none()
    )
```

**Prohibited pattern (security defect):**

```python
# NEVER do this — returns data across all tenants
def get_artifact_WRONG(session: Session, artifact_id: uuid.UUID):
    return session.query(EnterpriseArtifact).filter(
        EnterpriseArtifact.id == artifact_id
        # Missing tenant_id filter
    ).one_or_none()
```

### 6.3 Context Propagation

In Phases 1-3, `tenant_id` flows from the `DEFAULT_TENANT_ID` constant directly into repository method calls.

```
Request arrives → FastAPI route handler
                → repository method(tenant_id=DEFAULT_TENANT_ID)
                → SQL WHERE tenant_id = $1
```

In Phase 4+ (post-PRD 2), `AuthContext` replaces the constant:

```
Request arrives → FastAPI route handler
                → auth middleware extracts AuthContext.tenant_id
                → repository method(tenant_id=ctx.tenant_id)
                → SQL WHERE tenant_id = $1
```

**No schema change is required for this transition.** The `tenant_id` column is present from day one; only the source of the value changes.

### 6.4 Base Repository Class Pattern

Phase 2 (ENT-2.x) will implement a base class that enforces tenant scoping:

```python
# Sketch — implementation in Phase 2
class TenantScopedRepository:
    """Base repository that enforces tenant isolation on all queries."""

    def __init__(self, session: Session, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    def _scoped(self, query):
        """Apply tenant_id filter to a query. Call before executing."""
        # Subclasses call this on every query.
        # Makes omission obvious during code review.
        raise NotImplementedError

class EnterpriseArtifactRepository(TenantScopedRepository):
    def _scoped(self, query):
        return query.filter(EnterpriseArtifact.tenant_id == self.tenant_id)

    def list_all(self) -> list[EnterpriseArtifact]:
        return self._scoped(
            self.session.query(EnterpriseArtifact)
        ).all()
```

### 6.5 Multi-Tenant Test Strategy

Integration tests (ENT-1.11) MUST include negative isolation tests:

```python
def test_tenant_isolation(session):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Insert artifact in tenant A
    session.add(EnterpriseArtifact(
        tenant_id=tenant_a, name="my-skill", type="skill"
    ))
    session.flush()

    # Query from tenant B context must return zero rows
    result = (
        session.query(EnterpriseArtifact)
        .filter(EnterpriseArtifact.tenant_id == tenant_b)
        .all()
    )
    assert result == [], "Tenant B must not see Tenant A's artifacts"
```

### 6.6 Future RLS Migration Path (Not Phase 1)

PostgreSQL Row Level Security (RLS) is documented here as a future path. It is NOT implemented in Phase 1 due to:
- Additional session-variable overhead (`SET LOCAL app.current_tenant_id = ?` per transaction)
- Performance implications that require profiling at scale
- Testing complexity (RLS policies bypass superuser)
- Application-enforced isolation is adequate for initial single-tenant enterprise deployments

**Migration path when RLS becomes necessary:**

```sql
-- Step 1: Enable RLS on each enterprise table (non-destructive)
ALTER TABLE enterprise_artifacts ENABLE ROW LEVEL SECURITY;

-- Step 2: Create isolation policy
CREATE POLICY tenant_isolation ON enterprise_artifacts
    FOR ALL
    TO skillmeat_app_role
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Step 3: Set session variable per transaction (in middleware)
-- SET LOCAL app.current_tenant_id = '<tenant-uuid>';
```

Application-layer `WHERE tenant_id = ?` filters can coexist with RLS during a gradual rollout. RLS provides defense-in-depth; application-layer filtering provides primary enforcement. The transition requires zero schema changes.

---

## 7. Relationship to Existing Shared Tables

### 7.1 Tables That Require tenant_id in ENT-1.8

The following existing shared tables will receive a `tenant_id` column via the ENT-1.8 migration. These are tables that serve both local (SQLite) and enterprise (PostgreSQL) contexts and need tenant scoping when running in enterprise mode.

| Table | Rationale | Column Added | Nullable? |
|-------|-----------|-------------|-----------|
| `collections` | Existing local-mode collections; when mirrored to PG for local users connecting to enterprise, need tenant scoping | `tenant_id VARCHAR(36)` | YES (NULL = local-only, not tenant-scoped) |

**Analysis of other shared tables:**

| Table | Enterprise relevance | Action |
|-------|---------------------|--------|
| `projects` | Local FS project tracking; not relevant to enterprise mode | No change |
| `artifacts` | Local FS artifact cache; enterprise artifacts are in `enterprise_artifacts` | No change in Phase 1 |
| `artifact_versions` | Local change-origin tracking; enterprise versioning in new table | No change |
| `marketplace` / `catalog_entries` | Marketplace browse is read-only and shared; no tenant data | No change |
| `groups` | Local-mode only; no enterprise counterpart in Phase 1 | No change |
| `memory_items` | Project-scoped, no enterprise relevance in Phase 1 | No change |
| `workflow_*` | Local execution only | No change |

### 7.2 Why Parallel Tables vs Extending Existing

The enterprise tables (`enterprise_artifacts`, `enterprise_collections`, `enterprise_collection_artifacts`) are intentionally parallel to the existing SQLite tables rather than extending them. The reasons:

1. **Schema divergence:** Enterprise tables use UUID PKs, JSONB, TIMESTAMPTZ, and PostgreSQL-specific features. Existing tables use TEXT PKs and SQLite-compatible types. Unifying these would require a breaking migration to the existing schema.

2. **Operational separation:** Local mode operates entirely on `artifacts`, `collections`, etc. Enterprise mode operates entirely on `enterprise_*` tables. There is no overlap at runtime.

3. **Rollback safety:** ENT-1.7 (enterprise table creation) can be reversed without touching any existing table. ENT-1.8 (tenant columns on shared tables) adds only a nullable column — also safely reversible.

4. **Migration path:** When a user migrates local data to enterprise cloud (`skillmeat enterprise migrate`, Phase 5), data flows from the local `artifacts` table into `enterprise_artifacts`, not via an in-place schema migration.

---

## 8. SQLAlchemy ORM Model Sketches

These sketches define the column types, relationships, and constraints for the Python ORM models. They are not final runnable code — implementation files are created in ENT-1.2 through ENT-1.5. The models live under `skillmeat/cache/models/` in separate files per the implementation plan's file organization.

### 8.1 EnterpriseArtifact

**File:** `skillmeat/cache/models/enterprise_artifacts.py`

```python
from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from skillmeat.cache.models import Base  # existing DeclarativeBase

class EnterpriseArtifact(Base):
    __tablename__ = "enterprise_artifacts"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Core metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="user")

    # Flexible storage
    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    versions: Mapped[List["ArtifactVersion"]] = relationship(
        "ArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="ArtifactVersion.created_at.desc()",
    )
    collection_memberships: Mapped[List["EnterpriseCollectionArtifact"]] = relationship(
        "EnterpriseCollectionArtifact",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", "type",
                         name="uq_enterprise_artifacts_tenant_name_type"),
        CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'workflow', 'composite', 'project_config', 'spec_file', "
            "'rule_file', 'context_file', 'progress_template')",
            name="ck_enterprise_artifacts_type",
        ),
        CheckConstraint("scope IN ('user', 'local')",
                        name="ck_enterprise_artifacts_scope"),
        CheckConstraint("length(name) > 0 AND length(name) <= 255",
                        name="ck_enterprise_artifacts_name_length"),
        Index("idx_enterprise_artifacts_tenant_id", "tenant_id"),
        Index("idx_enterprise_artifacts_tenant_type", "tenant_id", "type"),
        Index("idx_enterprise_artifacts_tenant_created_at", "tenant_id", "created_at"),
        # GIN index for tags — declared separately in migration (not via Index())
    )
```

### 8.2 ArtifactVersion (Enterprise)

**File:** `skillmeat/cache/models/enterprise_artifacts.py` (same file; companion model)

```python
class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"
    # NOTE: This model maps to the PostgreSQL enterprise table, not the
    # SQLite artifact_versions table. The SQLite table uses a different
    # schema (change_origin, version_lineage) and is mapped by the
    # existing ArtifactVersion model in skillmeat/cache/models.py.
    # This model is PostgreSQL-only and lives in the enterprise models file.

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprise_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Content
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    markdown_payload: Mapped[str] = mapped_column(Text, nullable=False)

    # Version labeling
    version_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Audit (immutable — no updated_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Relationship
    artifact: Mapped["EnterpriseArtifact"] = relationship(
        "EnterpriseArtifact", back_populates="versions"
    )

    __table_args__ = (
        CheckConstraint("length(content_hash) = 64",
                        name="ck_artifact_versions_content_hash_length"),
        CheckConstraint("commit_sha IS NULL OR length(commit_sha) = 40",
                        name="ck_artifact_versions_commit_sha_length"),
        Index("idx_artifact_versions_artifact_created", "artifact_id", "created_at"),
        Index("idx_artifact_versions_tenant_created", "tenant_id", "created_at"),
        Index("idx_artifact_versions_commit_sha", "commit_sha"),
        # UNIQUE constraint on content_hash handled by unique=True on mapped_column
    )
```

### 8.3 EnterpriseCollection

**File:** `skillmeat/cache/models/enterprise_collections.py`

```python
class EnterpriseCollection(Base):
    __tablename__ = "enterprise_collections"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Core metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relationships
    memberships: Mapped[List["EnterpriseCollectionArtifact"]] = relationship(
        "EnterpriseCollectionArtifact",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EnterpriseCollectionArtifact.order_index",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name",
                         name="uq_enterprise_collections_tenant_name"),
        CheckConstraint("length(name) > 0 AND length(name) <= 255",
                        name="ck_enterprise_collections_name_length"),
        Index("idx_enterprise_collections_tenant_id", "tenant_id"),
        Index("idx_enterprise_collections_tenant_name", "tenant_id", "name"),
        # Partial index for is_default — declared separately in migration
    )
```

### 8.4 EnterpriseCollectionArtifact

**File:** `skillmeat/cache/models/enterprise_collections.py` (same file; companion model)

```python
class EnterpriseCollectionArtifact(Base):
    __tablename__ = "enterprise_collection_artifacts"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Relationships
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprise_collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprise_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Ordering
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Audit
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    collection: Mapped["EnterpriseCollection"] = relationship(
        "EnterpriseCollection", back_populates="memberships"
    )
    artifact: Mapped["EnterpriseArtifact"] = relationship(
        "EnterpriseArtifact", back_populates="collection_memberships"
    )

    __table_args__ = (
        UniqueConstraint("collection_id", "artifact_id",
                         name="uq_eca_collection_artifact"),
        CheckConstraint("order_index >= 0",
                        name="ck_eca_order_index"),
        Index("idx_eca_collection_order", "collection_id", "order_index"),
        Index("idx_eca_artifact_id", "artifact_id"),
        Index("idx_eca_tenant_id", "tenant_id"),
        Index("idx_eca_collection_tenant_order", "collection_id", "tenant_id", "order_index"),
    )
```

### 8.5 ORM Model File Organization

```
skillmeat/cache/models/
├── __init__.py               # Re-exports all models; imports enterprise models
├── enterprise_artifacts.py   # EnterpriseArtifact + ArtifactVersion (enterprise)
├── enterprise_collections.py # EnterpriseCollection + EnterpriseCollectionArtifact
└── enterprise_schema.py      # Shared utilities: DEFAULT_TENANT_ID, enterprise Base metadata
```

The existing `skillmeat/cache/models.py` monolith is not modified in Phase 1. New models are added in the new submodule files and imported into the shared `Base.metadata` by importing them in `models/__init__.py`.

---

## 9. Alembic Migration Strategy

### 9.1 Migration Chain Position

The enterprise schema migrations are appended to the end of the existing Alembic revision chain. They do NOT create a separate branch. This ensures `alembic upgrade head` applies all migrations (local + enterprise) in sequence on a PostgreSQL instance.

```
... (existing SQLite migrations)
20260303_1100_add_workflow_to_artifact_type_check   <- current HEAD
        |
        v
20260306_1200_create_enterprise_schema              <- ENT-1.7 (new)
        |
        v
20260306_1300_add_tenant_columns_shared_tables      <- ENT-1.8 (new, conditional)
```

### 9.2 ENT-1.7: Enterprise Schema Creation Migration

**File:** `skillmeat/cache/migrations/versions/20260306_1200_create_enterprise_schema.py`

**Revision chain:**
```python
revision = "20260306_1200_create_enterprise_schema"
down_revision = "20260303_1100_add_workflow_to_artifact_type_check"
branch_labels = None
depends_on = None
```

**Upgrade strategy:**

The migration uses `op.get_bind()` dialect inspection to skip SQLite-incompatible DDL. On SQLite connections, a warning is logged and the migration exits cleanly (SQLite-only deployments never create enterprise tables).

```python
def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite local mode — enterprise tables are not created here.
        # This migration is a no-op for SQLite; enterprise tables only
        # exist in PostgreSQL deployments.
        import logging
        logging.getLogger(__name__).info(
            "Skipping enterprise schema creation on SQLite (local mode)."
        )
        return

    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # 1. enterprise_artifacts
    if "enterprise_artifacts" not in existing:
        op.create_table(
            "enterprise_artifacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("type", sa.String(50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_url", sa.String(512), nullable=True),
            sa.Column("scope", sa.String(50), nullable=False, server_default="user"),
            sa.Column("tags", postgresql.JSONB(), nullable=False,
                      server_default=sa.text("'[]'::jsonb")),
            sa.Column("custom_fields", postgresql.JSONB(), nullable=False,
                      server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("created_by", sa.String(255), nullable=True),
            sa.UniqueConstraint("tenant_id", "name", "type",
                                name="uq_enterprise_artifacts_tenant_name_type"),
            sa.CheckConstraint(
                "type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
                "'workflow', 'composite', 'project_config', 'spec_file', "
                "'rule_file', 'context_file', 'progress_template')",
                name="ck_enterprise_artifacts_type",
            ),
            sa.CheckConstraint("scope IN ('user', 'local')",
                               name="ck_enterprise_artifacts_scope"),
            sa.CheckConstraint("length(name) > 0 AND length(name) <= 255",
                               name="ck_enterprise_artifacts_name_length"),
        )
        # Indexes (CONCURRENTLY not allowed inside a transaction block;
        # use postgresql_concurrently=True which Alembic wraps correctly)
        op.create_index("idx_enterprise_artifacts_tenant_id",
                        "enterprise_artifacts", ["tenant_id"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_enterprise_artifacts_tenant_type",
                        "enterprise_artifacts", ["tenant_id", "type"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_enterprise_artifacts_tenant_created_at",
                        "enterprise_artifacts", ["tenant_id", "created_at"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_enterprise_artifacts_tags_gin",
                        "enterprise_artifacts", ["tags"],
                        postgresql_using="gin",
                        postgresql_ops={"tags": "jsonb_path_ops"},
                        if_not_exists=True)
        op.create_index("idx_enterprise_artifacts_source_url",
                        "enterprise_artifacts", ["source_url"],
                        postgresql_where=sa.text("source_url IS NOT NULL"),
                        postgresql_concurrently=True, if_not_exists=True)

    # 2. artifact_versions
    if "artifact_versions" not in existing:
        op.create_table(
            "artifact_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("markdown_payload", sa.Text(), nullable=False),
            sa.Column("version_label", sa.String(50), nullable=True),
            sa.Column("commit_sha", sa.String(40), nullable=True),
            sa.Column("created_by", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(
                ["artifact_id"], ["enterprise_artifacts.id"],
                name="fk_artifact_versions_artifact_id",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("content_hash",
                                name="uq_artifact_versions_content_hash"),
            sa.CheckConstraint("length(content_hash) = 64",
                               name="ck_artifact_versions_content_hash_length"),
            sa.CheckConstraint("commit_sha IS NULL OR length(commit_sha) = 40",
                               name="ck_artifact_versions_commit_sha_length"),
        )
        op.create_index("idx_artifact_versions_artifact_created",
                        "artifact_versions", ["artifact_id", "created_at"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_artifact_versions_tenant_created",
                        "artifact_versions", ["tenant_id", "created_at"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_artifact_versions_commit_sha",
                        "artifact_versions", ["commit_sha"],
                        postgresql_where=sa.text("commit_sha IS NOT NULL"),
                        postgresql_concurrently=True, if_not_exists=True)

    # 3. enterprise_collections
    if "enterprise_collections" not in existing:
        op.create_table(
            "enterprise_collections",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_by", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_id", "name",
                                name="uq_enterprise_collections_tenant_name"),
            sa.CheckConstraint("length(name) > 0 AND length(name) <= 255",
                               name="ck_enterprise_collections_name_length"),
        )
        op.create_index("idx_enterprise_collections_tenant_id",
                        "enterprise_collections", ["tenant_id"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_enterprise_collections_tenant_name",
                        "enterprise_collections", ["tenant_id", "name"],
                        postgresql_concurrently=True, if_not_exists=True)
        # Partial index for default collection lookup
        op.create_index("idx_enterprise_collections_tenant_default",
                        "enterprise_collections", ["tenant_id", "is_default"],
                        postgresql_where=sa.text("is_default = TRUE"),
                        if_not_exists=True)

    # 4. enterprise_collection_artifacts
    if "enterprise_collection_artifacts" not in existing:
        op.create_table(
            "enterprise_collection_artifacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("added_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(
                ["collection_id"], ["enterprise_collections.id"],
                name="fk_eca_collection_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["artifact_id"], ["enterprise_artifacts.id"],
                name="fk_eca_artifact_id",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("collection_id", "artifact_id",
                                name="uq_eca_collection_artifact"),
            sa.CheckConstraint("order_index >= 0",
                               name="ck_eca_order_index"),
        )
        op.create_index("idx_eca_collection_order",
                        "enterprise_collection_artifacts",
                        ["collection_id", "order_index"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_eca_artifact_id",
                        "enterprise_collection_artifacts", ["artifact_id"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_eca_tenant_id",
                        "enterprise_collection_artifacts", ["tenant_id"],
                        postgresql_concurrently=True, if_not_exists=True)
        op.create_index("idx_eca_collection_tenant_order",
                        "enterprise_collection_artifacts",
                        ["collection_id", "tenant_id", "order_index"],
                        postgresql_concurrently=True, if_not_exists=True)
```

**Downgrade strategy:**

Drop tables in reverse FK dependency order. Indexes are dropped automatically with their tables in PostgreSQL.

```python
def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # No-op on SQLite

    op.drop_table("enterprise_collection_artifacts")
    op.drop_table("enterprise_collections")
    op.drop_table("artifact_versions")
    op.drop_table("enterprise_artifacts")
```

### 9.3 ENT-1.8: Tenant Columns on Shared Tables

**File:** `skillmeat/cache/migrations/versions/20260306_1300_add_tenant_columns_shared_tables.py`

**Revision chain:**
```python
revision = "20260306_1300_add_tenant_columns_shared_tables"
down_revision = "20260306_1200_create_enterprise_schema"
branch_labels = None
depends_on = None
```

Based on the analysis in Section 7.1, the only shared table requiring a `tenant_id` column in Phase 1 is `collections` (if it will be surfaced in enterprise mode). This migration is deliberately narrow.

**Upgrade strategy:**

```python
def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # Add tenant_id to shared collections table for PostgreSQL deployments.
        # Column is nullable: NULL means "local-mode entry, not tenant-scoped".
        # On SQLite this column is not added (SQLite deployments do not use tenant_id).
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("collections")}

        if "tenant_id" not in existing_cols:
            op.add_column(
                "collections",
                sa.Column("tenant_id", sa.String(36), nullable=True,
                          comment="Enterprise tenant UUID; NULL for local-mode collections"),
            )
            # Backfill with DEFAULT_TENANT_ID for any existing rows
            # (ensures existing data is usable in enterprise context)
            op.execute(sa.text(
                "UPDATE collections "
                "SET tenant_id = '00000000-0000-4000-a000-000000000001' "
                "WHERE tenant_id IS NULL"
            ))
            op.create_index(
                "idx_collections_tenant_id",
                "collections",
                ["tenant_id"],
                postgresql_concurrently=True,
                if_not_exists=True,
            )
    else:
        # SQLite: no tenant_id on shared tables. Local mode is single-user.
        import logging
        logging.getLogger(__name__).info(
            "Skipping tenant column additions on SQLite (local mode)."
        )
```

**Downgrade strategy:**

```python
def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("collections")}

    if "tenant_id" in existing_cols:
        op.drop_index("idx_collections_tenant_id", table_name="collections",
                      if_exists=True)
        with op.batch_alter_table("collections") as batch_op:
            batch_op.drop_column("tenant_id")
```

### 9.4 Running Migrations

**Local development (SQLite):**
```bash
# Enterprise migrations are no-ops on SQLite
alembic upgrade head
```

**Enterprise (PostgreSQL):**
```bash
export DATABASE_URL="postgresql://skillmeat:pass@localhost/skillmeat"
alembic upgrade head
# Creates all tables including enterprise schema
```

**Rollback one step:**
```bash
alembic downgrade -1
```

**Rollback enterprise schema only:**
```bash
alembic downgrade 20260303_1100_add_workflow_to_artifact_type_check
# Downgrades through both ENT-1.8 and ENT-1.7
```

**Check current revision:**
```bash
alembic current
alembic history --verbose
```

### 9.5 env.py Changes Required

The Alembic `env.py` currently hard-codes SQLite connection settings (`PRAGMA`, `render_as_batch=True`, `NullPool`). For PostgreSQL connectivity, the following changes are needed in ENT-1.9 (database connection factory) and `env.py` update:

```python
# In run_migrations_online(), after resolving db_url:
if db_url and db_url.startswith("postgresql"):
    # PostgreSQL: use QueuePool, no render_as_batch
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.QueuePool,
        pool_pre_ping=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,  # Not needed for PostgreSQL
        )
        with context.begin_transaction():
            context.run_migrations()
else:
    # SQLite: existing path unchanged
    ...
```

---

## 10. Design Decisions and Rationale

### Decision 1: UUID Primary Keys (not TEXT or Integer)

**Choice:** UUID (`gen_random_uuid()`) for all enterprise table PKs.

**Rationale:**
- The existing local-mode `artifacts` table uses TEXT PKs (`type:name` composite strings). These are not globally unique and cannot be used across tenants.
- UUID PKs enable distributed ID generation (no coordination needed for inserts from multiple API instances).
- UUIDs are the standard for multi-tenant SaaS; they prevent enumeration attacks (IDs are not sequential).
- `gen_random_uuid()` is built into PostgreSQL 13+; no UUID extension required.

**Trade-off:** UUIDs are larger than integers (16 bytes vs 4/8 bytes) and slightly slower for B-tree index lookups. Acceptable for the expected scale (<10M rows per tenant in Phase 1).

### Decision 2: JSONB for tags and custom_fields

**Choice:** JSONB columns for `tags` (array) and `custom_fields` (object) on `enterprise_artifacts`.

**Rationale:**
- Tags require flexible, schema-less extensibility without a separate tag join table.
- GIN indexing on JSONB enables efficient containment queries (`@>`).
- JSONB is stored as binary (faster than JSON text parsing on read).
- `custom_fields` allows consumers to attach arbitrary metadata without schema migrations.

**Trade-off:** JSONB queries are less type-safe than relational columns. For the MVP tag volume, a separate normalized `tags` table would be over-engineered. This can be normalized later if query patterns require it.

### Decision 3: Denormalized tenant_id in Child Tables

**Choice:** `tenant_id` is present in `artifact_versions` and `enterprise_collection_artifacts` as a denormalized copy.

**Rationale:**
- Queries like "get all recent versions for this tenant" would require a join through `enterprise_artifacts` without denormalization.
- Adding `tenant_id` to child tables avoids this join in hot query paths.
- The tenant_id is always known at write time (from the parent artifact/collection).

**Trade-off:** Application layer must validate that child `tenant_id` matches parent `tenant_id` on insert. A future database trigger can enforce this if drift is detected.

### Decision 4: Parallel Tables, Not Schema Extension

**Choice:** New `enterprise_*` tables in the same schema rather than altering existing `artifacts` and `collections` tables.

**Rationale:** Documented in Section 7.2. Preserves full backward compatibility with SQLite local mode. Existing `artifacts` table uses a TEXT PK (`type:name`) that is incompatible with UUID FKs required by enterprise joins.

### Decision 5: Application-Enforced Tenant Isolation (not RLS)

**Choice:** WHERE clause filtering in all queries; no PostgreSQL RLS in Phase 1.

**Rationale:** Documented in Section 6.6. RLS migration path is documented for future adoption when scale and security requirements justify the operational overhead.

### Decision 6: Unique content_hash Across All Tenants

**Choice:** The `uq_artifact_versions_content_hash` constraint is global (not per-tenant).

**Rationale:**
- Content-based deduplication works globally: two tenants with the same artifact content share one version row.
- This reduces storage and enables efficient cross-tenant similarity queries (future feature).
- Privacy implication: content hashes leak whether two tenants have the same artifact. For Phase 1 (single-tenant enterprise), this is acceptable. Multi-tenant evaluation may require per-tenant scoping of `content_hash` uniqueness.

**Future consideration:** If multi-tenant privacy requires isolation, change the constraint to `UNIQUE (tenant_id, content_hash)` and duplicate the `markdown_payload` rows. The index and constraint rename would be a simple migration.

### Decision 7: is_default Enforced at Application Layer

**Choice:** No `UNIQUE` partial index on `(tenant_id) WHERE is_default = TRUE`.

**Rationale:** While PostgreSQL supports this pattern, enforcing it at the database level requires a partial unique index that can cause confusing constraint violation errors when swapping the default collection (would need to clear the old default in the same transaction). Enforcing at the repository layer (`set_default` method uses `UPDATE ... SET is_default = FALSE WHERE tenant_id = ? ... then UPDATE ... SET is_default = TRUE WHERE id = ?` in a single transaction) is simpler and testable. A database-level CHECK would be added in a later phase if drift is detected in testing.

---

## Appendix A: Prerequisite Checklist for ENT-1.2

Before implementing ENT-1.2 (creating the first enterprise table), verify:

- [ ] PostgreSQL 15+ instance available (local docker-compose or managed service)
- [ ] `sqlalchemy[asyncio]` and `asyncpg` (or `psycopg2`) added to dependencies
- [ ] `SKILLMEAT_DATABASE_URL` or `DATABASE_URL` env var resolves to PostgreSQL
- [ ] `alembic upgrade head` runs clean on SQLite (baseline check)
- [ ] `skillmeat/cache/models/enterprise_artifacts.py` file created (empty)
- [ ] `skillmeat/cache/models/enterprise_collections.py` file created (empty)
- [ ] `skillmeat/cache/models/enterprise_schema.py` file created with `DEFAULT_TENANT_ID`

## Appendix B: Column Type Cross-Reference (SQLite vs PostgreSQL)

| Concept | SQLite type (existing) | PostgreSQL type (enterprise) |
|---------|----------------------|------------------------------|
| UUID identifier | `TEXT` (UUID hex string) | `UUID` (native 16-byte type) |
| JSON data | `JSON` (text-stored) | `JSONB` (binary, GIN-indexable) |
| Timestamp | `TIMESTAMP` (naive UTC) | `TIMESTAMP WITH TIME ZONE` |
| Text content | `TEXT` | `TEXT` (same; no limit) |
| Boolean | `BOOLEAN` (stored as 0/1) | `BOOLEAN` (native) |
| String with limit | `String(N)` | `VARCHAR(N)` (same) |
| Auto-generate UUID | `default=lambda: uuid.uuid4().hex` | `DEFAULT gen_random_uuid()` |
