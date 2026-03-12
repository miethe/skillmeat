---
type: context
schema_version: 2
doc_type: context
prd: enterprise-repo-parity
feature_slug: enterprise-repo-parity
created: 2026-03-12
updated: 2026-03-12
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
---

# Enterprise Repository Parity v2 - Context

## Overview

Complete enterprise repository parity for all DI-routed repository interfaces. The goal is to eliminate SQLite-only implementations by providing PostgreSQL-backed enterprise repositories for all 8 repository interfaces used in local mode, ensuring data resilience and multi-tenant support in enterprise deployments.

## Key Decisions

**Phase 1: Triage & Classify**
- All 8 repository interfaces read and classified by implementation pattern
- Classification gates all subsequent implementation work:
  - **Full**: Complete local implementation, must be ported to enterprise
  - **Passthrough**: Local implementation delegates to another repo (no new code)
  - **Stub**: Minimal local implementation (mostly empty), enterprise stub acceptable
  - **Excluded**: Already enterprise-ready or not applicable

**Serialized Execution**
- Phases execute sequentially (Phase 1 triage → Phase 2 models → Phases 3-4-5 repositories → Phase 6 wiring → Phase 7 tests)
- Triage output directly informs task scope and dependency structure in subsequent phases

## Architecture Constraints

### SQLAlchemy 2.x Pattern
- Enterprise repositories use `select()` style (SQLAlchemy 2.x)
- Local repositories use `session.query()` style (SQLAlchemy 1.x fallback)
- No bridge code—intentional pattern divergence per ADR

### Entity Design
- All enterprise models inherit from `EnterpriseBase` (UUID PKs, tenant isolation)
- UUID primary keys instead of surrogate integers
- Tenant isolation via `_apply_tenant_filter(query, tenant_id)` method on each repo class
- Soft deletes where applicable (e.g., artifacts marked `deleted_at` instead of removed)

### Tenant Isolation
- Every query must include `_apply_tenant_filter()` to scope results to current tenant
- Join tables use `artifact_uuid` (stable ADR-007 identity) for FK references
- Session scoping: one session per HTTP request context (injected via FastAPI dependencies)

## Key Files

### Models & Data Layer
- `skillmeat/cache/models_enterprise.py` — Enterprise ORM model definitions
- `skillmeat/cache/models.py` — Local ORM models (1.x style)
- `skillmeat/cache/migrations/versions/` — Alembic migrations (both local and enterprise)

### Repository Interfaces & Implementations
- `skillmeat/cache/repositories.py` — Local repository implementations (query() style)
- `skillmeat/cache/enterprise_repositories.py` — Enterprise repository implementations (select() style)
- `skillmeat/cache/repository_factory.py` — DI provider that routes local/enterprise at instantiation

### Dependency Injection
- `skillmeat/api/dependencies.py` — Repository providers, tenant context injection
- `skillmeat/cache/models.py` — `get_session()` factory (returns local or enterprise SessionLocal)

### API Integration
- `skillmeat/api/routers/*.py` — API endpoints that consume repositories via DI

## Repository Interfaces to Port

1. **TagRepository** — Artifact tag management
2. **GroupRepository** — Artifact group management
3. **SettingsRepository** — User/tenant settings storage
4. **ContextEntityRepository** — MCP server and context entity storage
5. **ProjectRepository** — Project metadata
6. **DeploymentRepository** — Artifact deployment records
7. **DeploymentSetRepository** — Logical groupings of deployments
8. **DeploymentProfileRepository** — Deployment configuration profiles
9. **MarketplaceSourceRepository** — Marketplace source configuration
10. **ProjectTemplateRepository** — Project template scaffolding (stub only)
11. **DbCollectionArtifactRepository** — Collection/artifact associations (wiring only)
12. **DbArtifactHistoryRepository** — Artifact version history (wiring only)
13. **DuplicatePairRepository** — Duplicate artifact detection (wiring only)
14. **MarketplaceSourceRepository (concrete)** — Edition-aware wiring (Phase 6)

## Phase Breakdown

| Phase | Focus | Key Output |
|-------|-------|-----------|
| **Phase 1** | Triage & classify all 8 interfaces | Classification document |
| **Phase 2** | Define enterprise models for all entities | `models_enterprise.py` + Alembic migration |
| **Phase 3-4** | Implement tag/group/settings + project/deployment repos | 8 enterprise repository classes |
| **Phase 5** | Implement marketplace source + stub template repo | 2 enterprise repository classes |
| **Phase 6** | Wire edition-aware providers for all 8 repos + audit SQLite references | Updated `repository_factory.py` + grep audit |
| **Phase 7** | Full test coverage: local, PostgreSQL, tenant isolation | Passing test suite |

## Quick Reference

**View PRD**: `docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md`

**View Implementation Plan**: `docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md`

**Check progress**: `ls -d .claude/progress/enterprise-repo-parity/phase-*-progress.md`

**Update task status**:
```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-repo-parity/phase-N-progress.md \
  -t ENT2-N.X -s completed
```

**Batch update**:
```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/enterprise-repo-parity/phase-N-progress.md \
  --updates "ENT2-N.1:completed,ENT2-N.2:completed"
```
