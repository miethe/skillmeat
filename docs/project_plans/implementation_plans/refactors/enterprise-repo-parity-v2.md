---
title: "Implementation Plan: Enterprise Repository Parity v2"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-03-12
updated: 2026-03-12
feature_slug: enterprise-repo-parity
feature_version: v2
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: null
scope: Implement enterprise repository parity for all DI-routed interfaces and edition-aware non-DI repositories
effort_estimate: 55-70 story points
architecture_summary: Enterprise repository implementations following EnterpriseRepositoryBase pattern with tenant isolation, new Alembic migrations, and edition-aware DI wiring
related_documents:
  - docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
  - docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
  - .claude/findings/ENTERPRISE_503_REPOSITORY_GAPS.md
owner: python-backend-engineer
contributors:
  - data-layer-expert
  - backend-architect
  - senior-code-reviewer
priority: high
risk_level: medium
category: product-planning
tags:
  - enterprise
  - repository
  - postgresql
  - parity
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - skillmeat/api/dependencies.py
  - skillmeat/api/server.py
  - skillmeat/cache/enterprise_repositories.py
  - skillmeat/cache/models_enterprise.py
  - skillmeat/cache/migrations/versions/
  - skillmeat/cache/repositories.py
---

# Implementation Plan: Enterprise Repository Parity v2

## Executive Summary

This plan delivers the complete set of enterprise repository implementations needed for full feature parity in `SKILLMEAT_EDITION=enterprise`. Enterprise-db-storage-v1 implemented `EnterpriseArtifactRepository`, `EnterpriseCollectionRepository`, `EnterpriseUserCollectionAdapter`, and `EnterpriseMembershipRepository`. Eight DI-routed interfaces remain as HTTP 503 stubs, and eight non-DI repositories silently write to SQLite in enterprise mode, creating split-brain state in any PostgreSQL-backed deployment.

**Key Outcomes:**
- Zero HTTP 503 responses caused by missing repository implementations in enterprise mode
- All non-DI repositories are edition-aware; no SQLite writes occur when `SKILLMEAT_EDITION=enterprise`
- Enterprise mode is viable for production PostgreSQL deployment without workarounds
- Linear Alembic migration history maintained; `alembic heads` remains exactly 1

**Complexity:** Large | **Phases:** 7 | **Estimated Timeline:** 4-6 weeks | **Effort:** 55-70 story points

---

## Implementation Strategy

### Architecture Sequencing

This plan follows the standard MeatyPrompts layered architecture: schema first, then repositories, then DI wiring. Each phase gates the next — no repository implementation begins before its schema is validated.

```
Phase 1 (Triage) → Phase 2 (Schema) → Phases 3-4 (Core Repos) → Phases 5-6 (Remaining Repos) → Phase 7 (Testing)
```

### Parallelization Opportunities

| Window | Parallel Work |
|--------|---------------|
| Phase 3-4 preparation | After Phase 2 schema is merged, Phases 3 and 4 can proceed simultaneously since they target different repository classes |
| Phase 5-6 preparation | Phases 5 and 6 can proceed in parallel after Phases 3-4 complete |
| Phase 7 | All test tasks are sequential by design (local mode first, then enterprise integration) |

### Architecture Invariants (from enterprise-db-storage-v1)

All new enterprise repositories MUST follow:
- SQLAlchemy 2.x `select()` style — never `session.query()`
- `EnterpriseBase` declarative base — never `Base` from `models.py`
- UUID primary keys on all enterprise models — no integer PKs
- `tenant_id UUID NOT NULL` on every new table, indexed
- `_apply_tenant_filter()` called on every query — no exceptions
- Injected `Session` via FastAPI DI — no direct session management
- Edition routing via `APISettings.edition == "enterprise"` — the only branch condition

### Critical Path

```
Phase 1 (Triage) → Phase 2 (Schema + migration) → Phase 3 (DI wiring for core repos) → Phase 7 (Validation)
```

Phase 4, 5, and 6 are parallel to Phase 3 after Phase 2 completes. Phase 7 requires all prior phases.

---

## Phase Overview

| Phase | Title | Effort | Duration | Phase File |
|-------|-------|--------|----------|------------|
| 1 | Triage & Classify | 8 pts | 1-2 days | [phase-1-triage.md](./enterprise-repo-parity-v2/phase-1-triage.md) |
| 2 | Schema Additions | 13 pts | 2-3 days | [phase-2-schema.md](./enterprise-repo-parity-v2/phase-2-schema.md) |
| 3-4 | Core Repositories (Tag/Group/Settings/ContextEntity + Project/Deployment) | 20 pts | 3-5 days | [phase-3-4-core-repos.md](./enterprise-repo-parity-v2/phase-3-4-core-repos.md) |
| 5-6 | Marketplace/Template + Non-DI Repo Migration | 14 pts | 3-4 days | [phase-5-6-marketplace-nondi.md](./enterprise-repo-parity-v2/phase-5-6-marketplace-nondi.md) |
| 7 | Testing & Validation | 9-10 pts | 2-3 days | [phase-7-testing.md](./enterprise-repo-parity-v2/phase-7-testing.md) |

**Total estimate:** 64-65 story points (range: 55-70 accounting for triage classification outcomes)

---

## Repository Gap Summary

### Group A — DI-Routed, Returning HTTP 503

| Interface | DI Provider | Affected Endpoints | Phase |
|-----------|-------------|-------------------|-------|
| `ITagRepository` | `get_tag_repository` | `/api/v1/tags` | 3 |
| `IGroupRepository` | `get_group_repository` | `/api/v1/groups` | 3 |
| `ISettingsRepository` | `get_settings_repository` | `/api/v1/settings` | 3 |
| `IContextEntityRepository` | `get_context_entity_repository` | `/api/v1/context-entities` | 3 |
| `IProjectRepository` | `get_project_repository` | `/api/v1/projects` | 4 |
| `IDeploymentRepository` | `get_deployment_repository` | `/api/v1/deployments` | 4 |
| `IMarketplaceSourceRepository` | `get_marketplace_source_repository` | `/api/v1/marketplace-sources` | 5 |
| `IProjectTemplateRepository` | `get_project_template_repository` | `/api/v1/project-templates` | 5 |

### Group B — Non-DI, Silently Using SQLite

| Concrete Class | Affected Endpoints | Phase |
|----------------|--------------------|-------|
| `DeploymentSetRepository` | `/api/v1/deployment-sets` | 4 |
| `DeploymentProfileRepository` | `/api/v1/deployment-profiles` | 4 |
| `MarketplaceCatalogRepository` | `/api/v1/marketplace-catalog` | 5 |
| `MarketplaceTransactionHandler` | `/api/v1/marketplace` (transactions) | 5 |
| `DbCollectionArtifactRepository` | `/api/v1/collections`, `/api/v1/artifacts` (join ops) | 6 |
| `DbArtifactHistoryRepository` | `/api/v1/artifact-history` | 6 |
| `DuplicatePairRepository` | `/api/v1/match` (dedup) | 6 |
| `MarketplaceSourceRepository` (concrete) | `/api/v1/marketplace-sources` (concrete path) | 6 |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `IProjectRepository` filesystem path conflict | Medium | High | Phase 1 triage must produce explicit decision: enterprise projects store path as nullable metadata, not live filesystem reference |
| Alembic branch head introduced | Medium | Medium | Each migration in Phase 2 explicitly sets `down_revision` to current head; verify with `alembic heads` before merge |
| Over-scoping Full-tier repos | Medium | Medium | Phase 1 triage is a binding gate; classify strictly per PRD tier definitions |
| SQLAlchemy comparator cache poisoning in tests | Low | Medium | Use `MagicMock(spec=Session)` exclusively; never SQLite shims for enterprise repos |
| `session.query()` style accidentally used | Low | Medium | PR review checklist in Phase 7; `senior-code-reviewer` checks all new enterprise repos |
| Non-DI changes break local mode | Low | High | Local mode smoke test is part of Phase 7 exit criteria |

---

## Quality Gates

| Phase | Gate | Verification |
|-------|------|-------------|
| 1 | Triage document approved by `backend-architect` | Review sign-off |
| 2 | `alembic upgrade head` completes on fresh PostgreSQL; `alembic heads` = 1 | `docker compose` CI |
| 3-4 | Target endpoints return HTTP 200 in enterprise mode | Integration smoke test |
| 5-6 | `grep` audit finds zero hardcoded SQLite instantiations without edition check in `dependencies.py` | Automated grep |
| 7 | Full `pytest` suite passes in both local and enterprise modes; tenant isolation confirmed | CI matrix |

---

## Acceptance Criteria Summary

| ID | Criterion |
|:--:|-----------|
| AC-1 | All 8 previously-503 endpoint groups return HTTP 200 in enterprise mode |
| AC-2 | No SQLite or `db_path` references execute when `SKILLMEAT_EDITION=enterprise` |
| AC-3 | Tenant A cannot retrieve data created by tenant B (all new repos) |
| AC-4 | `alembic upgrade head` completes cleanly from fresh schema |
| AC-5 | `alembic heads` outputs exactly 1 revision after all Phase 2 migrations |
| AC-6 | All new enterprise repository classes have >= 80% line coverage |
| AC-7 | Local mode produces zero regressions |
| AC-8 | All new enterprise models inherit `EnterpriseBase`; no `Base` from `models.py` |
| AC-9 | `IProjectTemplateRepository` returns HTTP 200 with empty list (not 503) |
| AC-10 | Excluded-tier routers return HTTP 404 with descriptive message, not 503 |
