---
schema_version: '0.3'
doc_type: implementation_plan
title: Repository Pattern Final Cleanup
status: completed
created: '2026-03-06'
updated: '2026-03-06'
feature_slug: repo-pattern-final-cleanup
feature_version: v1
priority: high
risk_level: low
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: null
scope: 2 router files, 39 session violations
effort_estimate: 3-5 points
architecture_summary: Mechanical elimination of 39 residual direct session.execute/flush
  calls across user_collections.py (36) and artifact_history.py (3), using fully wired
  DbUserCollectionRepository and DbCollectionArtifactRepository DI infrastructure;
  may require 1-2 new repository methods.
related_documents:
- docs/project_plans/implementation_plans/refactors/db-user-collection-repository-v1.md
- docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md
- docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md
owner: null
contributors: []
category: refactors
tags:
- implementation
- refactoring
- repository-pattern
- session-cleanup
- user-collections
- artifact-history
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/api/routers/user_collections.py
- skillmeat/api/routers/artifact_history.py
- skillmeat/cache/repositories.py
- skillmeat/core/interfaces/repositories.py
---

# Implementation Plan: Repository Pattern Final Cleanup

**Plan ID**: `IMPL-2026-03-06-REPO-PATTERN-FINAL-CLEANUP`
**Date**: 2026-03-06
**Author**: Implementation Planning Orchestrator
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md`
- **Prior plan (completed)**: `docs/project_plans/implementation_plans/refactors/db-user-collection-repository-v1.md`
- **Prior plan (completed)**: `docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md`
- **Prior plan (completed)**: `docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md`

**Complexity**: Small
**Total Estimated Effort**: 3-5 story points
**Target Timeline**: 2-4 days

---

## Executive Summary

Three prior refactoring plans have built out the full repository infrastructure (12 ABCs, 18 DTOs, 10 local implementations, 2 DB implementations, 17 DI aliases). This plan eliminates the 39 residual direct `session.execute` / `session.flush` calls that remain in `user_collections.py` (36) and `artifact_history.py` (3). All work is mechanical replacement: identify each raw SQL call, map it to an existing or new repository method, swap the call, and update the function signature to accept the repo via DI. Zero architectural decisions required.

---

## Implementation Strategy

### Architecture Context

The repository infrastructure is fully in place. Key files for agents:

- **Repository ABCs**: `skillmeat/core/interfaces/repositories.py`
- **Repository DTOs**: `skillmeat/core/interfaces/dtos.py`
- **DB implementations**: `skillmeat/cache/repositories.py`
  - `DbUserCollectionRepository` starts at line 5522
  - `DbCollectionArtifactRepository` starts at line 6247
- **DI wiring**: `skillmeat/api/dependencies.py` (aliases: `DbUserCollectionRepoDep`, `DbCollectionArtifactRepoDep`)
- **Target routers**: `skillmeat/api/routers/user_collections.py`, `skillmeat/api/routers/artifact_history.py`

### Replacement Pattern

For each violation:

1. Read the raw `session.execute(...)` call and understand its SQL intent (SELECT / INSERT / UPDATE / DELETE).
2. Find the matching method on `DbUserCollectionRepository` or `DbCollectionArtifactRepository` (or the artifact history repo if applicable).
3. If no method exists, add it to both the ABC interface and the concrete implementation.
4. Replace the call with the repository method.
5. Update the function signature to receive the repository via DI (`DbUserCollectionRepoDep` or `DbCollectionArtifactRepoDep`) instead of a raw `db_session` / `session`.

### Parallel Work Opportunities

- Phase 1 (helper functions) and Phase 3 (artifact_history.py) touch different functions and different files — they can run in parallel once Phase 1's helper migration is scoped, but Phase 2 depends on Phase 1 because endpoints call those helpers.
- Phase 3 is fully independent of Phases 1 and 2.

### Critical Path

Phase 1 → Phase 2 → Phase 4 (validation). Phase 3 can run alongside Phase 2.

---

## Phase Breakdown

### Phase 1: Helper Function Migration

**Entry Criteria**: `db-user-collection-repository-v1` plan marked completed; zero `session.query` / `session.add` / `session.commit` in `user_collections.py` (already achieved in prior plan).
**Exit Criteria**: All helper functions in `user_collections.py` (lines 244-513) use repository methods; no raw `session.execute` or `session.flush` remain in those functions.
**Duration**: 0.5-1 day
**Dependencies**: None (infrastructure complete)
**Assigned To**: `python-backend-engineer`

**Parallelization**: All helper tasks can run as a single batch (same file, sequential lines, one agent).

| Task ID | Name | Description | Acceptance Criteria | Est | Assigned To |
|---------|------|-------------|---------------------|-----|-------------|
| TASK-1.1 | Audit helper session calls | Read lines 244-513 of `user_collections.py`; list each `session.execute` / `session.flush` call with its SQL intent and the repository method it maps to (or a proposed new method name) | Audit list produced; each call mapped to a repo method or flagged for addition | 0.5 pt | python-backend-engineer |
| TASK-1.2 | Add missing repository methods | If TASK-1.1 identifies gaps, add the required methods to `IDbUserCollectionRepository` or `IDbCollectionArtifactRepository` ABC in `skillmeat/core/interfaces/repositories.py` and implement them in `skillmeat/cache/repositories.py` | New methods present in ABC and implementation; existing tests still pass | 0.5 pt | python-backend-engineer |
| TASK-1.3 | Migrate helper functions | Replace all `session.execute` / `session.flush` calls in the helper functions (lines 244-513) with repository method calls; update helper signatures to accept repo deps instead of raw session | Zero `session.execute` / `session.flush` in lines 244-513; helpers return correct results | 1 pt | python-backend-engineer |

**Phase 1 Quality Gates:**
- [ ] Zero `session.execute` / `session.flush` in helper functions (lines 244-513)
- [ ] `pytest tests/` passes with no new failures
- [ ] Helper function signatures accept repository DI parameters

---

### Phase 2: Endpoint Migration — user_collections.py

**Entry Criteria**: Phase 1 complete; helper functions migrated.
**Exit Criteria**: Zero `session.execute` / `session.flush` / `db_session.execute` / `db_session.flush` anywhere in `user_collections.py`.
**Duration**: 1-2 days
**Dependencies**: Phase 1 (helpers migrated so endpoints calling helpers are already partially cleaned)
**Assigned To**: `python-backend-engineer`

**Parallelization**: Batches 2A-2D touch different line ranges and different endpoint groups — they can run in parallel if a second agent is available, but a single agent is sufficient given the sequential nature of one file.

**Violation groups by line range:**

- **Batch 2A** (lines 703-900): `session.execute` at 703, 716, 763, 824, 838; `session.flush` at 855
- **Batch 2B** (lines 990-1300): `session.execute` at 993, 1013, 1185; `session.flush` at 1234
- **Batch 2C** (lines 1700-1900): `session.execute` at 1750, 1766, 1782, 1823, 1842, 1852, 1881
- **Batch 2D** (lines 2500-3250): `session.execute` at 2592, 2606; `db_session.execute` at 2758, 2777; `db_session.flush` at 2869; `session.execute` at 3202, 3220, 3231

| Task ID | Name | Description | Acceptance Criteria | Est | Assigned To |
|---------|------|-------------|---------------------|-----|-------------|
| TASK-2.1 | Migrate endpoints — Batch 2A (lines 703-900) | Replace 5x `session.execute` and 1x `session.flush` in endpoints around lines 703-900; update endpoint signatures to use `DbUserCollectionRepoDep` / `DbCollectionArtifactRepoDep` | No raw session calls remain in lines 703-900 | 0.5 pt | python-backend-engineer |
| TASK-2.2 | Migrate endpoints — Batch 2B (lines 990-1300) | Replace 3x `session.execute` and 1x `session.flush` in endpoints around lines 990-1300 | No raw session calls remain in lines 990-1300 | 0.5 pt | python-backend-engineer |
| TASK-2.3 | Migrate endpoints — Batch 2C (lines 1700-1900) | Replace 7x `session.execute` in endpoints around lines 1700-1900 (membership/sharing operations) | No raw session calls remain in lines 1700-1900 | 0.5 pt | python-backend-engineer |
| TASK-2.4 | Migrate endpoints — Batch 2D (lines 2500-3250) | Replace 9x `session.execute` / `db_session.execute` / `db_session.flush` calls in endpoints around lines 2500-3250 | No raw session calls remain in lines 2500-3250 | 1 pt | python-backend-engineer |
| TASK-2.5 | Remove unused imports in user_collections.py | After migration, remove any ORM model imports from `skillmeat.cache.models` that are no longer referenced directly (were only used in raw queries) | `flake8 --select=F401` reports no unused imports in this file | 0.5 pt | python-backend-engineer |

**Phase 2 Quality Gates:**
- [ ] `grep -n "session\.execute\|session\.flush\|db_session\.execute\|db_session\.flush" skillmeat/api/routers/user_collections.py` returns zero matches
- [ ] `pytest tests/` passes with no new failures
- [ ] No unused ORM model imports remain

---

### Phase 3: artifact_history.py Migration

**Entry Criteria**: Repository infrastructure in place (independent of Phases 1-2).
**Exit Criteria**: Zero `session.execute` / `db_session.execute` in `artifact_history.py`.
**Duration**: 0.5 day
**Dependencies**: None (can run in parallel with Phase 2)
**Assigned To**: `python-backend-engineer`

**Violations:**
- Line 133: `session.execute(`
- Line 407: `db_session.execute(`
- Line 422: `db_session.execute(`

**Note**: `artifact_history.py` likely queries `ArtifactHistory` ORM model. If no existing repository covers it, add a minimal method to the most appropriate repository ABC (or a new `IArtifactHistoryRepository` if the pattern warrants). Check `skillmeat/core/interfaces/repositories.py` and `skillmeat/cache/repositories.py` before adding new ABCs.

| Task ID | Name | Description | Acceptance Criteria | Est | Assigned To |
|---------|------|-------------|---------------------|-----|-------------|
| TASK-3.1 | Audit artifact_history session calls | Read lines 133, 407, 422 of `artifact_history.py`; identify SQL intent and the repository / method to use; determine if a new method or new repository ABC is needed | Audit complete; repo method identified or gap flagged | 0.5 pt | python-backend-engineer |
| TASK-3.2 | Add repository method(s) if needed | If TASK-3.1 identifies a gap, add the method to the relevant ABC and implementation | New methods compile and are tested | 0.5 pt | python-backend-engineer |
| TASK-3.3 | Migrate artifact_history.py | Replace 3x raw session calls (lines 133, 407, 422) with repository method calls; update function signatures to use DI | Zero `session.execute` / `db_session.execute` in `artifact_history.py`; `pytest tests/` passes | 0.5 pt | python-backend-engineer |

**Phase 3 Quality Gates:**
- [ ] `grep -n "session\.execute\|db_session\.execute" skillmeat/api/routers/artifact_history.py` returns zero matches
- [ ] `pytest tests/` passes with no new failures

---

### Phase 4: Validation and Audit

**Entry Criteria**: Phases 1, 2, and 3 all complete.
**Exit Criteria**: Full grep audit confirms zero violations across all router files; test suite green.
**Duration**: 0.5 day
**Dependencies**: Phases 1, 2, 3
**Assigned To**: `task-completion-validator`

**Parallelization**: All validation tasks can run sequentially by one agent.

| Task ID | Name | Description | Acceptance Criteria | Est | Assigned To |
|---------|------|-------------|---------------------|-----|-------------|
| TASK-4.1 | Full grep audit — router directory | Run grep for all prohibited session patterns across `skillmeat/api/routers/`: `session.execute`, `session.flush`, `session.query`, `session.add`, `session.commit`, `session.delete`, `db_session.execute`, `db_session.flush` | Zero matches in any router file | 0.5 pt | task-completion-validator |
| TASK-4.2 | Run test suite | Execute `pytest tests/ -v` and confirm no regressions introduced by the migration | All tests pass (or pre-existing failures match baseline) | 0.5 pt | task-completion-validator |
| TASK-4.3 | Confirm no unused imports | Run `flake8 skillmeat/api/routers/user_collections.py skillmeat/api/routers/artifact_history.py --select=F401` | No unused import warnings in either file | 0.5 pt | task-completion-validator |

**Phase 4 Quality Gates:**
- [ ] Zero prohibited session patterns in any router file
- [ ] `pytest tests/` passes
- [ ] No unused imports in migrated files
- [ ] `enterprise-db-storage-v1` PRD unblocked (repository pattern violations = 0)

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| A raw session call performs a query with no equivalent repository method | Medium | Low | Add the method to the ABC + implementation in the same task; keep it minimal (1-2 lines) |
| Helper function signature change breaks endpoint callers | Medium | Medium | Update all callers in the same agent task; search for call sites before changing signatures |
| artifact_history.py requires a new repository ABC | Low | Low | Add a thin `IArtifactHistoryRepository` only if 2+ methods needed; otherwise add to nearest existing repo |
| Test suite has pre-existing failures masking regressions | Low | Low | Run baseline `pytest` before starting Phase 1 to record existing failures; compare post-migration |

---

## Success Metrics

- **Zero violations**: `grep` audit returns zero raw session calls in all router files
- **Green tests**: `pytest tests/` passes with no new failures
- **PRD unblocked**: `enterprise-db-storage-v1` can proceed without repository pattern blockers
- **Lean scope**: No new infrastructure added beyond what is strictly needed to replace the 39 violations

---

**Progress Tracking:**

See `.claude/progress/repo-pattern-final-cleanup/` (create when starting Phase 1).

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-06
