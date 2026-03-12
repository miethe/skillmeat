---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-repo-parity
feature_slug: enterprise-repo-parity
phase: 2
phase_title: "Enterprise Models & Migration"
status: pending
created: 2026-03-12
updated: 2026-03-12
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
commit_refs: []
pr_refs: []

owners: ["data-layer-expert"]
contributors: ["backend-architect"]

tasks:
  - id: "ENT2-2.1"
    title: "Enterprise models for tags, groups, settings"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
  - id: "ENT2-2.2"
    title: "Enterprise models for context entities"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
  - id: "ENT2-2.3"
    title: "Enterprise models for projects and deployments"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
  - id: "ENT2-2.4"
    title: "Enterprise models for marketplace sources"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
  - id: "ENT2-2.5"
    title: "Generate Alembic migration for all enterprise models"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["ENT2-2.1", "ENT2-2.2", "ENT2-2.3", "ENT2-2.4"]
  - id: "ENT2-2.6"
    title: "Validate migration on PostgreSQL"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["ENT2-2.5"]

parallelization:
  batch_1: ["ENT2-2.1", "ENT2-2.2", "ENT2-2.3", "ENT2-2.4"]
  batch_2: ["ENT2-2.5"]
  batch_3: ["ENT2-2.6"]
---

# Phase 2: Enterprise Models & Migration

Define all ORM models for enterprise deployment, then generate and validate Alembic migration.

## Quick Reference

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-repo-parity/phase-2-progress.md \
  -t ENT2-2.1 -s completed
```

## Phase Overview

Phase 2 models foundation for all enterprise repositories. Based on Phase 1 triage, data-layer-expert defines enterprise models in `skillmeat/cache/models_enterprise.py` using SQLAlchemy 2.x patterns and UUID PKs. After all models are defined, an Alembic migration is generated and validated against a real PostgreSQL instance to ensure schema integrity.

Key constraints:
- All models inherit from `EnterpriseBase` (UUID PKs, tenant isolation metadata)
- Soft deletes via `deleted_at` timestamp where applicable
- Foreign key relationships via `artifact_uuid` (stable identity per ADR-007)
- `_apply_tenant_filter()` method on each model class for query scoping
