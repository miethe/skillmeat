---
title: "Phase 2: Schema Additions"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-12
updated: 2026-03-12
feature_slug: enterprise-repo-parity
feature_version: v2
phase: 2
phase_title: Schema Additions
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
entry_criteria:
  - Phase 1 triage document approved by backend-architect
  - All Full-tier items have schema sketches in the triage document
  - Current Alembic head confirmed (run `alembic heads` to verify single head)
exit_criteria:
  - All new enterprise SQLAlchemy models added to `skillmeat/cache/models_enterprise.py`
  - All new models inherit `EnterpriseBase`, have UUID PK, `tenant_id UUID NOT NULL`, indexed
  - Single Alembic migration file created appending to current head
  - `alembic upgrade head` completes without error on fresh PostgreSQL
  - `alembic heads` shows exactly 1 head after migration applied
  - All new models importable without errors (`python -c "from skillmeat.cache.models_enterprise import *"`)
  - backend-architect validates migration runs on docker-compose enterprise profile
---

# Phase 2: Schema Additions

## Overview

**Duration:** 2-3 days | **Effort:** 13 story points | **Subagents:** `data-layer-expert`, `backend-architect`

This phase creates all enterprise SQLAlchemy models and the Alembic migration for domains identified as Full-tier in Phase 1. No repository classes are written in this phase — only model definitions and the migration. This separation ensures that Phase 3-4-5 repository authors have stable, reviewed model targets to import.

**Key constraint:** A single Alembic migration file (`ent_008_*`) covers all new tables from this phase. This keeps the migration history linear. If domains are added to scope after this migration is merged, a separate `ent_009_*` migration is required — do not amend `ent_008_*`.

---

## Schema Design Invariants

Every new enterprise model MUST satisfy:

```python
from skillmeat.cache.models_enterprise import EnterpriseBase
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UUID as SA_UUID, String, Boolean, DateTime, func

class EnterpriseExampleModel(EnterpriseBase):
    __tablename__ = "enterprise_examples"

    id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True), nullable=False, index=True
    )
    # ... domain columns ...
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

**Checklist per model:**
- [ ] Inherits `EnterpriseBase` (NOT `Base` from `models.py`)
- [ ] `id: uuid.UUID` primary key with `default=uuid.uuid4`
- [ ] `tenant_id: uuid.UUID` column, `nullable=False`, `index=True`
- [ ] `created_at` / `updated_at` with timezone-aware `DateTime`
- [ ] Table name prefixed `enterprise_`

---

## Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-2.1 | Core domain models: tags and groups | Add `EnterpriseTag` and `EnterpriseGroup` models to `models_enterprise.py`; tags: id, tenant_id, name, color (nullable), description (nullable), created_at, updated_at; groups: id, tenant_id, name, description (nullable), is_default, created_at, updated_at | Both models importable; all invariant checklist items satisfied; no reference to `Base` from `models.py` | 2 pts | data-layer-expert | Phase 1 approved | `skillmeat/cache/models_enterprise.py` |
| ENT2-2.2 | Settings domain model | Add `EnterpriseSettings` model; columns: id, tenant_id, key (String, not-null), value (Text, nullable), is_encrypted (Boolean, default False), created_at, updated_at; add unique constraint on `(tenant_id, key)` | Model importable; unique constraint defined in `__table_args__`; all invariant checklist items satisfied | 2 pts | data-layer-expert | Phase 1 approved | `skillmeat/cache/models_enterprise.py` |
| ENT2-2.3 | Context entity domain model | Add `EnterpriseContextEntity` model; columns: id, tenant_id, name, entity_type (String), content (Text, nullable), metadata (JSONB, nullable), artifact_id (UUID FK nullable → enterprise_artifacts.id), created_at, updated_at | Model importable; JSONB column uses `postgresql.JSONB`; FK to enterprise_artifacts is nullable; all invariant checklist items satisfied | 2 pts | data-layer-expert | Phase 1 approved | `skillmeat/cache/models_enterprise.py` |
| ENT2-2.4 | Project domain model | Add `EnterpriseProject` model; columns: id, tenant_id, name, description (nullable), filesystem_path (String, nullable — informational only in enterprise mode), metadata (JSONB, nullable), is_active (Boolean, default True), created_at, updated_at | Model importable; `filesystem_path` is explicitly nullable (enterprise projects are DB records); all invariant checklist items satisfied | 2 pts | data-layer-expert | Phase 1 approved + OQ-1 answer | `skillmeat/cache/models_enterprise.py` |
| ENT2-2.5 | Deployment domain models | Add `EnterpriseDeployment`, `EnterpriseDeploymentSet`, `EnterpriseDeploymentProfile` models; deployment: id, tenant_id, project_id (UUID FK → enterprise_projects.id, nullable), artifact_id (UUID FK → enterprise_artifacts.id, nullable), status (String), deployed_at (DateTime nullable), metadata (JSONB nullable), created_at, updated_at; deployment_set: id, tenant_id, name, description (nullable), created_at, updated_at; deployment_profile: id, tenant_id, name, config (JSONB, not-null), set_id (UUID FK → enterprise_deployment_sets.id, nullable), created_at, updated_at | All three models importable; FK relationships defined; all invariant checklist items satisfied per model | 3 pts | data-layer-expert | ENT2-2.4 | `skillmeat/cache/models_enterprise.py` |
| ENT2-2.6 | Marketplace source domain model | Add `EnterpriseMarketplaceSource` model; columns: id, tenant_id, name, url (String, not-null), source_type (String), is_enabled (Boolean, default True), config (JSONB, nullable), created_at, updated_at | Model importable; all invariant checklist items satisfied | 1 pt | data-layer-expert | Phase 1 approved | `skillmeat/cache/models_enterprise.py` |
| ENT2-2.7 | Generate Alembic migration | Generate a single Alembic migration file named `ent_008_add_enterprise_parity_tables.py`; migration must: identify current head via `alembic heads`, set `down_revision` to that head, create all new tables from ENT2-2.1 through ENT2-2.6 in dependency order (projects before deployments), include proper `upgrade()` and `downgrade()` functions | Migration file exists at `skillmeat/cache/migrations/versions/ent_008_add_enterprise_parity_tables.py`; `down_revision` matches output of `alembic heads` before this migration; file parses without import errors | 2 pts | data-layer-expert | ENT2-2.1 through ENT2-2.6 | `skillmeat/cache/migrations/versions/ent_008_add_enterprise_parity_tables.py` |
| ENT2-2.8 | Validate migration on PostgreSQL | Run `alembic upgrade head` against a fresh PostgreSQL via docker-compose enterprise profile; verify `alembic heads` shows exactly 1 head; verify all new tables exist with correct columns and indexes | `alembic upgrade head` exits 0; `alembic heads` shows 1 revision; `psql \dt enterprise_*` shows all 8+ new tables; `tenant_id` index confirmed on each table | 1 pt | backend-architect | ENT2-2.7 | docker-compose enterprise profile |

---

## Parallelization Strategy

ENT2-2.1, ENT2-2.2, ENT2-2.3, and ENT2-2.6 are independent — they touch only `models_enterprise.py` but add non-conflicting model classes. These can be done as a serial batch by a single `data-layer-expert` agent (since all edits target one file, use sequential edits not parallel agents).

ENT2-2.4 must precede ENT2-2.5 (deployment models FK to project model).

ENT2-2.7 requires all model additions complete.

ENT2-2.8 requires ENT2-2.7 complete.

**Recommended execution order (single agent, sequential):**
1. ENT2-2.1 → ENT2-2.2 → ENT2-2.3 → ENT2-2.4 → ENT2-2.5 → ENT2-2.6 (all in `models_enterprise.py`)
2. ENT2-2.7 (generate migration after all models exist)
3. ENT2-2.8 (validation — `backend-architect`)

---

## Expected New Tables

Based on proposed Full-tier classifications (subject to Phase 1 output):

| Table | Domain | Key Columns | FK Dependencies |
|-------|--------|-------------|-----------------|
| `enterprise_tags` | Tags | id, tenant_id, name, color | None |
| `enterprise_groups` | Groups | id, tenant_id, name, is_default | None |
| `enterprise_settings` | Settings | id, tenant_id, key, value | Unique (tenant_id, key) |
| `enterprise_context_entities` | Context | id, tenant_id, name, entity_type, content, artifact_id | → enterprise_artifacts (nullable) |
| `enterprise_projects` | Projects | id, tenant_id, name, filesystem_path | None |
| `enterprise_deployments` | Deployments | id, tenant_id, project_id, artifact_id, status | → enterprise_projects, enterprise_artifacts |
| `enterprise_deployment_sets` | Deployment Sets | id, tenant_id, name | None |
| `enterprise_deployment_profiles` | Deployment Profiles | id, tenant_id, name, config, set_id | → enterprise_deployment_sets |
| `enterprise_marketplace_sources` | Marketplace | id, tenant_id, name, url, source_type | None |

**Note:** If Phase 1 triage reclassifies any item as Stub or Passthrough, remove its table from ENT2-2.7. Update this table accordingly.

---

## Key Files

| File | Role |
|------|------|
| `skillmeat/cache/models_enterprise.py` | Target file for all new model additions |
| `skillmeat/cache/migrations/versions/` | Target directory for `ent_008_*` migration |
| `skillmeat/cache/migrations/env.py` | Alembic environment; verify `EnterpriseBase.metadata` is included |
| `skillmeat/cache/enterprise_repositories.py` | Reference: existing models pattern (how v1 models were defined) |
| `.claude/findings/ENT2_TRIAGE.md` | Input: Phase 1 output specifying Full-tier domains |

---

## Quality Gate

Phase 3-4 is blocked until:

1. All Full-tier domain models added to `models_enterprise.py` and pass import check
2. `ent_008_add_enterprise_parity_tables.py` migration file exists
3. `alembic upgrade head` exits 0 on fresh PostgreSQL
4. `alembic heads` shows exactly 1 head
5. ENT2-2.8 backend-architect sign-off

---

**Parent plan:** [enterprise-repo-parity-v2.md](../enterprise-repo-parity-v2.md)
**Previous phase:** [phase-1-triage.md](./phase-1-triage.md)
**Next phase:** [phase-3-4-core-repos.md](./phase-3-4-core-repos.md)
