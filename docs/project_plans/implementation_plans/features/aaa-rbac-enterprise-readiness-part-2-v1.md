---
title: 'Implementation Plan: AAA Enterprise Readiness Part 2'
schema_version: 2
doc_type: implementation_plan
status: completed
created: 2026-03-07
updated: '2026-03-07'
feature_slug: aaa-rbac-enterprise-readiness-part-2
feature_version: v1
parent_plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
scope: Close the remaining P0-P2 gaps identified during post-implementation AAA validation
  so enterprise repository wiring, visibility enforcement, auth bypass semantics,
  and PAT configuration are production-consistent.
priority: critical
risk_level: high
category: product-planning
tags:
- implementation
- planning
- auth
- rbac
- enterprise
- tenancy
- hardening
related_documents:
- /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
- /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
- /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1-addendum-review-findings.md
- /docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md
- /docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-2-repositories.md
review_source: Post-implementation AAA validation (Codex, 2026-03-07)
---
# Implementation Plan: AAA Enterprise Readiness Part 2

**Plan ID**: `IMPL-2026-03-07-AAA-ENTERPRISE-READINESS-PART-2`
**Date**: 2026-03-07
**Author**: Codex (reviewed and corrected by Opus)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md`
- **Parent Plan**: `/docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md`
- **Addendum**: `/docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1-addendum-review-findings.md`
- **Enterprise Repository Plan**: `/docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-2-repositories.md`

**Complexity**: Medium
**Total Estimated Effort**: 22 story points
**Target Timeline**: 1.5-2 weeks

## Executive Summary

AAA/RBAC Foundation v1 landed the auth provider system, JWT validation (including `aud`/`iss` hardening), secure-by-default route protection, tenant context wiring, visibility filtering infrastructure, and end-to-end integration tests. However, post-implementation validation found four remaining gaps: the `auth_enabled=false` bypass path has inconsistent semantics across server/CLI/docs, the enterprise repository implementations are not wired into the main API dependency graph (10 providers return `503 Unsupported edition`), visibility enforcement only covers the `list_artifacts` enterprise read path, and enterprise PAT configuration uses conflicting environment variable naming between `enterprise_auth.py` and `APISettings`.

This part-2 plan treats those gaps as release-blocking hardening work.

## Current State (What's Already Landed)

The following infrastructure from the AAA foundation and addendum is **complete and tested** (verified in codebase):

| Component | Status | Evidence |
|-----------|--------|----------|
| Auth provider instantiation in lifespan | Done | `server.py:111-134` — reads `settings.auth_provider`, instantiates Local/Clerk, calls `set_auth_provider()` |
| JWT `aud`/`iss` claim validation | Done | `clerk_provider.py:326-341` — dynamic required claims with audience/issuer validation |
| `request.state.auth_context` population | Done | `dependencies.py:246` — set after successful auth |
| `set_tenant_context_dep` registration | Done | `server.py:397-400` — registered as app-level dependency alongside `require_auth()` |
| Secure-by-default route protection | Done | `server.py:400` — `_auth_deps` applied to protected router; public routes on separate router |
| `apply_visibility_filter_stmt` function | Done | `core/repositories/filters.py:69-129` — handles admin bypass, owner/public/team semantics |
| Visibility filter applied to enterprise `list_artifacts` | Done | `enterprise_repositories.py:805-821` |
| `str_owner_id` helper + type mismatch docs | Done | DES-001 completed |
| End-to-end auth integration tests | Done | `test_auth_integration.py` — 15+ test cases covering provider→require_auth→service flow |

## Addendum Reconciliation

All P0 and most P1/P2 items from the addendum have been completed. This table maps each addendum task to its current status:

| Addendum ID | Description | Status | Part 2 Coverage |
|-------------|-------------|--------|-----------------|
| SEC-001 | `aud` claim validation | **Completed** | — |
| SEC-002 | `iss` claim validation | **Completed** | — |
| WIRE-001 | Auth provider instantiation in lifespan | **Completed** | — |
| WIRE-002 | TenantContext dependency registration | **Completed** | — |
| WIRE-003 | `request.state.auth_context` | **Completed** | — |
| ENT-001 | Secure-by-default route protection | **Completed** | — |
| ENT-002 | Visibility-based filtering in repositories | **Partial** — only `list_artifacts` | Absorbed into SEC2-002, SEC2-003 |
| ENT-003 | End-to-end auth flow integration test | **Completed** | — |
| ENT-004 | Structured audit events | **Deferred** (Phase 6+) | Out of scope |
| DES-001 | `owner_id` type mismatch helper | **Completed** | — |
| DES-002 | `system_admin` assignment path docs | **Completed** | — |
| DES-003 | `AuthorizationService` interface | **Deferred** (Phase 5+) | Out of scope |
| DES-004 | Token revocation strategy | **Deferred** (Phase 5+) | Out of scope |
| DES-005 | String-based scope registry | **Deferred** (Phase 5+) | Out of scope |

## Validation Scope

This plan covers the **four unresolved findings** from the AAA validation review:

1. **P0**: `auth_enabled=false` does not consistently bypass auth — the `require_auth` dependency and CLI mode detection interpret the flag differently.
2. **P0**: Main API dependency providers do not support enterprise edition repositories — 10 providers in `dependencies.py` return `503 Unsupported edition` for `edition != "local"`.
3. **P1**: Visibility enforcement only applies to `enterprise_repositories.py:list_artifacts` — direct reads (`get_by_id`), content reads, version reads, and tag searches lack `apply_visibility_filter_stmt`.
4. **P2**: PAT runtime env var handling is inconsistent — `enterprise_auth.py:120` reads `ENTERPRISE_PAT_SECRET` via `os.environ.get()`, while `config.py:212` defines `SKILLMEAT_ENTERPRISE_PAT_SECRET` via `APISettings`.

## Implementation Strategy

### Architecture Sequence

1. **Auth Bypass Contract** — Make `auth_enabled=false` semantics deterministic across server, middleware, CLI, and docs.
2. **Enterprise Dependency Graph Completion** — Wire enterprise repository implementations into the 10 FastAPI dependency providers.
3. **Visibility Hardening** — Extend `apply_visibility_filter_stmt` (already exists) to all enterprise repository read paths.
4. **PAT Config Normalization** — Align `enterprise_auth.py` to read through `APISettings`.
5. **Validation & Documentation** — Regression tests + doc corrections.

### Parallel Work Opportunities

- **Phase 1 and Phase 2 are independent** — auth bypass semantics and enterprise DI routing touch different code paths. They can run in parallel.
- PAT config normalization (CP-003) can run in parallel with either phase.
- Visibility hardening (Phase 3) can begin once the enterprise read path audit (SEC2-001) is complete, which only requires Phase 2's provider inventory (ENT2-001).
- Documentation updates can begin after Phase 1 decisions are finalized, concurrent with Phase 3/4 implementation.

### Critical Path

1. Define runtime contract for `auth_enabled=false` bypass behavior.
2. Complete enterprise provider routing matrix (ENT2-001).
3. Wire enterprise artifact/collection providers (ENT2-002) — unblocks visibility audit.
4. Extend visibility filters to all enterprise read methods (SEC2-002/003).
5. Regression tests across both local and enterprise modes.

## Phase Breakdown

### Phase 1: Auth Bypass Contract Alignment

**Duration**: 2 days
**Dependencies**: None
**Assigned Subagent(s)**: backend-architect, python-backend-engineer

#### Goals

- Establish one authoritative runtime contract for `auth_enabled=false` behavior.
- Ensure `require_auth` dependency, CLI mode detection, and deployment docs all interpret the same flag identically.

**Note**: Auth provider instantiation (WIRE-001) and secure-by-default routing (ENT-001) are already complete. This phase focuses narrowly on the `auth_enabled=false` bypass path, which is the remaining inconsistency.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| CP-001 | Auth Bypass Contract | Define and implement the authoritative decision table for `auth_enabled=false` in the active `require_auth` path. Provider instantiation is already done (`server.py:111-134`); this task clarifies what happens when `auth_enabled=false` — does `require_auth` short-circuit to `LocalAuthProvider`, skip validation entirely, or return a fixed anonymous context? | `require_auth` behavior matches the documented contract for both `auth_enabled=true` and `auth_enabled=false`; no hidden secondary enforcement path contradicts the contract | 2 pts | backend-architect, python-backend-engineer | None |
| CP-002 | Server and CLI Semantics Sync | Align `server.py` startup logging, CLI local-mode detection, and any auth helpers so they interpret `auth_enabled` identically | CLI and server agree on local vs authenticated mode; integration tests cover the shared decision table | 1 pt | python-backend-engineer | CP-001 |
| CP-003 | Enterprise PAT Config Normalization | Update `enterprise_auth.py:120` to read through `APISettings` instead of raw `os.environ.get("ENTERPRISE_PAT_SECRET")`. Remove ambiguity between `ENTERPRISE_PAT_SECRET` and `SKILLMEAT_ENTERPRISE_PAT_SECRET` | One documented config path exists; legacy alias behavior is explicit if retained; tests cover both accepted and rejected config states | 1 pt | python-backend-engineer | None |
| CP-004 | OpenAPI and Rollout Contract Update | Update API auth descriptions and rollout docs to match the actual control-plane behavior implemented in CP-001..003 | OpenAPI auth docs, deployment auth rollout guide, and API auth guide all describe the same enforcement behavior | 1 pt | api-documenter, documentation-writer | CP-001, CP-003 |

#### Quality Gates

- [ ] `auth_enabled=false` semantics are deterministic and test-covered
- [ ] No control-plane mismatch remains between API server, CLI, and docs
- [ ] PAT config uses `APISettings` as single source of truth
- [ ] OpenAPI/auth rollout docs match runtime behavior exactly

### Phase 2: Enterprise Edition Dependency Graph Completion

**Duration**: 4 days
**Dependencies**: None (runs in parallel with Phase 1)
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert, backend-architect

#### Goals

- Make the 10 API dependency providers in `dependencies.py` return enterprise repository implementations when `edition == "enterprise"`.
- Thread DB session requirements and repository construction through the hexagonal provider layer.
- Eliminate `Unsupported edition` failures for supported enterprise AAA surfaces.

**Current state**: All 10 providers (`get_artifact_repository`, `get_collection_repository`, `get_project_repository`, `get_deployment_repository`, `get_tag_repository`, `get_settings_repository`, `get_group_repository`, `get_context_entity_repository`, `get_marketplace_source_repository`, `get_project_template_repository`) only support `edition == "local"` and raise `HTTPException(503)` otherwise.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| ENT2-001 | Provider Inventory and Routing Matrix | Enumerate all 10 dependency providers in `dependencies.py`, classify which enterprise repository implementations exist in `cache/enterprise_repositories.py`, and define the edition routing matrix | A concrete matrix exists for each provider showing local implementation, enterprise implementation, or explicit unsupported status with rationale | 1 pt | backend-architect, python-backend-engineer | None |
| ENT2-002 | Enterprise Artifact/Collection Providers | Wire `get_artifact_repository()` and `get_collection_repository()` to enterprise implementations using the request DB session path | Enterprise edition returns working artifact and collection repositories instead of `503 Unsupported edition`; local behavior remains unchanged | 3 pts | python-backend-engineer, data-layer-expert | ENT2-001 |
| ENT2-003 | Enterprise Provider Coverage for Adjacent Services | Extend remaining edition-aware dependency providers that have enterprise implementations, or explicitly gate unsupported surfaces with deliberate errors and docs | No accidental `Unsupported edition` remains on AAA-critical enterprise routes; unsupported surfaces fail intentionally with actionable messaging | 3 pts | python-backend-engineer, backend-architect | ENT2-001 |
| ENT2-004 | Request-Lifecycle Tenant Wiring Validation | Verify enterprise provider wiring works correctly with `set_tenant_context_dep` (already registered at `server.py:400`), DB session lifecycle, and service-layer auth propagation | Enterprise requests set tenant context before repository usage; no request-level leakage or missing-context fallback occurs on supported routes | 1 pt | data-layer-expert, python-backend-engineer | ENT2-002, ENT2-003 |

#### Quality Gates

- [ ] Supported enterprise edition routes resolve repository dependencies successfully
- [ ] Artifact and collection services operate through enterprise repositories in main API mode
- [ ] Unsupported enterprise paths are explicit, documented, and non-accidental
- [ ] Tenant context and DB session lifecycles remain correct under enterprise mode

### Phase 3: Repository Visibility and Ownership Hardening

**Duration**: 3 days
**Dependencies**: Phase 2 ENT2-001 complete (need provider inventory to know which read paths exist)
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

#### Goals

- Extend `apply_visibility_filter_stmt` (already implemented in `core/repositories/filters.py:69-129`) to all enterprise repository read paths beyond `list_artifacts`.
- Preserve tenant isolation while preventing same-tenant leakage of private resources.
- Clarify and enforce owner-level semantics for direct fetches.

**Current state**: `apply_visibility_filter_stmt` handles admin bypass, owner checks, and public/team/private filtering. It is applied in `enterprise_repositories.py:821` for `list_artifacts` only. Other read methods (`get_by_id`, content reads, version reads, tag searches, collection membership reads) do not call it.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| SEC2-001 | Enterprise Read Path Audit | Audit all enterprise repository read methods for artifact, collection, and membership access to identify missing `apply_visibility_filter_stmt` calls | Every enterprise read method is classified as visibility-aware, intentionally public-within-tenant, or needing remediation | 1 pt | data-layer-expert, python-backend-engineer | ENT2-001 |
| SEC2-002 | Artifact Read Path Enforcement | Apply `apply_visibility_filter_stmt` to direct artifact reads and derivative reads (content, versions, tag searches) in enterprise repositories | Private artifact access is blocked for same-tenant non-owners across direct and indirect reads; admin bypass is preserved per existing filter logic | 2 pts | python-backend-engineer, data-layer-expert | SEC2-001 |
| SEC2-003 | Collection and Membership Visibility Policy | Define and implement collection visibility semantics for direct fetches and `list_artifacts()`/membership reads using `apply_visibility_filter_stmt` | Collection fetches and collection artifact reads follow documented visibility rules; same-tenant private collection leakage is prevented | 2 pts | python-backend-engineer, data-layer-expert | SEC2-001 |
| SEC2-004 | Ownership Error Semantics | Normalize whether unauthorized reads return `None`, filtered empties, or explicit authorization failures, and ensure routers/services do not disclose existence improperly | Unauthorized access behavior is consistent by method type and documented in code/tests; no cross-owner existence disclosure regressions remain | 1 pt | backend-architect, python-backend-engineer | SEC2-002, SEC2-003 |

#### Quality Gates

- [ ] Enterprise read paths enforce visibility consistently via `apply_visibility_filter_stmt`
- [ ] Same-tenant users cannot read each other's private artifacts or collections through alternate methods
- [ ] Admin bypass and team/public semantics are deliberate and documented
- [ ] Unauthorized read behavior is consistent and non-leaky

### Phase 4: Integration, Regression, and Documentation Closure

**Duration**: 3 days
**Dependencies**: Phases 1-3 complete
**Assigned Subagent(s)**: python-backend-engineer, api-documenter, documentation-writer

#### Goals

- Prove the final runtime behavior with regression coverage across local and enterprise modes.
- Correct documentation so rollout, operations, and future implementation work all follow the actual contract.
- Produce an explicit completion checklist for enterprise-readiness signoff.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| TEST2-001 | Auth Bypass Regression Tests | Add integration coverage for `auth_enabled=false` behavior in the real app factory/lifespan path | Tests prove disabled auth behavior and local provider passthrough using actual app wiring | 2 pts | python-backend-engineer | Phase 1 |
| TEST2-002 | Enterprise Dependency Graph Integration Tests | Add end-to-end tests that start the app in enterprise edition and verify repository dependency resolution on supported routes | Supported enterprise routes return real responses instead of `503 Unsupported edition`; tenant context and auth context reach services | 2 pts | python-backend-engineer, data-layer-expert | Phase 2 |
| TEST2-003 | Visibility Regression Matrix | Add test coverage for direct reads, indirect reads, and collection membership reads across owner/public/team/private cases | All previously identified leakage paths are covered; failing cases are reproducible before fix and green after fix | 2 pts | python-backend-engineer | Phase 3 |
| DOC2-001 | Enterprise Auth and Rollout Guide Corrections | Update deployment, API auth, security, and developer guides to reflect the post-fix runtime contract and provider wiring | Docs describe exact env vars, edition behavior, auth bypass semantics, and supported enterprise surfaces | 1 pt | documentation-writer, api-documenter | TEST2-001, TEST2-002 |
| DOC2-002 | Completion Signoff Checklist | Add a concise enterprise-readiness checklist tying AAA v1, enterprise-db storage, and repo-pattern closure together | A maintainer can validate the combined three-part initiative from one checklist without hidden assumptions | 1 pt | documentation-writer | DOC2-001 |

#### Quality Gates

- [ ] Integration tests cover local and enterprise runtime wiring
- [ ] Regression coverage exists for all four validation findings
- [ ] Auth and rollout docs match implementation exactly
- [ ] Enterprise-readiness checklist exists for final signoff

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Auth bypass changes break zero-auth local mode | High | Medium | Keep existing local-mode regression tests green (`test_auth_integration.py`) while introducing bypass contract tests |
| Enterprise provider wiring exposes unsupported surfaces unexpectedly | High | Medium | Build provider routing matrix first (ENT2-001); use explicit, documented gating for unsupported repositories |
| Visibility hardening causes behavior changes in existing enterprise routes | Medium | Low | Existing `apply_visibility_filter_stmt` logic is proven; extending it to new call sites is low-risk |
| PAT config alias change breaks existing deployments | Medium | Medium | Support a backward-compatible alias window and document exact precedence order |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Enterprise edition scope expands beyond the four validated findings | Medium | High | Keep this plan limited to P0-P2 closure; defer new feature asks to a separate PRD/plan |
| Test setup for enterprise edition becomes costly | Medium | Medium | Reuse existing enterprise repository and auth integration fixtures |
| Documentation drifts during implementation | Medium | Medium | Land doc updates in the same phase as regression validation |

## Success Metrics

### Delivery Metrics

- All four validated P0-P2 findings are mapped to completed tasks and passing regression tests.
- No supported enterprise AAA route returns accidental `503 Unsupported edition`.
- No rollout or API auth doc describes behavior that differs from the active runtime path.

### Technical Metrics

- `auth_enabled=false` behavior is test-proven in the real `create_app()` path.
- Enterprise artifact and collection access uses the correct repository implementation when `edition=enterprise`.
- Private same-tenant data is not accessible through direct or indirect repository reads.
- PAT auth configuration reads through `APISettings` as single source of truth.

### Readiness Exit Criteria

- The AAA foundation, enterprise-db storage module, and repo-pattern refactor operate as one coherent runtime system.
- There are no known P0, P1, or P2 gaps remaining in auth control plane, enterprise provider wiring, or visibility enforcement.
- Staging validation can be performed from a single documented checklist without hidden manual assumptions.

## Suggested Execution Order

1. Start Phase 1 (auth bypass) and Phase 2 (enterprise DI) in parallel — they are independent.
2. Start CP-003 (PAT normalization) immediately — independent of both phases.
3. Begin Phase 3 visibility audit (SEC2-001) once ENT2-001 provider inventory is complete.
4. Land Phase 3 with failing regression cases already in place.
5. Use Phase 4 to prove the system and update the operational contract.

## Change Boundary

This part-2 plan is intentionally limited to closing the remaining P0-P2 readiness gaps. It does **not** expand into future dynamic RBAC features (DES-003), token revocation (DES-004), string-based scope registry (DES-005), audit persistence (ENT-004), or broader enterprise feature enablement beyond what is required to make the current three-part initiative production-consistent.
