---
title: "Phase 1: Triage & Classify"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-12
updated: 2026-03-12
feature_slug: enterprise-repo-parity
feature_version: v2
phase: 1
phase_title: Triage & Classify
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
entry_criteria:
  - enterprise-db-storage-v1 Phase 2 confirmed complete (EnterpriseRepositoryBase available)
  - repo-pattern-refactor-v1 confirmed complete (all I*Repository interfaces available)
  - aaa-rbac-foundation-v1 confirmed complete (AuthContext with tenant_id available)
exit_criteria:
  - Triage document produced classifying all 16 repositories into Full/Passthrough/Stub/Excluded tiers
  - Rationale documented for every classification decision
  - Schema design sketch produced for all Full-tier items
  - Open questions OQ-1 through OQ-4 from the PRD answered or deferred with owner
  - backend-architect review sign-off on triage document
  - Phase 2 scope confirmed (which domains need new enterprise models)
---

# Phase 1: Triage & Classify

## Overview

**Duration:** 1-2 days | **Effort:** 8 story points | **Subagents:** `data-layer-expert`, `backend-architect`

Before any implementation begins, each of the 16 repositories (8 Group A DI-routed, 8 Group B non-DI) must be classified into one of four tiers. This classification is a binding gate: it determines what gets implemented in Phases 2-6, prevents over-engineering, and documents intentional exclusions.

**Why this phase is critical:**

Implementing the wrong tier wastes significant effort. A "Full" classification requires new enterprise schema tables, a new SQLAlchemy model, a new enterprise repository class, unit tests, and DI wiring — roughly 8-12 story points per repository. A "Stub" classification requires only a returning-empty class — roughly 1-2 story points. Getting this wrong before any code is written is far cheaper than discovering it mid-implementation.

**Tier Definitions:**

| Tier | Definition | Implementation Cost |
|------|------------|-------------------|
| Full | Multi-tenant meaningful; needs real DB implementation with schema | High (8-12 pts per repo) |
| Passthrough | Works identically across editions; reuse local impl or simple adapter | Low (0.5-1 pt per repo) |
| Stub | Enterprise can safely return empty/default; deferred full impl | Low (1-2 pts per repo) |
| Excluded | Intentionally local-only; enterprise returns 404 or feature-gated response | Minimal (0.5 pt for route guard) |

---

## Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies | Target Files |
|---------|------|-------------|--------------------|---------:|-------------|--------------|--------------|
| ENT2-1.1 | Read Group A interface signatures | Read all 8 Group A `I*Repository` interfaces from `skillmeat/core/interfaces/repositories.py`; extract method signatures, parameter types, return types, and any docstrings that explain intent | Interface signatures table produced; method count and types documented for each of 8 interfaces | 2 pts | data-layer-expert | Entry criteria met | `skillmeat/core/interfaces/repositories.py` |
| ENT2-1.2 | Read local implementations for Group A | Read local implementations for all 8 Group A interfaces (in `skillmeat/core/repositories/local_*.py`); identify filesystem coupling: path lookups, directory scans, file reads, subprocess calls | Filesystem coupling inventory per repository: None/Low/Medium/High with specific method callouts | 2 pts | data-layer-expert | ENT2-1.1 | `skillmeat/core/repositories/local_*.py` |
| ENT2-1.3 | Read Group B non-DI repository classes | Read relevant classes in `skillmeat/cache/repositories.py` for all 8 Group B repos; examine how they acquire their DB session (SQLite path vs injected session) | Session acquisition pattern documented per Group B class; SQLite path usage identified | 1 pt | data-layer-expert | ENT2-1.1 | `skillmeat/cache/repositories.py` |
| ENT2-1.4 | Read DI providers for both groups | Read all 16 DI providers in `skillmeat/api/dependencies.py`; confirm which raise 503 stubs and which hardcode SQLite; check if any Group B repos are already edition-aware from v1 work | Exact line numbers for all 503 stubs and all hardcoded SQLite instantiations; any existing edition checks noted | 1 pt | data-layer-expert | ENT2-1.2, ENT2-1.3 | `skillmeat/api/dependencies.py` |
| ENT2-1.5 | Produce triage document | Produce the triage document classifying all 16 repositories; include: tier assignment, rationale, schema design sketch for Full-tier items (table name, key columns, FK relationships), answers to PRD open questions OQ-1 through OQ-4 | All 16 repos classified with written rationale; schema sketch for each Full-tier item includes table name, UUID PK, tenant_id column, and key domain columns; OQ-1 through OQ-4 answered | 3 pts | data-layer-expert | ENT2-1.1 through ENT2-1.4 | Output: `.claude/findings/ENT2_TRIAGE.md` |
| ENT2-1.6 | Architecture review of triage document | Review triage document; validate tier assignments against enterprise architecture invariants; flag any Full classifications that can safely be Stub; confirm IProjectRepository decision re: filesystem paths (OQ-1) | Sign-off comment on triage document; any classification changes noted with rationale; IProjectRepository filesystem decision explicit | 1 pt | backend-architect | ENT2-1.5 | `.claude/findings/ENT2_TRIAGE.md` |

---

## Parallelization Strategy

All tasks ENT2-1.1 through ENT2-1.4 are file-reading tasks that can run in parallel as a single batch since they touch different files. ENT2-1.5 depends on all four reads. ENT2-1.6 depends on ENT2-1.5.

**Batch 1 (parallel):** ENT2-1.1, ENT2-1.2, ENT2-1.3, ENT2-1.4

**Batch 2 (sequential):** ENT2-1.5 → ENT2-1.6

---

## Triage Document Structure

The output of ENT2-1.5 must be saved to `.claude/findings/ENT2_TRIAGE.md` with the following structure:

```markdown
# Enterprise Repo Parity v2 — Triage Classification

## Group A: DI-Routed Interfaces

| Interface | Tier | Rationale | Schema Sketch (if Full) |
|-----------|------|-----------|------------------------|
| ITagRepository | Full/Passthrough/Stub/Excluded | ... | enterprise_tags: (id UUID PK, tenant_id UUID NN, ...) |
...

## Group B: Non-DI Repositories

| Class | Tier | Rationale | Schema Sketch (if Full) |
...

## Open Question Resolutions

### OQ-1: IProjectRepository filesystem paths
...

### OQ-2: DbCollectionArtifactRepository v1 status
...

### OQ-3: MarketplaceTransactionHandler tier
...

### OQ-4: Group B repos already guarded
...

## Phase 2 Scope Confirmation

Tables to be created in Phase 2:
- enterprise_tags (domain: tags)
- ...
```

---

## Proposed Initial Classification

The PRD provides a recommended starting point. This is not binding — Phase 1 must validate it:

**Group A proposed tiers:**

| Interface | Proposed | Key Question |
|-----------|----------|-------------|
| `ITagRepository` | Full | Tags are pure metadata; no filesystem coupling expected |
| `IGroupRepository` | Full | Groups filter collections; multi-tenant meaningful |
| `ISettingsRepository` | Full | Per-tenant settings are essential |
| `IContextEntityRepository` | Full | Central to enterprise artifact context |
| `IProjectRepository` | Full | OQ-1: how to handle filesystem paths in enterprise |
| `IDeploymentRepository` | Full | Deployment records needed; path refs become DB refs |
| `IMarketplaceSourceRepository` | Full | Per-tenant source config |
| `IProjectTemplateRepository` | Stub | Filesystem-heavy; safe empty return for v2 |

**Group B proposed tiers:**

| Class | Proposed | Key Question |
|-------|----------|-------------|
| `DeploymentSetRepository` | Full | Tenant-scoped sets needed |
| `DeploymentProfileRepository` | Full | Tenant isolation required |
| `MarketplaceCatalogRepository` | Passthrough | Read-only shared data; SQLite cache acceptable |
| `MarketplaceTransactionHandler` | Full | OQ-3: transaction isolation needed? |
| `DbCollectionArtifactRepository` | Full (gap fill) | OQ-2: verify v1 coverage |
| `DbArtifactHistoryRepository` | Stub | History can degrade gracefully |
| `DuplicatePairRepository` | Stub | Dedup is local workflow |
| `MarketplaceSourceRepository` (concrete) | Full | Same domain as IMarketplaceSourceRepository |

---

## Quality Gate

Phase 2 is blocked until:

1. Triage document exists at `.claude/findings/ENT2_TRIAGE.md`
2. All 16 repositories have a tier assignment and written rationale
3. Schema sketch exists for every Full-tier item
4. `backend-architect` has reviewed and signed off (ENT2-1.6 complete)
5. Phase 2 scope (which tables to create) is explicitly listed in the triage document

---

## Key Files

| File | Role |
|------|------|
| `skillmeat/core/interfaces/repositories.py` | Source of truth for all I*Repository interface signatures (~4000 lines) |
| `skillmeat/core/repositories/local_*.py` | Local implementations; read to identify filesystem coupling |
| `skillmeat/cache/repositories.py` | Non-DI concrete classes (~7800 lines); Group B targets |
| `skillmeat/api/dependencies.py` | Current DI wiring; 503 stubs and SQLite hardcodes (~1100 lines) |
| `skillmeat/cache/enterprise_repositories.py` | Existing enterprise repo implementations for pattern reference (~2370 lines) |
| `skillmeat/cache/models_enterprise.py` | Existing enterprise models for pattern reference |
| `.claude/findings/ENT2_TRIAGE.md` | **Output artifact** of this phase |

---

**Parent plan:** [enterprise-repo-parity-v2.md](../enterprise-repo-parity-v2.md)
**Next phase:** [phase-2-schema.md](./phase-2-schema.md)
