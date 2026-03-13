---
title: 'Implementation Plan: Enterprise Router Migration'
schema_version: 2
doc_type: implementation_plan
status: in-progress
created: 2026-03-12
updated: '2026-03-12'
feature_slug: enterprise-router-migration
feature_version: v1
prd_ref: null
plan_ref: null
scope: Migrate 9 routers from filesystem managers to repository DI for enterprise
  mode compatibility
effort_estimate: 21 pts
architecture_summary: Replace CollectionManagerDep/ArtifactManagerDep reads with *RepoDep
  in all routers; make AppState edition-aware
related_documents:
- .claude/agent-memory/codebase-explorer/enterprise_router_miswiring.md
- .claude/findings/ENTERPRISE_ROUTER_AUDIT.md
- .claude/findings/MANAGER_MIGRATION_MATRIX.md
owner: python-backend-engineer
contributors:
- refactoring-expert
- code-reviewer
priority: high
risk_level: low
category: product-planning
tags:
- refactoring
- enterprise
- repository-di
- router-migration
milestone: null
commit_refs:
- f301e229
pr_refs: []
files_affected:
- skillmeat/api/dependencies.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/routers/health.py
- skillmeat/api/routers/mcp.py
- skillmeat/api/routers/user_collections.py
- skillmeat/api/routers/deployment_sets.py
- skillmeat/api/routers/tags.py
- skillmeat/api/routers/marketplace_sources.py
- skillmeat/api/routers/match.py
- skillmeat/api/routers/deployments.py
---

# Implementation Plan: Enterprise Router Migration

**Plan ID**: `IMPL-2026-03-12-enterprise-router-migration`
**Date**: 2026-03-12
**Author**: Opus (orchestrator)
**Related Documents**:
- **Audit**: `.claude/findings/ENTERPRISE_ROUTER_AUDIT.md`
- **Gotcha**: `.claude/agent-memory/codebase-explorer/enterprise_router_miswiring.md`
- **Immediate fix**: commit `f301e229` (entrypoint + FilesystemErrorMiddleware)

**Complexity**: Medium
**Total Estimated Effort**: 21 story points
**Target Timeline**: 3-5 sessions

## Executive Summary

Nine API routers use `CollectionManagerDep` and `ArtifactManagerDep` for read operations. These managers only access the filesystem. In enterprise mode (PostgreSQL), data lives in the DB, causing silent failures or errors. This plan migrates all filesystem reads to edition-aware repository DI (`*RepoDep`), makes `AppState` edition-aware, and adds proper feature gating for filesystem-only operations.

## Implementation Strategy

### Architecture Sequence

This is a pure refactoring - no new tables, schemas, or features. The work follows a simple pattern:

```
1. AppState → make managers conditional by edition
2. Routers → replace manager reads with *RepoDep
3. Utilities → migrate shared helper functions
4. Test → verify enterprise mode works end-to-end
```

### Migration Pattern (Copy-Paste Ready)

Every migration follows the same pattern:

```python
# BEFORE (broken in enterprise):
async def endpoint(
    collection_mgr: CollectionManagerDep,
    ...
):
    collections = collection_mgr.list_collections()
    coll = collection_mgr.load_collection(name)
    artifact = coll.find_artifact(name, type)

# AFTER (works in both modes):
async def endpoint(
    collection_repo: CollectionRepoDep,
    artifact_repo: ArtifactRepoDep,
    settings: SettingsDep,
    ...
):
    collections = collection_repo.list()
    artifact = artifact_repo.get(type, name)
```

For filesystem-only features (discovery, scanning):

```python
# AFTER (graceful degradation):
async def endpoint(
    settings: SettingsDep,
    artifact_mgr: ArtifactManagerDep,
    ...
):
    if settings.edition == "enterprise":
        raise HTTPException(
            status_code=501,
            detail="Discovery is not available in enterprise edition"
        )
    # ... existing filesystem logic
```

### Critical Path

```
Phase 1 (AppState) → Phase 2 (P0 routers) → Phase 3 (P1 routers) → Phase 4 (Validation)
```

All phases are sequential - Phase 1 enables Phases 2-3, Phase 4 validates everything.

### Parallel Work Opportunities

Within Phase 2 and Phase 3, individual router migrations are independent and can be parallelized:
- Phase 2: artifacts.py, marketplace_sources.py, match.py (3 parallel tasks)
- Phase 3: tags.py, user_collections.py, deployment_sets.py, deployments.py, mcp.py, health.py (6 parallel tasks)

---

## Phase Overview

| Phase | Title | Effort | Tasks | Assignee |
|-------|-------|--------|-------|----------|
| 1 | AppState Edition-Awareness | 3 pts | 2 | python-backend-engineer |
| 2 | P0 Router Migration (Broken) | 8 pts | 3 | python-backend-engineer |
| 3 | P1/P2 Router Migration (Degraded) | 7 pts | 6 | python-backend-engineer |
| 4 | Validation & Cleanup | 3 pts | 3 | python-backend-engineer, code-reviewer |

---

## Phase 1: AppState Edition-Awareness (3 pts)

**Goal**: Make filesystem manager initialization conditional on edition, so enterprise mode doesn't depend on filesystem access.

**Entry Criteria**: None
**Exit Criteria**: Enterprise containers start without filesystem managers initialized

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assignee |
|----|------|-------------|---------------------|----------|----------|
| TASK-1.1 | Make AppState managers optional | In `dependencies.py`, make `collection_manager`, `artifact_manager`, `sync_manager`, and `context_sync_service` initialization conditional on `settings.edition != "enterprise"`. Set them to `None` in enterprise mode. | Enterprise containers start without PermissionError; `app_state.collection_manager is None` in enterprise | 2 pts | python-backend-engineer |
| TASK-1.2 | Guard manager dependency getters | Update `get_collection_manager()`, `get_artifact_manager()`, `get_sync_manager()` to raise `HTTPException(501)` with clear message when called in enterprise mode and manager is `None`. | Endpoints using ManagerDep in enterprise get 501 "Not available in enterprise" instead of crash | 1 pt | python-backend-engineer |

**Key Files**:
- `skillmeat/api/dependencies.py` (AppState.initialize, get_*_manager functions)

**Quality Gate**: Container starts in enterprise mode without filesystem errors.

---

## Phase 2: P0 Router Migration - Broken in Enterprise (8 pts)

**Goal**: Migrate the 3 routers that are completely broken in enterprise mode.

**Entry Criteria**: Phase 1 complete (managers guarded)
**Exit Criteria**: artifacts.py, marketplace_sources.py, match.py work in enterprise mode

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assignee |
|----|------|-------------|---------------------|----------|----------|
| TASK-2.1 | Migrate artifacts.py utilities | Migrate 3 utility functions that use filesystem managers for reads: `resolve_collection_name()` (~line 369), `_find_artifact_in_collections()` (~line 465), `build_version_graph()` (~line 679). Replace `collection_mgr.list_collections()` → `CollectionRepoDep.list()`, `collection_mgr.load_collection()` → `ArtifactRepoDep`, `artifact_history` → `DbArtifactHistoryRepoDep`. Also gate `discover()` and `discover_in_project()` endpoints with edition check (return 501 in enterprise). | All 3 utilities work with repo DI; discovery endpoints return 501 in enterprise | 3 pts | python-backend-engineer |
| TASK-2.2 | Migrate marketplace_sources.py helper | Migrate `get_collection_artifact_keys()` helper (~line 612) that uses `ArtifactManager.enumerate_all()`. Replace with `ArtifactRepoDep.list_by_collection()` or equivalent query. This helper is used by ~6 endpoints, so fixing it cascades. | Helper works in enterprise; all 6 dependent endpoints return correct data | 3 pts | python-backend-engineer |
| TASK-2.3 | Migrate match.py | Migrate single endpoint (~line 65) that uses `artifact_mgr.match()`. Replace with `ArtifactRepoDep.search()` or equivalent DB query. If no search method exists, implement a simple name-matching query on the repository. | Match endpoint returns results from DB in enterprise mode | 2 pts | python-backend-engineer |

**Key Files**:
- `skillmeat/api/routers/artifacts.py`
- `skillmeat/api/routers/marketplace_sources.py`
- `skillmeat/api/routers/match.py`
- `skillmeat/core/interfaces/repositories.py` (if new methods needed)
- `skillmeat/core/repositories/local_*.py` (if new methods needed)
- `skillmeat/cache/enterprise_repositories.py` (if new methods needed)

**Quality Gate**: All 3 routers respond correctly in enterprise mode (manual API test or pytest).

---

## Phase 3: P1/P2 Router Migration - Degraded in Enterprise (7 pts)

**Goal**: Migrate remaining routers that partially work or are degraded.

**Entry Criteria**: Phase 1 complete
**Exit Criteria**: All 6 remaining routers work in enterprise mode

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assignee |
|----|------|-------------|---------------------|----------|----------|
| TASK-3.1 | Migrate tags.py | ~4 READ operations use `CollectionManagerDep` for tag lookups. Replace with `TagRepoDep`. Keep ~2 WRITE operations that do filesystem write-through (but wrap in edition check - skip FS write in enterprise). | Tag CRUD works in enterprise; no filesystem access in enterprise mode | 2 pts | python-backend-engineer |
| TASK-3.2 | Migrate user_collections.py | ~3 READ operations use managers. Replace with `DbUserCollectionRepoDep` / `DbCollectionArtifactRepoDep`. ~5 WRITE operations need edition-conditional filesystem write-through (skip FS in enterprise, write DB only). | Collection operations work in enterprise | 2 pts | python-backend-engineer |
| TASK-3.3 | Migrate deployment_sets.py | Audit and migrate any `CollectionManagerDep`/`ArtifactManagerDep` reads. Replace with `DeploymentRepoDep` or appropriate repo. | Deployment sets work in enterprise | 1 pt | python-backend-engineer |
| TASK-3.4 | Migrate deployments.py | Audit and migrate any manager reads. Replace with `DeploymentRepoDep`. | Deployments work in enterprise | 1 pt | python-backend-engineer |
| TASK-3.5 | Clean up health.py | Already has edition-aware check for collection_manager in detailed health. Remove `CollectionManagerDep` from function signature in enterprise-only code paths (readiness check still injects it unnecessarily). | Health endpoints don't trigger filesystem access in enterprise | 0.5 pts | python-backend-engineer |
| TASK-3.6 | Migrate mcp.py | ~3 READ operations and ~3 WRITE operations use `ArtifactManagerDep`. READs → `ArtifactRepoDep`. WRITEs → keep manager but gate behind edition check (MCP is filesystem-native, may need 501 in enterprise for write ops). | MCP reads work in enterprise; writes return 501 if not feasible | 0.5 pts | python-backend-engineer |

**Key Files**:
- `skillmeat/api/routers/tags.py`
- `skillmeat/api/routers/user_collections.py`
- `skillmeat/api/routers/deployment_sets.py`
- `skillmeat/api/routers/deployments.py`
- `skillmeat/api/routers/health.py`
- `skillmeat/api/routers/mcp.py`

**Quality Gate**: All routers respond correctly in enterprise mode.

---

## Phase 4: Validation & Cleanup (3 pts)

**Goal**: Verify all changes work end-to-end, clean up unused code, update docs.

**Entry Criteria**: Phases 2-3 complete
**Exit Criteria**: Enterprise mode fully functional; no unused manager imports

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assignee |
|----|------|-------------|---------------------|----------|----------|
| TASK-4.1 | Enterprise smoke test | Start enterprise docker-compose, hit all major API endpoints. Verify no 400/500 from filesystem errors. Test: list artifacts, list collections, search, tags CRUD, health checks. | All endpoints return valid responses (200/201/204) or proper 501 for unsupported features | 1 pt | python-backend-engineer |
| TASK-4.2 | Clean up unused imports | Remove unused `CollectionManagerDep` and `ArtifactManagerDep` imports from migrated routers. Remove unused manager methods if no longer called anywhere. Run `flake8` to verify. | No unused imports; flake8 passes | 1 pt | refactoring-expert |
| TASK-4.3 | Update gotcha doc | Update `.claude/agent-memory/codebase-explorer/enterprise_router_miswiring.md` to mark issue as resolved. Note which routers still use managers for writes (expected, with edition checks). | Gotcha doc reflects current state | 1 pt | documentation-writer |

**Quality Gate**: Enterprise docker-compose works end-to-end; no filesystem errors in logs.

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missing repository method | Medium | Low | Add method to interface + both implementations (local + enterprise). Pattern already established. |
| Write-through regression in local mode | Medium | Medium | Run existing pytest suite after each router migration. Local mode behavior must not change. |
| MCP endpoints incompatible with DB | Low | Low | Gate with 501; MCP is inherently filesystem-based. Enterprise users manage MCP differently. |

## Success Metrics

- **Zero filesystem errors** in enterprise container logs
- **All endpoints** return valid responses (200/201/204/501) - no 400/500 from permission errors
- **Existing tests pass** in local mode (no regression)
- **No CollectionManagerDep/ArtifactManagerDep** in router READ paths (only in edition-gated WRITE paths)

## Orchestration Quick Reference

```bash
# Phase 1 - AppState
Task("python-backend-engineer", "TASK-1.1 + TASK-1.2: Make AppState.initialize() edition-aware.
  File: skillmeat/api/dependencies.py
  1. In AppState.initialize(), wrap manager initialization in `if settings.edition != 'enterprise':`
  2. Guard get_collection_manager/get_artifact_manager/get_sync_manager to return 501 when None
  Pattern: See existing require_local_edition() at line 506", model="sonnet", mode="acceptEdits")

# Phase 2 - P0 Routers (parallel)
Task("python-backend-engineer", "TASK-2.1: Migrate artifacts.py utilities. [details]", model="sonnet", mode="acceptEdits")
Task("python-backend-engineer", "TASK-2.2: Migrate marketplace_sources.py. [details]", model="sonnet", mode="acceptEdits")
Task("python-backend-engineer", "TASK-2.3: Migrate match.py. [details]", model="sonnet", mode="acceptEdits")

# Phase 3 - P1/P2 Routers (parallel)
Task("python-backend-engineer", "TASK-3.1-3.6: Migrate remaining routers. [details]", model="sonnet", mode="acceptEdits")

# Phase 4 - Validation
Task("refactoring-expert", "TASK-4.2: Clean up unused imports", model="sonnet", mode="acceptEdits")
Task("documentation-writer", "TASK-4.3: Update gotcha doc", model="haiku", mode="acceptEdits")
```
