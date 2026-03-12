---
title: 'Phases 5-6: Marketplace/Template Repositories + Non-DI Migration'
schema_version: 2
doc_type: phase_plan
status: in-progress
created: 2026-03-12
updated: '2026-03-12'
feature_slug: enterprise-repo-parity
feature_version: v2
phase: 5
phase_title: Marketplace/Template Repositories and Non-DI Repo Migration
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
entry_criteria:
- Phases 3 and 4 complete (all core repositories implemented and DI-wired)
- Phase 1 triage classification confirmed for Group B repos: MarketplaceCatalogRepository,
    MarketplaceTransactionHandler, DbCollectionArtifactRepository, DbArtifactHistoryRepository,
    DuplicatePairRepository, concrete MarketplaceSourceRepository
- Open questions OQ-2 (DbCollectionArtifactRepository v1 status) and OQ-3 (MarketplaceTransactionHandler
  tier) resolved from Phase 1 triage
exit_criteria:
- Phase 5 exit: EnterpriseMarketplaceSourceRepository implemented and DI-wired; EnterpriseProjectTemplateRepository
    stub implemented and DI-wired; MarketplaceCatalogRepository and MarketplaceTransactionHandler
    edition-aware (or confirmed Passthrough); endpoints return 200 in enterprise mode
- Phase 6 exit: All remaining Group B repos edition-aware; grep audit finds zero hardcoded
    SQLite instantiations without edition check in `dependencies.py`; no SQLite writes
    for any Group B endpoint in enterprise mode
- Unit tests pass for all new Phase 5 classes
---

# Phases 5-6: Marketplace/Template Repositories + Non-DI Migration

## Overview

**Duration:** 3-4 days | **Effort:** 14 story points | **Subagents:** `python-backend-engineer`

Phase 5 closes the remaining two Group A DI-routed gaps (marketplace sources, project templates) and handles the marketplace-domain Group B repos. Phase 6 audits and resolves all remaining Group B repositories not addressed in Phases 4-5.

These two phases are grouped together because they share the same implementor and target files. Phase 5 must complete before Phase 6 to ensure the marketplace domain is fully resolved before the audit sweep.

---

## Phase 5 Task Breakdown

### ENT2-5: Marketplace Source, Project Template, and Marketplace Group B

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-5.1 | EnterpriseMarketplaceSourceRepository | Implement `EnterpriseMarketplaceSourceRepository(EnterpriseRepositoryBase, IMarketplaceSourceRepository)` in `enterprise_repositories.py`; per-tenant source configuration; implement all `IMarketplaceSourceRepository` methods including get_all, get_by_id, create, update, delete, get_enabled; `config` is JSONB; SQLAlchemy 2.x `select()` throughout; `_apply_tenant_filter()` on every query | All `IMarketplaceSourceRepository` methods implemented; JSONB config stored/returned correctly; tenant filtering on all queries; no `session.query()` calls | 3 pts | python-backend-engineer | Phases 3-4 complete | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-5.2 | EnterpriseProjectTemplateRepository stub | Implement `EnterpriseProjectTemplateRepository(EnterpriseRepositoryBase, IProjectTemplateRepository)` as a safe stub; all methods return empty collections or None with a `logger.debug("EnterpriseProjectTemplateRepository: stub — full implementation deferred to v3")` log line; no database queries issued (the stub does not need to touch the DB); the stub must NOT raise an exception | Class implemented; all `IProjectTemplateRepository` methods return empty/None without exception; debug log line present; class importable | 1 pt | python-backend-engineer | ENT2-5.1 | `skillmeat/cache/enterprise_repositories.py` |
| ENT2-5.3 | Audit MarketplaceCatalogRepository | Based on Phase 1 triage outcome: if Passthrough, update `get_marketplace_catalog_repository` in `dependencies.py` to return the existing local `MarketplaceCatalogRepository` for enterprise mode (no edition check needed — shared read-only cache); if Full, implement `EnterpriseMarketplaceCatalogRepository` following standard pattern; document the decision in a code comment | DI provider for `get_marketplace_catalog_repository` updated per triage decision; if Passthrough, existing local repo returned for enterprise mode with a `# enterprise: passthrough — shared read-only catalog cache` comment; if Full, new class implemented with tenant filter | 2 pts | python-backend-engineer | ENT2-5.2 | `skillmeat/api/dependencies.py`, optionally `skillmeat/cache/enterprise_repositories.py` |
| ENT2-5.4 | Audit MarketplaceTransactionHandler | Based on Phase 1 triage outcome for OQ-3: if Full, implement `EnterpriseMarketplaceTransactionHandler(EnterpriseRepositoryBase)` fulfilling the same interface as `MarketplaceTransactionHandler`; if Stub, implement a stub class that returns empty/None without SQLite access; if Passthrough, wire existing class; update `get_marketplace_transaction_handler` DI provider | DI provider updated; no SQLite writes in enterprise mode for transaction handler; if Full: tenant filtering on all queries; if Stub: no exceptions, empty returns with log | 2 pts | python-backend-engineer | ENT2-5.3 | `skillmeat/api/dependencies.py`, optionally `skillmeat/cache/enterprise_repositories.py` |
| ENT2-5.5 | DI wiring for Phase 5 Group A repos | Update `get_marketplace_source_repository` and `get_project_template_repository` in `dependencies.py`; enterprise path returns new enterprise classes; local path returns existing local implementations; no 503 stubs remain for these 2 interfaces | Both DI providers updated; no 503 stubs; `/api/v1/marketplace-sources` and `/api/v1/project-templates` return 200 in enterprise mode | 1 pt | python-backend-engineer | ENT2-5.1, ENT2-5.2 | `skillmeat/api/dependencies.py` |
| ENT2-5.6 | Unit tests for Phase 5 repos | Write unit tests for `EnterpriseMarketplaceSourceRepository` in `skillmeat/cache/tests/test_enterprise_parity_phase5.py`; test all CRUD methods with `MagicMock(spec=Session)`; include test for JSONB config round-trip; also test `EnterpriseProjectTemplateRepository` stub: verify all methods return empty/None without raising; do NOT test stub against real DB | Test file created; `EnterpriseMarketplaceSourceRepository` tests pass with `MagicMock(spec=Session)`; stub tests confirm no exceptions; >= 80% line coverage for `EnterpriseMarketplaceSourceRepository` | 2 pts | python-backend-engineer | ENT2-5.5 | `skillmeat/cache/tests/test_enterprise_parity_phase5.py` |

**Phase 5 Quality Gate:**
- `pytest skillmeat/cache/tests/test_enterprise_parity_phase5.py` — all pass
- Endpoints `/api/v1/marketplace-sources` and `/api/v1/project-templates` return 200 in enterprise mode
- `get_marketplace_catalog_repository` and `get_marketplace_transaction_handler` DI providers are edition-aware
- No SQLite writes for marketplace endpoints in enterprise mode

---

## Phase 6 Task Breakdown

### ENT2-6: Remaining Non-DI Repository Migration

Phase 6 is an audit-and-fix sweep for the Group B repositories not addressed in Phase 4 or 5. The goal is zero hardcoded SQLite instantiations without an edition check in `dependencies.py`.

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-6.1 | DbCollectionArtifactRepository edition-check | Based on OQ-2 resolution from Phase 1 triage: verify whether `DbCollectionArtifactRepository` was already made enterprise-aware in v1; if yes, add a code comment confirming it; if no, update `get_db_collection_artifact_repository` DI provider to check edition and either return enterprise-compatible implementation or raise a descriptive 501 with a clear message about what to implement | DI provider verified or updated; no SQLite-path instantiation without edition check; OQ-2 resolution documented in a `# enterprise: [resolution]` comment at the DI provider | 2 pts | python-backend-engineer | Phase 5 complete | `skillmeat/api/dependencies.py` |
| ENT2-6.2 | DbArtifactHistoryRepository edition-check | Based on Phase 1 triage (proposed: Stub); if Stub, implement `EnterpriseArtifactHistoryStub` returning empty list/None without DB access; update `get_db_artifact_history_repository` DI provider; if reclassified as Full in triage, implement `EnterpriseDbArtifactHistoryRepository` following standard pattern | DI provider for `get_db_artifact_history_repository` is edition-aware; in enterprise mode, no SQLite path is referenced; stub returns empty without exception | 2 pts | python-backend-engineer | ENT2-6.1 | `skillmeat/api/dependencies.py`, optionally `skillmeat/cache/enterprise_repositories.py` |
| ENT2-6.3 | DuplicatePairRepository edition-check | Based on Phase 1 triage (proposed: Stub); dedup is a local workflow; implement minimal `EnterpriseDuplicatePairStub` returning empty list/False results; update `get_duplicate_pair_repository` DI provider; add a log: `logger.debug("DuplicatePairRepository: enterprise stub — dedup is local-only in v2")` | DI provider updated; enterprise mode returns stub; stub returns empty/False without exception or SQLite access; log line present | 1 pt | python-backend-engineer | ENT2-6.2 | `skillmeat/api/dependencies.py`, optionally `skillmeat/cache/enterprise_repositories.py` |
| ENT2-6.4 | Concrete MarketplaceSourceRepository edition-check | The concrete `MarketplaceSourceRepository` (distinct from the interface-based `IMarketplaceSourceRepository`) has its own DI provider `get_marketplace_source_repository_concrete`; update this provider to route to `EnterpriseMarketplaceSourceRepository` (already implemented in Phase 5) for enterprise mode; local mode returns existing concrete class | DI provider `get_marketplace_source_repository_concrete` is edition-aware; enterprise mode returns `EnterpriseMarketplaceSourceRepository` from Phase 5; no duplicate class needed | 1 pt | python-backend-engineer | ENT2-6.3 | `skillmeat/api/dependencies.py` |
| ENT2-6.5 | Full audit: grep for remaining SQLite hardcodes | Run a targeted grep across `skillmeat/api/dependencies.py` for patterns that indicate SQLite-backed instantiation without an edition check: patterns include `db_path=`, `SQLite`, `sqlite:///`, direct instantiation of known local repo classes without `if settings.edition`; produce a short finding list; fix any remaining instances found | Grep report produced; all found instances either fixed or documented as intentionally local-only (e.g., CLI-only code paths); `dependencies.py` has zero `db_path=` or SQLite references without an adjacent edition guard | 1 pt | python-backend-engineer | ENT2-6.4 | `skillmeat/api/dependencies.py` |
| ENT2-6.6 | Update server.py for Excluded-tier routers | Based on Phase 1 triage: if any repos were classified as Excluded, update `skillmeat/api/server.py` to conditionally register their routers; excluded routers registered only in local mode; enterprise mode returns 404 with descriptive `detail` message (not 503); this task is a no-op if Phase 1 produced zero Excluded-tier classifications | If Excluded-tier repos exist: router registration conditional in `server.py`; enterprise 404 response has `detail` explaining the feature is local-only; no router returns 503 for intentionally unsupported features | 1 pt | python-backend-engineer | ENT2-6.5 | `skillmeat/api/server.py` |

**Phase 6 Quality Gate:**
- `grep -n "db_path=" skillmeat/api/dependencies.py | grep -v "edition"` returns no matches (or only intentionally-guarded lines)
- All Group B DI providers verified edition-aware
- `pytest skillmeat/cache/tests/` — no new failures introduced by Phase 6 changes
- ENT2-6.5 audit report confirms zero unguarded SQLite references

---

## Parallelization Strategy

Phases 5 and 6 must be sequential (same target files). Within Phase 5, tasks ENT2-5.1 through ENT2-5.4 target different classes but all write to `enterprise_repositories.py` — execute as a single agent batch in order. ENT2-5.5 (DI wiring) can start after ENT2-5.1 and ENT2-5.2 complete. ENT2-5.6 (tests, new file) can run after ENT2-5.5.

Phase 6 tasks ENT2-6.1 through ENT2-6.6 all touch `dependencies.py` — execute sequentially with a single agent to avoid conflicts.

**Batch execution:**

```
Phase 5 Batch A (sequential, 1 agent): ENT2-5.1 → ENT2-5.2 → ENT2-5.3 → ENT2-5.4 → ENT2-5.5
Phase 5 Batch B: ENT2-5.6 (new test file — parallel with Batch A completion)
                 ↓ Phase 5 quality gate passes
Phase 6 Batch A (sequential, 1 agent): ENT2-6.1 → ENT2-6.2 → ENT2-6.3 → ENT2-6.4 → ENT2-6.5 → ENT2-6.6
                 ↓ Phase 6 quality gate passes
```

---

## Key Files

| File | Role |
|------|------|
| `skillmeat/cache/enterprise_repositories.py` | Target: new marketplace and stub classes |
| `skillmeat/api/dependencies.py` | Target: DI providers for marketplace, template, and all Group B |
| `skillmeat/api/server.py` | Target: conditional router registration for Excluded-tier (if any) |
| `skillmeat/cache/repositories.py` | Reference: Group B local classes (MarketplaceCatalogRepository, MarketplaceTransactionHandler, DbCollectionArtifactRepository, DbArtifactHistoryRepository, DuplicatePairRepository) |
| `skillmeat/core/interfaces/repositories.py` | Reference: IMarketplaceSourceRepository, IProjectTemplateRepository signatures |
| `.claude/findings/ENT2_TRIAGE.md` | Input: Phase 1 triage decisions for OQ-2, OQ-3, Excluded-tier |
| `skillmeat/cache/tests/test_enterprise_parity_phase5.py` | Output: Phase 5 unit tests (new file) |

---

**Parent plan:** [enterprise-repo-parity-v2.md](../enterprise-repo-parity-v2.md)
**Previous phase:** [phase-3-4-core-repos.md](./phase-3-4-core-repos.md)
**Next phase:** [phase-7-testing.md](./phase-7-testing.md)
