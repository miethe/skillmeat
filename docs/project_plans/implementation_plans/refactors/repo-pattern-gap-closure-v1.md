---
schema_version: 2
doc_type: implementation_plan
title: 'Implementation Plan: Repository Pattern Gap Closure'
status: draft
created: 2026-03-04
updated: '2026-03-04'
feature_slug: repo-pattern-gap-closure
feature_version: v1
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: null
scope: Close all remaining direct data access gaps in API routers to fully abstract
  behind repository interfaces, enabling enterprise-db-storage refactor
effort_estimate: 38 pts
architecture_summary: Extend existing 6 ABCs with missing methods, create 4 new domain
  ABCs (Group, ContextEntity, MarketplaceSource, ProjectTemplate), implement local
  concrete classes, wire DI factories, migrate all remaining routers
related_documents:
- docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md
- docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
- docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
owner: null
contributors: []
priority: critical
risk_level: high
category: refactors
tags:
- implementation
- planning
- repository-pattern
- hexagonal-architecture
- refactor
- gap-closure
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/core/interfaces/repositories.py
- skillmeat/core/interfaces/dtos.py
- skillmeat/core/repositories/
- skillmeat/api/dependencies.py
- skillmeat/api/routers/
---

# Implementation Plan: Repository Pattern Gap Closure

**Plan ID**: `IMPL-2026-03-04-REPO-GAP-CLOSURE`
**Date**: 2026-03-04
**Author**: Opus orchestrator
**Related Documents**:
- **Parent refactor**: `docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md`
- **Enables**: `docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md`
- **Enables**: `docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md`

**Complexity**: Large
**Total Estimated Effort**: 38 story points
**Target Timeline**: 12-16 days

---

## Executive Summary

The repo-pattern-refactor-v1 established solid infrastructure (6 ABCs, 6 local implementations, DI factory providers, typed aliases) but left significant gaps in router adoption. An audit found **10 routers with 380+ direct SQLAlchemy session calls** that bypass repository interfaces entirely, plus **4 domains with no repository interface at all**.

This gap-closure plan completes the migration so that **zero direct data access remains in routers**, fully unblocking the enterprise-db-storage refactor. The enterprise edition needs only to implement the repository interfaces — if routers still hit SQLAlchemy directly, those code paths cannot be swapped to a cloud database.

### Gaps Identified

| Category | Count | Impact |
|----------|-------|--------|
| Missing ABCs (new domains) | 4 | Groups, ContextEntities, MarketplaceSources, ProjectTemplates have no interface |
| Missing methods on existing ABCs | ~10 | artifacts.py uses 31 fallback session queries for operations not on IArtifactRepository |
| Routers not using existing DI | 10 | 380+ direct session.query/add/commit calls bypass the interface layer |
| Concrete repo imports (should use DI) | 6 | Import from `skillmeat.cache.repositories` instead of `dependencies.py` aliases |
| Existing ABC gaps (ICollectionRepository) | 5+ methods | Missing create/update/delete/group membership operations |
| Existing ABC gaps (ISettingsRepository) | 5+ methods | Missing EntityTypeConfig/Category CRUD |

---

## Implementation Strategy

### Architecture Sequence

1. **Interface Extensions** — Extend existing ABCs with missing methods; create 4 new ABCs
2. **Local Implementation Extensions** — Extend existing local repos; create 4 new local repo classes
3. **DI Wiring** — Add factory providers and typed aliases for 4 new repos
4. **Router Migration (Critical)** — Migrate the 3 largest violating routers (280+ combined calls)
5. **Router Migration (High)** — Migrate 4 domain-specific routers (100+ combined calls)
6. **Router Migration (Medium)** — Migrate 4 routers with minor violations
7. **Validation** — Grep audit, test suite, OpenAPI diff

### Critical Path

Phase 1 → Phase 2 → Phase 3 is strictly linear. Phases 4-6 can begin once Phase 3 completes and can run in parallel within each phase (each router is independent). Phase 7 requires all prior phases.

### Parallel Opportunities

- Within Phase 1: existing ABC extensions (TASK-1.1, TASK-1.2) can run in parallel with new ABC creation (TASK-1.3, TASK-1.4)
- Within Phase 2: all 4 new local repos can run in parallel once their ABCs exist
- Within Phases 4-6: each router migration is independent
- Phase 5 can start as soon as Phase 3 completes (no dependency on Phase 4)

---

## Phase Breakdown

### Phase 1: Interface Extensions & New ABCs (6 pts, 2-3 days)

**Dependencies**: None
**Assigned**: python-backend-engineer, backend-architect

Extend the 3 existing ABCs that have method gaps, and create 4 entirely new ABCs for domains that currently lack any interface.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-1.1 | Extend IArtifactRepository | Add ~10 missing methods: `resolve_uuid_by_type_name()`, `batch_resolve_uuids()`, `get_with_collection_context()`, `get_collection_memberships()`, `get_by_uuid()`, `get_collection_description()`, `get_duplicate_cluster_members()`, `validate_exists()`, `update_collection_tags()` | All methods defined as abstract; type hints reference existing DTOs | 1.5 pts | backend-architect | None |
| TASK-1.2 | Extend ICollectionRepository & ISettingsRepository | ICollectionRepository: add `create()`, `update()`, `delete()`, `add_artifacts()`, `remove_artifact()`, `list_entities()`, `add_entity()`, `remove_entity()`, `migrate_to_default()`. ISettingsRepository: add `list_entity_type_configs()`, `create_entity_type_config()`, `update_entity_type_config()`, `delete_entity_type_config()`, `list_categories()`, `create_category()` | All methods defined as abstract | 1 pt | backend-architect | None |
| TASK-1.3 | Create IGroupRepository | New ABC with 11 methods: `create()`, `list()`, `get_with_artifacts()`, `update()`, `delete()`, `copy_to_collection()`, `reorder_groups()`, `add_artifacts()`, `remove_artifact()`, `update_artifact_position()`, `reorder_artifacts()`. Create `GroupDTO`, `GroupArtifactDTO` in dtos.py | ABC importable from `skillmeat.core.interfaces`; all methods abstract | 1 pt | backend-architect | None |
| TASK-1.4 | Create IContextEntityRepository, IMarketplaceSourceRepository, IProjectTemplateRepository | IContextEntityRepository: 7 methods (CRUD + deploy + content). IMarketplaceSourceRepository: cover catalog queries, source CRUD, import operations, composite membership. IProjectTemplateRepository: 6 methods (CRUD + deploy). Create corresponding DTOs | All 3 ABCs importable; all methods abstract | 2.5 pts | backend-architect | None |

**Phase 1 Quality Gates:**
- All extended + new ABCs importable from `skillmeat.core.interfaces`
- All new DTOs defined in `skillmeat/core/interfaces/dtos.py`
- Type checking passes with mypy
- Unit tests verify `NotImplementedError` on all new abstract methods

---

### Phase 2: Local Implementation Extensions (10 pts, 3-4 days)

**Dependencies**: Phase 1 complete
**Assigned**: python-backend-engineer, data-layer-expert

Extend the 3 existing local repos with newly-defined methods. Create 4 new `Local*Repository` classes that delegate to existing managers/ORM operations.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-2.1 | Extend LocalArtifactRepository | Implement the ~10 new methods from TASK-1.1. UUID resolution delegates to DB cache query. Batch resolution uses `IN` clause. Duplicate cluster queries delegate to DuplicatePair model. Collection membership/description queries delegate to CollectionArtifact model | All methods return correct DTOs; write-through for mutations | 3 pts | python-backend-engineer | TASK-1.1 |
| TASK-2.2 | Extend LocalCollectionRepository & LocalSettingsRepository | Implement new collection CRUD + entity membership methods. Settings: implement EntityTypeConfig/Category CRUD. Both delegate to existing session patterns extracted from routers | All methods return correct DTOs | 2 pts | python-backend-engineer | TASK-1.2 |
| TASK-2.3 | Create LocalGroupRepository | New file `skillmeat/core/repositories/local_group.py`. Implement all 11 methods. Extract logic from `groups.py` router — position management, artifact UUID resolution, manifest sync side-effects. Manage session lifecycle internally | All methods tested; position reordering works correctly | 2 pts | python-backend-engineer | TASK-1.3 |
| TASK-2.4 | Create LocalContextEntityRepository | New file. Implement 7 methods. Extract CRUD logic from `context_entities.py` router. Handle ArtifactCategoryAssociation join table internally | All methods tested | 1 pt | python-backend-engineer | TASK-1.4 |
| TASK-2.5 | Create LocalMarketplaceSourceRepository | New file. Implement catalog query, source CRUD, import operations, composite membership. Extract from `marketplace_sources.py` and `marketplace.py` router logic | All methods tested; import workflow functional | 1.5 pts | python-backend-engineer | TASK-1.4 |
| TASK-2.6 | Create LocalProjectTemplateRepository | New file. Implement 6 methods. Extract CRUD from `project_templates.py` router | All methods tested | 0.5 pts | python-backend-engineer | TASK-1.4 |

**Phase 2 Quality Gates:**
- All extended repos pass integration tests
- All 4 new repos pass unit tests
- Write-through behavior verified for mutation methods
- No business logic in repos — only data access + DTO conversion

---

### Phase 3: DI Wiring (2 pts, 1 day)

**Dependencies**: Phase 2 complete
**Assigned**: python-backend-engineer

Add factory providers and typed `Annotated` aliases for the 4 new repositories in `skillmeat/api/dependencies.py`.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-3.1 | Add 4 new factory providers | Add `get_group_repository()`, `get_context_entity_repository()`, `get_marketplace_source_repository()`, `get_project_template_repository()` to `dependencies.py`. Each checks `config.EDITION` and returns the local implementation | All 4 factories resolve correctly | 1 pt | python-backend-engineer | TASK-2.6 |
| TASK-3.2 | Add 4 new typed DI aliases | Register `GroupRepoDep`, `ContextEntityRepoDep`, MarketplaceSourceRepoDep`, `ProjectTemplateRepoDep` as `Annotated[I*Repository, Depends(...)]` | All aliases available for router injection | 0.5 pts | python-backend-engineer | TASK-3.1 |
| TASK-3.3 | Update `__init__.py` exports | Ensure `skillmeat/core/interfaces/__init__.py` and `skillmeat/core/repositories/__init__.py` export all new classes | Clean imports from both modules | 0.5 pts | python-backend-engineer | TASK-3.1 |

**Phase 3 Quality Gates:**
- All 10 DI aliases (6 existing + 4 new) resolve in running FastAPI app
- Factory returns correct implementation based on `config.EDITION`
- Import paths clean

---

### Phase 4: Router Migration — Critical (10 pts, 3-4 days)

**Dependencies**: Phase 3 complete
**Assigned**: python-backend-engineer, refactoring-expert

Migrate the 3 largest violating routers. These account for ~280 of the 380+ direct session calls.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-4.1 | Migrate user_collections.py | Replace 180+ session calls with `CollectionRepoDep` + `ArtifactRepoDep`. Remove all `session.query()`, `session.add()`, `session.commit()`. Remove `from skillmeat.cache.models` imports. 16 endpoints | Zero direct session usage; all collection tests pass | 4 pts | refactoring-expert | TASK-3.3 |
| TASK-4.2 | Migrate groups.py | Replace 70+ session calls with `GroupRepoDep`. Remove `get_session()` imports. Remove all manual session lifecycle (try/commit/rollback/finally/close). 11 endpoints | Zero direct session usage; group tests pass | 3 pts | refactoring-expert | TASK-3.3 |
| TASK-4.3 | Migrate artifacts.py fallbacks | Replace 31 fallback session queries with extended `ArtifactRepoDep` methods. Target: UUID resolution calls, collection membership queries, duplicate cluster queries, similarity lookups, tag cache sync. Keep legitimate file-content I/O (open/read for artifact files) | Zero `session.query()` calls; all artifact tests pass | 3 pts | python-backend-engineer | TASK-3.3 |

**Phase 4 Quality Gates:**
- `grep -rn "session.query\|session.add\|session.commit\|session.execute\|get_session" skillmeat/api/routers/{user_collections,groups}.py` returns zero matches
- `grep -rn "db_session.query\|tag_db_session\|skill_uuid_session" skillmeat/api/routers/artifacts.py` returns zero matches
- Full pytest suite passes after each migration
- OpenAPI spec unchanged

---

### Phase 5: Router Migration — High (5 pts, 2-3 days)

**Dependencies**: Phase 3 complete (can run in parallel with Phase 4)
**Assigned**: python-backend-engineer

Migrate 4 domain-specific routers with significant session usage.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-5.1 | Migrate context_entities.py | Replace 25+ session calls with `ContextEntityRepoDep`. Remove direct `Artifact`, `ArtifactCategoryAssociation`, `Project` model imports. 7 endpoints | Zero direct session usage | 1.5 pts | python-backend-engineer | TASK-3.3 |
| TASK-5.2 | Migrate settings.py (entity type config) | Replace 25+ session calls for EntityTypeConfig/Category CRUD with `SettingsRepoDep`. Keep non-entity-type settings endpoints unchanged if they already use DI | Zero direct session usage for entity type config endpoints | 1.5 pts | python-backend-engineer | TASK-3.3 |
| TASK-5.3 | Migrate marketplace_sources.py | Replace 30+ direct session calls with `MarketplaceSourceRepoDep`. Keep manager-delegated parts unchanged. Remove direct `get_session()` and concrete repo imports | Zero direct session usage; import workflow functional | 1.5 pts | python-backend-engineer | TASK-3.3 |
| TASK-5.4 | Migrate project_templates.py | Replace 20+ session calls with `ProjectTemplateRepoDep`. 6 endpoints | Zero direct session usage | 0.5 pts | python-backend-engineer | TASK-3.3 |

**Phase 5 Quality Gates:**
- Zero `session.query` / `get_session` in all 4 migrated routers
- All router test files pass
- OpenAPI spec unchanged

---

### Phase 6: Router Migration — Medium (3 pts, 1-2 days)

**Dependencies**: Phase 3 complete (can run in parallel with Phases 4-5)
**Assigned**: python-backend-engineer

Migrate 4 routers with minor violations (2-5 direct calls each) and fix concrete repo imports.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-6.1 | Migrate idp_integration.py | Replace 5 session calls (DeploymentSet CRUD) with `DeploymentRepoDep`. Remove direct `get_session()` + model imports | Zero direct session; tests pass | 0.5 pts | python-backend-engineer | TASK-3.3 |
| TASK-6.2 | Migrate marketplace.py | Replace 4 direct session calls (CompositeMembership) with `MarketplaceSourceRepoDep` | Zero direct session; tests pass | 0.5 pts | python-backend-engineer | TASK-3.3 |
| TASK-6.3 | Migrate deployment_sets.py + deployment_profiles.py | deployment_sets.py: replace 2 artifact UUID resolution queries with `ArtifactRepoDep.resolve_uuid_by_type_name()`. deployment_profiles.py: replace concrete `DeploymentProfileRepository` import with DI alias. Both: remove `from skillmeat.cache.repositories` imports | Zero concrete repo imports; tests pass | 1 pt | python-backend-engineer | TASK-3.3 |
| TASK-6.4 | Fix remaining concrete repo imports | Audit and replace all `from skillmeat.cache.repositories import` in routers with DI aliases. Targets: marketplace_catalog.py, context_entities.py (DeploymentProfileRepository import), any others found. Exception: error types (ConstraintError, NotFoundError, RepositoryError) may remain as they're domain exceptions, not data access | Zero concrete repo class imports in routers (exception types OK) | 1 pt | python-backend-engineer | TASK-3.3 |

**Phase 6 Quality Gates:**
- Zero concrete repository class imports in any router file
- Zero `get_session()` / `session.query()` in any router file
- All tests pass

---

### Phase 7: Validation & Cleanup (2 pts, 1 day)

**Dependencies**: All previous phases complete
**Assigned**: task-completion-validator, python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TASK-7.1 | Zero-import audit | Run comprehensive grep to verify zero direct data access in ALL router files: `grep -rn "session\.\|get_session\|from sqlalchemy\|from skillmeat.cache.models\|from skillmeat.cache.repositories" skillmeat/api/routers/`. Whitelist: exception type imports only | Zero matches (excluding whitelisted exception imports) | 0.5 pts | task-completion-validator | TASK-6.4 |
| TASK-7.2 | OpenAPI contract diff | Diff current `openapi.json` against pre-refactor snapshot. Verify zero endpoint signature changes | Zero contract changes | 0.5 pts | task-completion-validator | TASK-7.1 |
| TASK-7.3 | Full test suite run | Run complete `pytest` suite. Document any regressions vs baseline | All tests pass (or pre-existing failures only) | 0.5 pts | task-completion-validator | TASK-7.1 |
| TASK-7.4 | Update interfaces README + exports | Update `skillmeat/core/interfaces/README.md` with all 10 ABCs. Verify `__init__.py` exports. Delete dead code (unused path helpers, orphaned imports) | Clean exports; no dead code | 0.5 pts | python-backend-engineer | TASK-7.1 |

**Phase 7 Quality Gates:**
- All acceptance criteria from enterprise-db-storage PRD prerequisites met
- Every router endpoint accesses data exclusively through repository DI
- An enterprise repository implementation would intercept ALL data access by implementing the 10 ABCs
- OpenAPI contract unchanged
- Full test suite passes

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| user_collections.py blast radius (180+ calls, 3000+ lines) | High | High | Migrate endpoint-by-endpoint; run tests after each batch of 3-4 endpoints |
| Session lifecycle changes break transactions | High | Medium | LocalGroupRepository must replicate exact commit/rollback semantics from router |
| Missing edge cases in extracted repo methods | Medium | Medium | Copy test fixtures from router tests into repo unit tests |
| Marketplace import workflow regression | High | Medium | Integration test the full import flow before and after migration |
| groups.py position management correctness | Medium | Medium | Extract position-shifting logic as-is; do not refactor during migration |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Interface churn during Phase 2 | Medium | Low | Freeze ABCs at Phase 1 completion; extension requests go through review |
| user_collections.py takes longer than estimated | High | Medium | Timebox TASK-4.1 at 4 days; if blocked, split into collection CRUD + artifact membership + entity membership sub-tasks |
| Phases 4-6 discover additional missing repo methods | Medium | Medium | Add methods to interfaces/implementations inline; track as addenda |

---

## Success Metrics

**Delivery**: All 7 phases completed within 16 days
**Quality**: Zero direct data access in routers (grep-verifiable), all tests pass, OpenAPI contract unchanged
**Business**: Fully unblocks enterprise-db-storage refactor — implementing 10 ABCs covers 100% of data access paths

---

## Enterprise Readiness Checklist

After this plan completes, the enterprise-db-storage refactor (PRD 3) requires:

- [ ] Implement `EnterpriseArtifactRepository` (replaces `LocalArtifactRepository`)
- [ ] Implement `EnterpriseCollectionRepository`
- [ ] Implement `EnterpriseProjectRepository`
- [ ] Implement `EnterpriseDeploymentRepository`
- [ ] Implement `EnterpriseTagRepository`
- [ ] Implement `EnterpriseSettingsRepository`
- [ ] Implement `EnterpriseGroupRepository`
- [ ] Implement `EnterpriseContextEntityRepository`
- [ ] Implement `EnterpriseMarketplaceSourceRepository`
- [ ] Implement `EnterpriseProjectTemplateRepository`
- [ ] Add `edition: "enterprise"` branch to all 10 factory providers in `dependencies.py`

No router changes required — DI handles the swap automatically.

---

**Progress Tracking:**

See `.claude/progress/repo-pattern-gap-closure/`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-04
