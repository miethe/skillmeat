---
schema_version: 2
doc_type: implementation_plan
title: "Implementation Plan: Storage Abstraction & Repository Pattern Refactor"
status: draft
created: 2026-03-01
updated: 2026-03-01
feature_slug: "repo-pattern-refactor"
feature_version: "v1"
prd_ref: docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
plan_ref: null
scope: "Decouple all API routers and services from direct filesystem/SQLite access via abstract repository interfaces with local implementations"
effort_estimate: "40 pts"
architecture_summary: "Hexagonal architecture with ABC interfaces in skillmeat/core/interfaces/, local implementations in skillmeat/cache/repositories/, factory providers in skillmeat/api/dependencies.py"
related_documents:
  - docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md
  - docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
  - docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
owner: null
contributors: []
priority: critical
risk_level: high
category: "refactors"
tags: [implementation, planning, repository-pattern, hexagonal-architecture, refactor]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - skillmeat/core/interfaces/
  - skillmeat/cache/repositories/
  - skillmeat/api/dependencies.py
  - skillmeat/api/routers/
  - skillmeat/core/
---

# Implementation Plan: Storage Abstraction & Repository Pattern Refactor

**Plan ID**: `IMPL-2026-03-01-REPO-PATTERN-REFACTOR`
**Date**: 2026-03-01
**Author**: python-backend-engineer
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md`
- **Enables**: `docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md`
- **Enables**: `docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md`

**Complexity**: Large
**Total Estimated Effort**: 40 story points
**Target Timeline**: 16-22 days

---

## Executive Summary

This refactor introduces hexagonal architecture to SkillMeat's API layer by placing abstract repository interfaces between routers and all storage backends. Today, 15+ FastAPI routers import `os`, `pathlib`, and `sqlite3` directly, making the codebase impossible to test without a real filesystem and impossible to swap to enterprise storage without touching every router. The implementation proceeds in seven phases — test scaffolding and prerequisites first, then interface design, local implementations, dependency injection wiring, router migration, test suite alignment, and final validation — with Phase 5 (mock repositories) unlockable in parallel once Phase 1 completes. Zero functional changes are visible to end-users; all 23 API contracts remain identical throughout.

---

## Implementation Strategy

### Architecture Sequence

This is a pure backend refactor. The standard MeatyPrompts layer sequence is condensed to the layers that exist here:

0. **Test Scaffolding & Prerequisites** - Baseline tests for untested routers, config, benchmarks
1. **Interface Design** — Abstract DTOs and ABCs that define the contract every storage backend must satisfy
2. **Local Repository Implementations** — Concrete classes that delegate to existing `ArtifactManager`, `ProjectManager`, and related managers, handling FS+DB write-through internally
3. **DI & Service Layer Wiring** — FastAPI `Depends()` factories and typed aliases that inject the correct implementation based on `config.EDITION`
4. **Router Migration** — Mechanical replacement of direct `os`/`pathlib`/`sqlite3` calls with repository method calls in all 15+ routers
5. **Test Suite Alignment** — Mock repository implementations so unit tests run without any filesystem I/O
6. **Validation & Cleanup** — Grep-verified zero-import audit, performance benchmark, CLI smoke test

### Critical Path

Phase 0 has no dependencies and can complete fully independently before Phase 1 begins, making it safe to run immediately. Phase 1 → Phase 2 → Phase 3 → Phase 4 is strictly linear. Each phase depends on the previous phase's deliverables. Phase 4 is the longest phase and its sub-tasks (TASK-4.1 through TASK-4.4) are the only place where limited parallelism is possible within a phase: each router file can be migrated independently once Phase 3 is complete.

### Parallel Opportunities

Within Phase 0, TASK-0.1 through TASK-0.7 can all run in parallel — they are fully independent (baseline tests for different routers, config addition, snapshot, and benchmark have no interdependencies). Only TASK-0.8 (full test suite run) must wait for TASK-0.1 through TASK-0.7 to complete.

Phase 5 (mock repositories) can begin as soon as Phase 1 completes, because mock implementations only need the ABC interface signatures. This means test infrastructure can be built concurrently with the local implementations in Phase 2. Phase 6 (validation) begins only after all prior phases are confirmed passing.

---

## Phase Breakdown

### Phase 0: Test Scaffolding & Prerequisites

**Duration**: 2-3 days
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer, task-completion-validator

This phase creates baseline test coverage for the 8 untested routers and establishes safety nets before any architectural changes begin.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-0.1 | Baseline tests: deployments | Create `tests/api/test_deployments.py` with endpoint tests for all routes in `deployments.py` | All endpoints tested for expected status codes with mocked deps | 1.5 pts | python-backend-engineer | None |
| TASK-0.2 | Baseline tests: deployment_sets + profiles | Create `tests/api/test_deployment_sets.py` and expand `test_api_deployment_profiles.py` | All endpoints tested | 1 pt | python-backend-engineer | None |
| TASK-0.3 | Baseline tests: context_sync | Create `tests/api/test_context_sync.py` with endpoint tests | All sync endpoints tested | 1 pt | python-backend-engineer | None |
| TASK-0.4 | Baseline tests: remaining routers | Create test files for `mcp.py`, `icon_packs.py`, `versions.py`, `artifact_history.py` | All endpoints tested | 1.5 pts | python-backend-engineer | None |
| TASK-0.5 | Add config.EDITION | Add `edition: str = "local"` to `APISettings` in `skillmeat/api/config.py` | Config field exists and defaults to "local" | 0.5 pts | python-backend-engineer | None |
| TASK-0.6 | Snapshot OpenAPI spec | Save current `openapi.json` as `openapi-pre-refactor.json` for post-migration diff | Snapshot file exists | 0.5 pts | task-completion-validator | None |
| TASK-0.7 | Baseline P95 benchmark | Record P95 latency on `GET /api/v1/artifacts` as pre-refactor baseline | Benchmark recorded in context.md | 0.5 pts | python-backend-engineer | None |
| TASK-0.8 | Run full test suite | Verify all existing tests pass, document any pre-existing failures | Full pytest run with results captured | 0.5 pts | task-completion-validator | TASK-0.1 through TASK-0.7 |

**Phase 0 Quality Gates:**
- [ ] All 8 previously-untested routers have dedicated test files
- [ ] Every endpoint in untested routers has at least one status-code assertion
- [ ] `config.EDITION` field exists and defaults to `"local"`
- [ ] OpenAPI pre-refactor snapshot saved
- [ ] P95 latency baseline recorded
- [ ] Full pytest suite passes (pre-existing failures documented)

---

### Phase 1: Interface Design (3 pts, 2-3 days)

**Dependencies**: None
**Assigned**: python-backend-engineer, backend-architect

The first deliverable is a clean `skillmeat/core/interfaces/` module. This module becomes the shared contract between all storage backends and all consumers (routers, services, tests). Getting the interface signatures right up front is critical — changing an ABC signature after router migration has begun is expensive.

`RequestContext` is deliberately minimal at this stage: `user_id` for future RBAC and `request_id` for correlation logging. The six domain DTOs (`ArtifactDTO`, `ProjectDTO`, `CollectionDTO`, `DeploymentDTO`, `TagDTO`, `SettingsDTO`) are plain dataclasses with no ORM dependencies, making them safe to use in any layer. The six ABCs map one-to-one to the domain objects and raise `NotImplementedError` on all methods, enforcing that every backend provides a complete implementation.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-1.1 | Create interfaces module | Create `skillmeat/core/interfaces/` with `__init__.py` | Module importable | 0.5 pts | python-backend-engineer | None |
| TASK-1.2 | Define RequestContext | Create `RequestContext` dataclass with `user_id: str \| None`, `request_id: str` | Importable from interfaces | 0.5 pts | python-backend-engineer | TASK-1.1 |
| TASK-1.3 | Define DTOs | Create `ArtifactDTO`, `ProjectDTO`, `CollectionDTO`, `DeploymentDTO`, `TagDTO`, `SettingsDTO` | All DTOs importable, typed | 1 pt | python-backend-engineer | TASK-1.1 |
| TASK-1.4 | Define repository ABCs | Create 6 abstract repository interfaces with full method signatures | All ABCs raise NotImplementedError | 1 pt | backend-architect | TASK-1.2, TASK-1.3 |

**Phase 1 Quality Gates:**
- All ABCs importable from `skillmeat.core.interfaces`
- Type checking passes with mypy
- Unit tests verify `NotImplementedError` on all abstract methods

---

### Phase 2: Local Repository Implementations (12 pts, 4-5 days)

**Dependencies**: Phase 1 complete
**Assigned**: python-backend-engineer, data-layer-expert

Each local repository is a thin adapter: it calls the appropriate existing manager (`ArtifactManager`, `ProjectManager`, etc.) and converts the manager's return value to the corresponding DTO. The key constraint is write-through consistency — any mutation method must write to the filesystem first (via the manager) and then sync to the DB cache via `refresh_single_artifact_cache()`. Integration tests in TASK-2.6 verify this invariant for every mutation type before Phase 3 begins.

`ProjectPathResolver` (TASK-2.1) is extracted first because it eliminates the duplicated `~/.skillmeat/collection/`, `~/.claude/skills/user/`, and project-local path construction scattered across the existing codebase. All subsequent local repositories use it instead of rebuilding paths from scratch.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-2.1 | ProjectPathResolver | Implement centralized path resolution in `skillmeat/core/` | Single utility replaces all duplicated path helpers | 2 pts | python-backend-engineer | TASK-1.4 |
| TASK-2.2 | LocalArtifactRepository | Implement `IArtifactRepository` delegating to ArtifactManager | All methods return ArtifactDTO; write-through test passes | 3 pts | python-backend-engineer | TASK-2.1 |
| TASK-2.3 | LocalProjectRepository | Implement `IProjectRepository` | All methods return ProjectDTO | 2 pts | python-backend-engineer | TASK-2.1 |
| TASK-2.4 | LocalCollectionRepository | Implement `ICollectionRepository` | All methods return CollectionDTO | 2 pts | python-backend-engineer | TASK-2.1 |
| TASK-2.5 | Local remaining repos | Implement `LocalDeploymentRepository`, `LocalTagRepository`, `LocalSettingsRepository` | All methods return correct DTOs | 2 pts | python-backend-engineer | TASK-2.1 |
| TASK-2.6 | Write-through integration tests | Test FS+DB state consistency for all mutation types | Tests confirm FS and DB match after create/update/delete | 1 pt | data-layer-expert | TASK-2.2 through TASK-2.5 |

**Phase 2 Quality Gates:**
- All local repos pass integration tests
- Write-through behavior verified for every mutation type
- No direct filesystem access outside the repository layer

---

### Phase 3: DI & Service Layer Wiring (4 pts, 2 days)

**Dependencies**: Phase 2 complete
**Assigned**: python-backend-engineer, data-layer-expert

This phase wires the implementations into FastAPI's dependency injection system. Factory providers in `skillmeat/api/dependencies.py` check `config.EDITION` and return the appropriate concrete class. Typed `Annotated` aliases (`ArtifactRepoDep`, `ProjectRepoDep`, etc.) let routers declare their dependencies with a single import.

The scoped session work in TASK-3.3 is a correctness fix that this refactor requires: today, many endpoints open and close their own SQLAlchemy sessions per-operation. Scoped sessions ensure that within a single request, all repository operations share one session, avoiding dirty-read inconsistencies and connection pool exhaustion. The marketplace and workflow repositories (TASK-3.4) already exist in `skillmeat/cache/repositories/` and need import-path compatibility checks only — no logic changes.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-3.1 | Factory providers | Add `get_artifact_repository()` etc. in `dependencies.py` | `config.EDITION == "local"` returns correct type | 1 pt | python-backend-engineer | TASK-2.6 |
| TASK-3.2 | Typed DI aliases | Register `ArtifactRepoDep`, `ProjectRepoDep`, etc. | All 6 aliases available via `Annotated[I*Repository, Depends(...)]` | 1 pt | python-backend-engineer | TASK-3.1 |
| TASK-3.3 | Scoped sessions | Implement per-request SQLAlchemy scoped session | Single session per request; no per-operation open/close | 1 pt | data-layer-expert | TASK-3.1 |
| TASK-3.4 | Marketplace repo compatibility | Verify existing marketplace/workflow repos work with new module structure | Import changes only, no logic changes | 1 pt | python-backend-engineer | TASK-3.1 |

**Phase 3 Quality Gates:**
- All DI aliases resolve correctly in a running FastAPI app
- Factory returns correct implementation based on `config.EDITION`
- Existing marketplace and workflow tests pass with new session management

---

### Phase 4: Router Migration (8 pts, 5-7 days)

**Dependencies**: Phase 3 complete
**Assigned**: python-backend-engineer, refactoring-expert

This is the highest-risk phase because `artifacts.py` is 9400+ lines and contains the majority of direct filesystem access. The migration strategy for each router is: (1) replace `os`/`pathlib` imports with repository DI parameter, (2) replace inline file operations with repository method calls, (3) run the router's test file, (4) proceed to next router only after tests pass.

TASK-4.1 handles `artifacts.py` alone because of its size. TASK-4.2 handles `projects.py`. TASK-4.3 batches the four collection/deployment routers. TASK-4.4 handles all remaining routers. The grep validation in Phase 6 provides the final confirmation that the migration is complete.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-4.1 | Migrate artifacts.py | Migrate largest router (9400+ lines) to use repository DI | Zero os/pathlib imports; all artifact tests pass | 3 pts | refactoring-expert | TASK-3.4 |
| TASK-4.2 | Migrate projects.py | Migrate projects router | Zero os/pathlib imports; project tests pass | 1 pt | python-backend-engineer | TASK-3.4 |
| TASK-4.3 | Migrate collections + deployments | Migrate user_collections.py, deployments.py, deployment_sets.py, deployment_profiles.py | Zero direct FS access in these routers | 2 pts | python-backend-engineer | TASK-3.4 |
| TASK-4.4 | Migrate context + remaining | Migrate context_entities.py, context_sync.py, marketplace_sources.py, marketplace.py, mcp.py, icon_packs.py, versions.py, artifact_history.py, bundles.py | All remaining routers migrated | 2 pts | python-backend-engineer | TASK-3.4 |

**Phase 4 Quality Gates:**
- `grep -r "import os\|from pathlib\|import sqlite3" skillmeat/api/routers/` returns zero matches
- Full `pytest` suite passes after each migration batch
- All API contracts unchanged (OpenAPI spec diff shows no changes)

---

### Phase 5: Test Suite Alignment (3 pts, 2-3 days)

**Dependencies**: TASK-1.4 complete (can start after interfaces defined); Phase 4 for full validation
**Assigned**: python-backend-engineer

Mock repositories implement every method of their corresponding ABC and return configurable canned responses. This lets unit tests for routers and services run in-process with no filesystem, no SQLite, and no network — dramatically reducing test execution time and eliminating environment-dependent flakiness. TASK-5.1 can run in parallel with Phase 2 once TASK-1.4 is done. TASK-5.2 and TASK-5.3 require Phase 4 to be complete so all router tests can be refactored together.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-5.1 | Mock repositories | Create `MockArtifactRepository`, `MockProjectRepository`, etc. | Mock repos implement all interface methods | 1 pt | python-backend-engineer | TASK-1.4 |
| TASK-5.2 | Update test fixtures | Refactor test fixtures to inject mock repos | Unit tests run without filesystem I/O | 1 pt | python-backend-engineer | TASK-5.1, TASK-4.4 |
| TASK-5.3 | Verify test coverage | Ensure all repository methods have test coverage | >80% coverage on new code | 1 pt | python-backend-engineer | TASK-5.2 |

**Phase 5 Quality Gates:**
- All unit tests pass without filesystem I/O
- Coverage >80% on new repository code
- No test regressions versus pre-refactor baseline

---

### Phase 6: Validation & Cleanup (2 pts, 1-2 days)

**Dependencies**: All previous phases complete
**Assigned**: python-backend-engineer, task-completion-validator

The final phase validates the refactor against all acceptance criteria in the PRD before the branch is merged. The grep audit (TASK-6.1) provides machine-verifiable proof that no direct storage access remains in routers. The performance benchmark (TASK-6.2) confirms the abstraction layer adds less than 5ms overhead on the hot read path. The CLI smoke test (TASK-6.3) ensures that CLI commands — which bypass the API layer and use filesystem directly — remain fully functional. Cleanup (TASK-6.4) removes dead path resolution helpers and adds a `README.md` to `skillmeat/core/interfaces/` for future backend implementers.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TASK-6.1 | Zero-import validation | Run grep to verify zero direct FS imports in routers | Zero matches | 0.5 pts | task-completion-validator | TASK-4.4 |
| TASK-6.2 | Performance benchmark | Run P95 latency test vs pre-refactor baseline | <5ms overhead on GET /api/v1/artifacts | 0.5 pts | python-backend-engineer | TASK-5.3 |
| TASK-6.3 | CLI smoke test | Run `skillmeat list`, `add`, `deploy` | All commands pass unchanged | 0.5 pts | task-completion-validator | TASK-5.3 |
| TASK-6.4 | Cleanup & docs | Delete dead code, write interfaces README | Zero dead path resolution helpers; README complete | 0.5 pts | python-backend-engineer | TASK-6.1 |

**Phase 6 Quality Gates:**
- All acceptance criteria from PRD section 11 met
- Performance within bounds (<5ms overhead)
- CLI fully functional post-migration

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| artifacts.py blast radius (9400 lines) | High | High | Migrate in endpoint groups, run tests after each group |
| Write-through regression (FS+DB out of sync) | High | Medium | Integration tests per mutation type before/after Phase 2 |
| Performance overhead from abstraction | Medium | Low | Benchmark before/after; optimize hot paths if >5ms |
| Session management conflicts | Medium | Medium | Start with scoped sessions; escalate to UnitOfWork only if needed |
| Manager delegation complexity | Medium | Medium | Delegate to existing managers first; extract logic only if managers are insufficient |
| Existing test fragility | Low | Medium | Run full suite after each router migration batch |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Phase 1 interface churn | Medium | Medium | Freeze ABCs before Phase 2 begins; change requests go through lead-architect |
| artifacts.py migration overruns | High | High | Timebox TASK-4.1 at 3 days; if blocked, split into per-endpoint-group sub-tasks |
| Marketplace repo breakage | Medium | Low | TASK-3.4 explicitly validates before router migration begins |

---

## Success Metrics

**Delivery**: All 7 phases completed within 22 days
**Quality**: Zero direct FS access in routers (grep-verifiable), all tests pass, <5ms latency overhead on hot reads
**Business**: Unblocks PRD 2 (AAA/RBAC Foundation) and PRD 3 (Enterprise DB Storage) — neither can be implemented safely without this interface layer

---

## Post-Implementation

- Monitor P95 latency for 1 week post-migration via existing observability stack
- Begin PRD 2 (AAA/RBAC) planning once this reaches `completed` status
- Begin PRD 3 (Enterprise DB) planning once RBAC foundation is in place
- Update `plan_ref` field in the PRD to point to this implementation plan once file is committed

---

**Progress Tracking:**

See `.claude/progress/repo-pattern-refactor/`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-01
