---
schema_version: 2
doc_type: implementation_plan
title: "Implementation Plan: DB Repository Migration \u2014 Complete Session Cleanup"
status: in-progress
created: 2026-03-05
updated: '2026-03-05'
feature_slug: db-user-collection-repository
feature_version: v1
prd_ref: null
plan_ref: null
scope: Create IDbUserCollectionRepository + IDbCollectionArtifactRepository ABCs,
  implement concrete DB-backed repositories with full transactional session management,
  wire DI factories, migrate all 16 user_collections.py endpoints to zero direct SQLAlchemy
  session usage; also clean up 21 residual session.query() calls in artifacts.py (15),
  artifact_history.py (2), deployment_profiles.py (2), projects.py (1), tags.py (1)
  from gap-closure Phases 4-6 over-claims
effort_estimate: 22 pts
architecture_summary: New DB-specific repository ABCs for Collection and CollectionArtifact
  domains, concrete implementations in cache/repositories.py using SQLAlchemy session
  management pattern, DI factory wiring with typed aliases, full router migration
  eliminating 110+ direct session calls, plus residual cleanup of 21 session.query()
  calls in 5 other routers
related_documents:
- docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md
- docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
owner: null
contributors: []
priority: high
risk_level: medium
category: refactors
tags:
- implementation
- planning
- repository-pattern
- user-collections
- db-migration
- hexagonal-architecture
- residual-cleanup
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/core/interfaces/repositories.py
- skillmeat/core/interfaces/dtos.py
- skillmeat/cache/repositories.py
- skillmeat/api/dependencies.py
- skillmeat/api/routers/user_collections.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/routers/artifact_history.py
- skillmeat/api/routers/deployment_profiles.py
- skillmeat/api/routers/projects.py
- skillmeat/api/routers/tags.py
- tests/mocks/repositories.py
---

# Implementation Plan: DB User Collection Repository Migration

**Plan ID**: `IMPL-2026-03-05-DB-USER-COLLECTION-REPO`
**Date**: 2026-03-05
**Author**: Opus orchestrator
**Related Documents**:
- **Parent gap-closure**: `docs/project_plans/implementation_plans/refactors/repo-pattern-gap-closure-v1.md` (TASK-4.1)
- **Enables**: `docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md`
- **Foundational refactor**: `docs/project_plans/implementation_plans/refactors/repo-pattern-refactor-v1.md`

**Complexity**: Medium
**Total Estimated Effort**: 19 story points
**Target Timeline**: 1-2 weeks

---

## Executive Summary

`skillmeat/api/routers/user_collections.py` (3,195 lines) operates directly on SQLAlchemy session across 16 endpoints with ~110 direct session calls. The file manages DB-backed `Collection` and `CollectionArtifact` ORM models (tables: `collections`, `collection_artifacts`, `collection_artifact_sources`) — distinct from filesystem collections.

The existing `ICollectionRepository` in the codebase targets **filesystem collections** and is incompatible with DB-backed user collections. This plan introduces two new repository ABCs:

- `IDbUserCollectionRepository` — CRUD + aggregation operations on `Collection` model
- `IDbCollectionArtifactRepository` — Membership + metadata operations on `CollectionArtifact` model

Concrete implementations follow the `LocalGroupRepository` pattern: transactional session management, DTO-returning methods, no ORM leakage. Upon completion, user_collections.py will have zero direct session usage, fully unblocking the enterprise-db-storage refactor.

Additionally, the Phase 7 validation audit of the parent gap-closure plan identified **21 residual `session.query()` calls** across 5 routers that were over-claimed as complete in Phases 4-6:

| Router | Calls | Original Task |
|--------|-------|---------------|
| `artifacts.py` | 15 | TASK-4.3 (gap-closure) |
| `artifact_history.py` | 2 | Not in original scope |
| `deployment_profiles.py` | 2 | TASK-6.3 (gap-closure) |
| `projects.py` | 1 | Not in original scope |
| `tags.py` | 1 | Not in original scope |

These are added as Phase 6 of this plan to achieve the full zero-session-usage goal across ALL routers.

### Key Constraints

- **No endpoint signature changes** — OpenAPI contract remains unchanged
- **No collection_artifacts table schema changes** — Use existing fields as-is
- **Session management pattern** — Match LocalGroupRepository: open → work → commit/rollback → close in try/finally
- **DTO conversion** — All returns must be immutable dataclass instances, never ORM models
- **File location** — DB repos live in `skillmeat/cache/repositories.py`, not `core/repositories/`

---

## Implementation Strategy

### Architecture Sequence

1. **DTO & ABC Layer (Phase 1)** — Define `UserCollectionDTO`, `CollectionArtifactDTO`, and the two new repository interfaces
2. **Concrete Repositories (Phase 2)** — Implement `DbUserCollectionRepository` and `DbCollectionArtifactRepository` in `cache/repositories.py` with full transactional patterns
3. **DI Wiring (Phase 3)** — Add factory providers and typed aliases; register in dependencies.py and __init__.py exports
4. **Router Migration — Core (Phase 4)** — Migrate helper functions and CRUD endpoints (list, create, get, update, delete)
5. **Router Migration — Complex (Phase 5)** — Migrate collection artifact operations and sync/cache functions; validate zero session usage
6. **Residual Router Cleanup (Phase 6)** — Migrate 21 remaining session.query() calls in artifacts.py, artifact_history.py, deployment_profiles.py, projects.py, tags.py using existing DI infrastructure

### Critical Path & Parallelization

- **Phase 1 → Phase 2 → Phase 3** strictly sequential (Phase 3 DI depends on Phase 2 implementations)
- **Phases 4–5** depend on Phase 3 completion; within each phase, tasks can parallelize where independent
- **Phase 4 tasks**: TASK-4.1 (helpers) **must complete before** TASK-4.2/4.3 (endpoints using helpers)
- **Phase 5 tasks**: TASK-5.1 and TASK-5.2 can run in parallel; TASK-5.3 (validation) depends on both
- **Phase 6 tasks**: TASK-6.1/6.2/6.3 can run in parallel with Phases 4-5 (different routers); TASK-6.4 (cross-router validation) depends on completion of both Phase 5 and TASK-6.1-6.3

### Reference Implementation

All repositories follow the `LocalGroupRepository` pattern in `skillmeat/core/repositories/local_group.py` (~250 lines):
- Session lifecycle: `session = self._get_session()` → try/finally with close()
- For mutations: commit on success, rollback on exception
- DTO conversion from ORM: helper functions like `_group_to_dto()` and `_group_artifact_to_dto()`
- Exception handling: raise plain Python exceptions (RuntimeError, KeyError, ValueError) — router handles HTTPException translation

---

## Phase Breakdown

### Phase 1: DTO & Interface Layer (3 pts, 1 day)

**Dependencies**: None
**Assigned**: python-backend-engineer

**Objective**: Define immutable DTOs and new repository ABCs.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|---|
| TASK-1.1 | Create `UserCollectionDTO` & `CollectionArtifactDTO` in dtos.py | Define two new frozen dataclasses in `skillmeat/core/interfaces/dtos.py`. **UserCollectionDTO**: id, name, description, created_by, collection_type, context_category, created_at, updated_at, artifact_count (derived). **CollectionArtifactDTO**: collection_id, artifact_uuid, added_at, description, author, license, tags (List[str]), tools (List[str]), deployments (List[str]), artifact_content_hash, artifact_structure_hash, artifact_file_count, artifact_total_size, source, origin, resolved_sha, resolved_version, synced_at. Add both to `__all__` export. | Both DTOs frozen, importable from `skillmeat.core.interfaces`, type hints correct, `__all__` updated | 1 pt | None |
| TASK-1.2 | Create `IDbUserCollectionRepository` ABC in repositories.py | New ABC in `skillmeat/core/interfaces/repositories.py` with 11 abstract methods: `list()` (with filters/pagination), `get_by_id()`, `create()`, `update()`, `delete()`, `ensure_default()`, `list_with_artifact_stats()`, `add_group()`, `remove_group()`, `get_groups()`, `get_artifact_count()`. All raise `NotImplementedError`, follow ABC conventions (ctx parameter optional at end). | ABC defined; all methods abstract; importable from `skillmeat.core.interfaces`; mypy passes | 1 pt | TASK-1.1 |
| TASK-1.3 | Create `IDbCollectionArtifactRepository` ABC in repositories.py | New ABC with 9 methods: `list_by_collection()`, `add_artifacts()`, `remove_artifact()`, `get_by_pk()`, `upsert_metadata()`, `list_with_tags()`, `count_by_collection()`, `update_source_tracking()`, `list_deployment_info()`. All raise `NotImplementedError`, follow conventions. | ABC defined; all 9 methods abstract; importable; mypy passes | 1 pt | TASK-1.1 |

**Phase 1 Quality Gates**:
- Both DTOs frozen and importable from `skillmeat.core.interfaces`
- Both ABCs importable from `skillmeat.core.interfaces`
- Type hints reference existing DTOs (ArtifactDTO, etc.) and standard types
- `mypy skillmeat/core/interfaces/ --ignore-missing-imports` passes
- All new methods decorated with `@abc.abstractmethod` and raise `NotImplementedError`

---

### Phase 2: Concrete Repository Implementation (6 pts, 2-3 days)

**Dependencies**: Phase 1 complete
**Assigned**: python-backend-engineer

**Objective**: Implement DbUserCollectionRepository and DbCollectionArtifactRepository in cache/repositories.py following LocalGroupRepository session management patterns.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|---|
| TASK-2.1 | Implement `DbUserCollectionRepository` in cache/repositories.py | Create new class implementing `IDbUserCollectionRepository`. Follow LocalGroupRepository pattern: define helper `_collection_to_dto()` for ORM→DTO conversion; implement all 11 methods with transactional session lifecycle (session = get_session(); try: ... finally: session.close()). For mutations: commit on success, catch exceptions, rollback, re-raise as RuntimeError/ValueError. Extract logic from user_collections.py endpoints: `ensure_default_collection()`, collection listing, filtering by type/category, artifact stats joins | All 11 methods implemented; session lifecycle correct; DTO conversion clean; unit tests cover CRUD + stats queries; no direct routers access | 3.5 pts | TASK-1.2 |
| TASK-2.2 | Implement `DbCollectionArtifactRepository` in cache/repositories.py | Create new class implementing `IDbCollectionArtifactRepository`. Define helper `_collection_artifact_to_dto()`. Implement all 9 methods. Extract from user_collections.py: `list_collection_artifacts()` with complex joins (tags, deployments, source tracking), `add_artifacts_to_collection()` with multi-insert + metadata population, `remove_artifact_from_collection()`, metadata upserting (fingerprints, source, resolved version). Handle tags_json, tools_json, deployments_json JSON parsing/serialization. | All 9 methods implemented; JSON field parsing handles null/invalid gracefully; multi-artifact operations transactional; unit tests for join queries + JSON handling; no router access | 2.5 pts | TASK-1.3 |

**Phase 2 Quality Gates**:
- Both classes inherit from `IDbUserCollectionRepository` and `IDbCollectionArtifactRepository` respectively
- Session lifecycle verified: no session leaks, try/finally ensures close()
- All mutations commit on success, rollback on error
- DTO conversion helpers exist and are tested
- Unit tests pass with 80%+ coverage for both classes
- No Pydantic models in return types — only DTOs

---

### Phase 3: DI Wiring & Test Mocks (2 pts, 1 day)

**Dependencies**: Phase 2 complete
**Assigned**: python-backend-engineer

**Objective**: Wire DI factories, create typed aliases, update mocks.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|---|
| TASK-3.1 | Add DI factory providers in dependencies.py | Add two functions to `skillmeat/api/dependencies.py`: `get_db_user_collection_repository()` and `get_db_collection_artifact_repository()`. Each opens session, creates instance, returns repo. Edition-agnostic (no edition check needed — DB repos are always available). | Functions defined; resolve correctly in FastAPI context; return correct instances | 0.5 pts | TASK-2.2 |
| TASK-3.2 | Register typed DI aliases | Add two `Annotated` aliases in dependencies.py: `DbUserCollectionRepoDep = Annotated[IDbUserCollectionRepository, Depends(get_db_user_collection_repository)]` and `DbCollectionArtifactRepoDep = Annotated[IDbCollectionArtifactRepository, Depends(get_db_collection_artifact_repository)]` | Both aliases defined; clean syntax; used in router signatures | 0.5 pts | TASK-3.1 |
| TASK-3.3 | Update exports in __init__.py files | Update `skillmeat/core/interfaces/__init__.py` to export `IDbUserCollectionRepository`, `IDbCollectionArtifactRepository`. Update `skillmeat/cache/repositories.py` `__all__` to export both concrete classes. | Imports from both modules clean; subagent unit tests verify | 0.5 pts | TASK-3.1 |
| TASK-3.4 | Add mock implementations in tests/mocks/repositories.py | Create `MockDbUserCollectionRepository` and `MockDbCollectionArtifactRepository` implementing full ABCs. Support in-memory collections dict; return pre-built DTOs or raise mocked exceptions. | Mock classes implement 100% of ABCs; used in test fixtures; no NotImplementedError exceptions | 0.5 pts | TASK-3.2 |

**Phase 3 Quality Gates**:
- Both DI aliases resolve in running FastAPI app (`python -c "from skillmeat.api.dependencies import DbUserCollectionRepoDep; print(DbUserCollectionRepoDep)"`)
- All imports work from public module locations
- Mock classes pass unit tests as drop-in replacements
- `pytest tests/mocks/ -v` passes

---

### Phase 4: Router Migration — Core CRUD (5 pts, 2 days)

**Dependencies**: Phase 3 complete
**Assigned**: python-backend-engineer

**Objective**: Migrate helper functions and CRUD endpoints in user_collections.py; remove DI-unused imports.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|---|
| TASK-4.1 | Migrate helper functions | Update `collection_to_response()`, `ensure_default_collection()`, `_ensure_collection_project_sentinel()` to use `DbUserCollectionRepoDep` + `DbCollectionArtifactRepoDep` instead of direct session. Remove `from skillmeat.cache.models import get_session` and direct `session.query()` calls. Update logic to consume DTOs from repos. Keep response shape identical. | Helpers use only DI repos; signatures unchanged; response shapes identical; grep finds zero `session.query` in migrated functions | 1.5 pts | TASK-3.3 |
| TASK-4.2 | Migrate list/create/get/update/delete collection endpoints | Migrate 10 endpoints: `list_user_collections()`, `create_user_collection()`, `get_user_collection()`, `update_user_collection()`, `delete_user_collection()`, plus 5 minor group-related endpoints. Replace all session calls with repo method calls. Inject `DbUserCollectionRepoDep` + `DbCollectionArtifactRepoDep`. Maintain OpenAPI contract (no signature changes). | Zero `session.query/add/commit` in these 10 endpoints; all tests pass; OpenAPI unchanged; responses identical | 2.5 pts | TASK-4.1 |
| TASK-4.3 | Remove direct session imports from migrated paths | Search user_collections.py for imports no longer used: `from sqlalchemy.orm import Session`, `from skillmeat.cache import get_session`, `from skillmeat.cache.models import ...` (only keep necessary for request schema validation). Verify no leftover direct session usage. | Zero `DbSessionDep` injection in endpoints; unused imports removed; grep audit clean | 1 pt | TASK-4.2 |

**Phase 4 Quality Gates**:
- `grep -n "session.query\|session.add\|session.commit\|get_session\|DbSessionDep" skillmeat/api/routers/user_collections.py` returns only comment references (no code matches)
- All CRUD endpoint tests pass: `pytest tests/api/test_user_collections.py -v`
- OpenAPI spec unchanged: `diff -u <(git show HEAD:skillmeat/api/openapi.json) skillmeat/api/openapi.json` shows no endpoint changes
- 100% of migrated endpoints use only DI repo aliases

---

### Phase 5: Router Migration — Complex Operations & Validation (3 pts, 2 days)

**Dependencies**: Phase 4 complete
**Assigned**: python-backend-engineer (5.1, 5.2), task-completion-validator (5.3)

**Objective**: Migrate remaining complex endpoints (artifact operations, cache/sync); validate zero session usage.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|---|
| TASK-5.1 | Migrate collection artifact endpoints | Migrate 6 endpoints: `list_collection_artifacts()` (complex multi-table join), `add_artifacts_to_collection()` (batch insert + metadata), `remove_artifact_from_collection()`, plus 3 artifact metadata/deployment endpoints. These use `DbCollectionArtifactRepoDep`. Replace 40+ direct session calls with repo method calls. Handle pagination, filtering, stats aggregation through repo layer. | Zero `session.query` in these endpoints; complex joins delegated to repo; batch operations atomic; pagination/stats work via DTO returns; tests pass | 1.5 pts | TASK-4.3 |
| TASK-5.2 | Migrate cache/sync endpoints | Migrate remaining endpoints: `refresh_collection_cache()`, `populate_collection_artifact_metadata()`, `_sync_all_tags_to_orm()`, `migrate_artifacts_to_default_collection()`, `_refresh_single_collection_cache()`. These coordinate repos + other services. Replace 30+ direct session calls. Keep refresh logic intact; delegate ORM operations to repos. | Endpoints use repos for all ORM access; refresh semantics preserved (idempotent); no direct session calls; cache operations still work; all tests pass | 1 pt | TASK-4.3 |
| TASK-5.3 | Validation — grep audit, tests, OpenAPI diff | Run grep audit to confirm zero `session.query/add/commit` in entire user_collections.py (except comments/docstrings). Run full pytest suite to verify all 16 endpoints work. Diff OpenAPI to confirm contract unchanged. Document findings. | Grep audit: zero direct session matches. Pytest: all user_collections tests pass. OpenAPI: no endpoint/schema changes. Validation report generated. | 0.5 pts | TASK-5.2 |

**Phase 5 Quality Gates**:
- **Final grep audit passes**: `grep -rn "session\\.query\|session\\.add\|session\\.commit\|session\\.execute\|get_session" skillmeat/api/routers/user_collections.py | grep -v "^[^:]*:[0-9]*:\s*#"` returns ZERO matches
- **Full test suite passes**: `pytest tests/api/test_user_collections.py -v --tb=short` (all 16 endpoints tested)
- **OpenAPI contract stable**: `diff <(git show HEAD:skillmeat/api/openapi.json | jq '.paths."/api/v1/user-collections"') <(jq '.paths."/api/v1/user-collections"' skillmeat/api/openapi.json)` shows no changes
- **All migrations complete**: No remaining TODO comments about session migration in user_collections.py

---

### Phase 6: Residual Router Cleanup (3 pts, 1 day)

**Dependencies**: Phase 3 complete (DI infrastructure already exists for these repos)
**Assigned**: python-backend-engineer (6.1-6.3), task-completion-validator (6.4)

**Objective**: Clean up 21 residual session.query() calls in 5 routers that were over-claimed in gap-closure Phases 4-6. These routers already have DI aliases available — the work is replacing direct session calls with existing repo method calls.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|---|
| TASK-6.1 | Migrate artifacts.py residual calls (15 calls) | Replace 15 session.query() calls in artifacts.py. These include: Collection queries (~3 calls around lines 375, 8553, 8561), Artifact queries (~6 calls around lines 9009, 9078, 9423, 9472, 9629, 9678), CollectionArtifact queries (~3 calls around lines 9122, 9237), DuplicatePair queries (~3 calls around lines 2181, 2283, 9440, 9646). Use existing `ArtifactRepoDep`, `CollectionRepoDep`, and create new repo methods if needed on existing ABCs. | Zero session.query() in artifacts.py; all tests pass; OpenAPI unchanged | 1.5 pts | TASK-3.3 |
| TASK-6.2 | Migrate artifact_history.py (2 calls) | Replace 2 session.query() calls: ArtifactVersion query (line ~129) and CacheArtifact query (line ~402). Use existing `ArtifactRepoDep` or extend ABC if needed. | Zero session.query() in artifact_history.py; tests pass | 0.5 pts | TASK-3.3 |
| TASK-6.3 | Migrate deployment_profiles.py, projects.py, tags.py (4 calls total) | deployment_profiles.py: 2 Project queries (lines ~65, ~77) — use `ProjectRepoDep`. projects.py: 1 Project query (line ~293) — use `ProjectRepoDep`. tags.py: 1 Collection query (line ~95) — use `CollectionRepoDep`. | Zero session.query() in all 3 files; tests pass | 0.5 pts | TASK-3.3 |
| TASK-6.4 | Cross-router validation audit | Run comprehensive grep across ALL routers: `grep -rn "session\.query\|session\.add\|session\.commit\|get_session" skillmeat/api/routers/ \| grep -v "^[^:]*:[0-9]*:\s*#"`. Only whitelisted exception imports should remain. Verify zero code-level session usage in all router files. Run full pytest suite. | Grep audit: zero code matches across all routers (comments OK). Full pytest passes. OpenAPI unchanged. | 0.5 pts | TASK-6.1, TASK-6.2, TASK-6.3 |

**Phase 6 Quality Gates**:
- `grep -rn "session\.query\|session\.add\|session\.commit" skillmeat/api/routers/ | grep -v "#"` returns ZERO matches
- All router test files pass
- OpenAPI spec unchanged
- Enterprise-db-storage prerequisite fully met: implementing 10+2 ABCs intercepts ALL data access

**Note**: Phase 6 tasks can run in parallel with Phases 4-5 since they target different routers. TASK-6.1-6.3 only depend on Phase 3 (DI infrastructure). The cross-router validation (TASK-6.4) should run after both Phase 5 and TASK-6.1-6.3 are complete.

---

## Effort Estimate Breakdown

| Phase | Tasks | Estimate | Duration |
|-------|-------|----------|----------|
| Phase 1: DTO & Interface | 3 tasks | 3 pts | 1 day |
| Phase 2: Concrete Repos | 2 tasks | 6 pts | 2-3 days |
| Phase 3: DI Wiring | 4 tasks | 2 pts | 1 day |
| Phase 4: Core CRUD Migration | 3 tasks | 5 pts | 2 days |
| Phase 5: Complex + Validation | 3 tasks | 3 pts | 2 days |
| Phase 6: Residual Router Cleanup | 4 tasks | 3 pts | 1 day |
| **Total** | **19 tasks** | **22 pts** | **~1.5-2.5 weeks** |

---

## Critical Implementation Notes

### ORM Fields & JSON Handling

The `CollectionArtifact` model has JSON-serialized fields:
- `tags_json` — JSON list of tag strings; parse to Python list in `_collection_artifact_to_dto()`
- `tools_json` — Similar; parse safely with `json.loads()` and fallback to `[]` on null
- `deployments_json` — Deployment summary objects; parse with error handling

**Pattern** (from existing code in user_collections.py):
```python
tags = json.loads(ca.tags_json) if ca.tags_json else []
tools = json.loads(ca.tools_json) if ca.tools_json else []
deployments = json.loads(ca.deployments_json) if ca.deployments_json else []
```

### Complex Queries to Extract

- **list_collection_artifacts()**: Joins `CollectionArtifact` → `Artifact` + aggregates tags + fingerprints + source tracking
- **add_artifacts_to_collection()**: Multi-row insert into `CollectionArtifact` + optional metadata population (fingerprints, source tracking, resolved version)
- **refresh_collection_cache()**: Syncs filesystem artifacts to `CollectionArtifact` rows; updates metadata from sources
- **populate_collection_artifact_metadata()**: Computes fingerprints (hash, structure, file count, size) and stores in DB

All should be in **repo methods**, not repeated in router.

### Session Lifecycle Pattern

From `LocalGroupRepository`:
```python
def list(self, filters=None, offset=0, limit=50, ctx=None):
    session = self._get_session()
    try:
        query = session.query(Group)
        # Apply filters, pagination
        groups = query.all()
        return [_group_to_dto(g) for g in groups]
    finally:
        session.close()

def create(self, name, description=None, ctx=None):
    session = self._get_session()
    try:
        group = Group(id=str(uuid.uuid4()), name=name, description=description, ...)
        session.add(group)
        session.commit()
        return _group_to_dto(group)
    except Exception:
        session.rollback()
        raise RuntimeError(f"Failed to create group: {e}")
    finally:
        session.close()
```

**Key points**:
1. Always `try/finally` with `session.close()` to prevent leaks
2. Mutations: `session.add()` → `session.commit()` on success; catch + rollback + re-raise on error
3. Return DTOs, never ORM models
4. Raise plain Python exceptions (RuntimeError, ValueError, KeyError) — router translates to HTTPException

### User Collections Endpoints Summary

| Endpoint | Method | CRUD Type | Session Calls | Repo Method(s) |
|----------|--------|-----------|---------------|---|
| `/user-collections` | GET | List | 10+ | `list()`, `list_with_artifact_stats()` |
| `/user-collections` | POST | Create | 5+ | `create()`, `ensure_default()` |
| `/user-collections/{id}` | GET | Read | 3+ | `get_by_id()` |
| `/user-collections/{id}` | PUT | Update | 5+ | `update()`, `get_groups()` |
| `/user-collections/{id}` | DELETE | Delete | 3+ | `delete()` |
| `/user-collections/{id}/artifacts` | GET | List | 15+ | `list_by_collection()`, `count_by_collection()` |
| `/user-collections/{id}/artifacts` | POST | Create | 20+ | `add_artifacts()`, `upsert_metadata()` |
| `/user-collections/{id}/artifacts/{uuid}` | DELETE | Delete | 5+ | `remove_artifact()` |
| `/user-collections/{id}/refresh` | POST | Action | 25+ | Multiple repo methods + orchestration |
| `/user-collections/default/ensure` | POST | Action | 8+ | `ensure_default()`, `_ensure_collection_project_sentinel()` |
| (+ 6 group-related endpoints) | VARIOUS | Mixed | 20+ | Group repo TBD or collection repo |

---

## Success Criteria

### Functional
- All 16 endpoints remain operational with identical request/response contracts
- No changes to OpenAPI spec (endpoint URLs, methods, status codes, response schemas)
- Pagination, filtering, sorting work as before
- Artifact metadata (tags, deployments, source tracking) preserved
- Collection grouping operations work correctly

### Technical
- **Zero direct session usage** in ALL routers (user_collections.py + artifacts.py + artifact_history.py + deployment_profiles.py + projects.py + tags.py) (verified by grep audit)
- **All mutations transactional** via repo `try/finally` blocks
- **DTO conversion** complete — no ORM models leaked to router layer
- **DI injection clean** — all endpoints use typed repo aliases, not imports
- **Session lifecycle managed** — no leaks, proper commit/rollback semantics
- **Tests pass** — 100% of existing user_collections tests continue to pass

### Quality Gates (Phase 5 Validation)
1. `grep -rn "session\.query\|session\.add\|session\.commit\|get_session" skillmeat/api/routers/ | grep -v "#"` returns ZERO code matches across ALL router files
2. `pytest tests/api/test_user_collections.py -v` passes (all endpoint tests green)
3. `diff <(git show HEAD:skillmeat/api/openapi.json | jq '.paths."/api/v1/user-collections"') <(jq '.paths."/api/v1/user-collections"' skillmeat/api/openapi.json)` shows no diff
4. Code review confirms no manual session management remains in migrated functions

---

## Assumptions & Dependencies

### Assumptions
- `skillmeat/cache/models.py` models (Collection, CollectionArtifact, Artifact) remain stable throughout
- Existing `Collection` table schema unchanged (no new columns required)
- `CollectionArtifact` JSON fields (tags_json, tools_json, deployments_json) continue to work as-is
- Router test fixtures can be updated to inject mock repos via DI
- LocalGroupRepository pattern is the canonical model for DB-backed repos

### External Dependencies
- `sqlalchemy.orm.Session` for session management (no changes needed)
- Existing `skillmeat.cache.models` ORM classes (Collection, CollectionArtifact, Artifact, etc.)
- Existing DI infrastructure in `dependencies.py` (Depends, Annotated patterns)
- pytest + mocking for test coverage

### Blockers / Risks
- **No blockers identified** — all interfaces and concrete classes are new; no breaking changes to existing code paths until Phase 4 router migration
- **Risk**: Large scope (~110 session calls) — mitigated by phased approach and thorough testing at each phase boundary
- **Risk**: Complex joins in `list_collection_artifacts()` — mitigated by extracting and testing repo method independently before integrating into router

---

## Related Context

### Files Already Modified (Phase 5 of gap-closure)
- `skillmeat/api/routers/context_entities.py` — already migrated (TASK-5.1)
- `skillmeat/api/routers/settings.py` — already migrated (TASK-5.2)
- `skillmeat/api/routers/project_templates.py` — already migrated (TASK-5.4)
- `skillmeat/api/routers/marketplace_sources.py` — in progress (TASK-5.3)

This plan completes the gap-closure by handling **TASK-4.1** (user_collections.py migration, deferred to avoid Phase 4 bloat) plus residual session.query() calls from TASK-4.3 and TASK-6.3 that were over-claimed as complete in the parent plan.

### Architecture Pattern Reference
- **ABC pattern**: See `skillmeat/core/interfaces/repositories.py` — IArtifactRepository, IProjectRepository, etc.
- **DTO pattern**: See `skillmeat/core/interfaces/dtos.py` — ArtifactDTO, ProjectDTO, GroupDTO
- **Concrete impl pattern**: See `skillmeat/core/repositories/local_group.py` — LocalGroupRepository with session lifecycle
- **DI pattern**: See `skillmeat/api/dependencies.py` — factory providers and Annotated aliases
- **Data flow**: See `.claude/context/key-context/repository-architecture.md` § "Recipe 1: Adding an Endpoint"

---

## Rollout & Validation Timeline

1. **Phase 1** (1 day): DTOs + ABCs defined and tested
2. **Phase 2** (2-3 days): Concrete repos implemented, unit tested, session lifecycle verified
3. **Phase 3** (1 day): DI wiring complete, mocks created, all imports clean
4. **Phase 4** (2 days): CRUD endpoints migrated, 10 endpoints use repos exclusively
5. **Phase 5** (2 days): Complex endpoints + cache sync migrated, full validation pass

**Checkpoint after Phase 3**: All ABCs, DTOs, repos, and DI ready; no router changes yet. Safe to gate here if needed.

**Final validation (Phase 5)**: Zero session usage confirmed; all tests pass; enterprise-db-storage refactor can proceed.

