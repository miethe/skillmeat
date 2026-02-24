---
title: 'Implementation Plan: Deployment Sets'
schema_version: 2
doc_type: implementation_plan
status: completed
created: 2026-02-23
updated: '2026-02-24'
feature_slug: deployment-sets
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/deployment-sets-v1.md
plan_ref: null
scope: Add DeploymentSet + DeploymentSetMember DB tables, recursive resolution service
  with cycle detection, 11-endpoint REST API, and full web UI (list, detail, member
  management, batch deploy modal) for composable one-action artifact deployment.
effort_estimate: 32 pts
architecture_summary: "DB-first: new ORM tables + Alembic migration \u2192 CRUD repo\
  \ + member repo \u2192 resolution service + cycle detection + batch deploy \u2192\
  \ 11-endpoint FastAPI router \u2192 Next.js pages + React Query hooks + shadcn UI."
related_documents:
- docs/project_plans/PRDs/features/deployment-sets-v1.md
- skillmeat/cache/models.py
- skillmeat/cache/repositories.py
- skillmeat/cache/migrations/
- skillmeat/api/schemas/deployment_sets.py
- skillmeat/api/routers/deployment_sets.py
- skillmeat/api/routers/groups.py
- skillmeat/api/routers/deployments.py
- skillmeat/api/server.py
- skillmeat/core/services/manifest_sync_service.py
- skillmeat/web/app/deployment-sets/page.tsx
- skillmeat/web/app/deployment-sets/[id]/page.tsx
- skillmeat/web/components/deployment-sets/
- skillmeat/web/types/deployment-sets.ts
- skillmeat/web/hooks/index.ts
owner: null
contributors: []
priority: high
risk_level: medium
category: product-planning
tags:
- implementation
- planning
- deployment-sets
- batch-deploy
- collections
- groups
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/cache/models.py
- skillmeat/cache/migrations/
- skillmeat/cache/repositories.py
- skillmeat/api/schemas/deployment_sets.py
- skillmeat/api/routers/deployment_sets.py
- skillmeat/api/server.py
- skillmeat/api/config.py
- skillmeat/web/types/deployment-sets.ts
- skillmeat/web/hooks/deployment-sets.ts
- skillmeat/web/hooks/index.ts
- skillmeat/web/app/deployment-sets/page.tsx
- skillmeat/web/app/deployment-sets/[id]/page.tsx
- skillmeat/web/components/deployment-sets/add-member-dialog.tsx
- skillmeat/web/components/deployment-sets/member-list.tsx
- skillmeat/web/components/deployment-sets/batch-deploy-modal.tsx
- skillmeat/web/components/deployment-sets/deploy-result-table.tsx
- .claude/progress/deployment-sets-v1/all-phases-progress.md
---

# Implementation Plan: Deployment Sets

**Plan ID**: `IMPL-2026-02-23-DEPLOYMENT-SETS`
**Date**: 2026-02-23
**Author**: Claude (Sonnet 4.6) — Implementation Planner
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/deployment-sets-v1.md`
- **Groups API reference**: `skillmeat/api/routers/groups.py`
- **Deploy API reference**: `skillmeat/api/routers/deployments.py`
- **ORM models reference**: `skillmeat/cache/models.py`

**Complexity**: Large
**Total Estimated Effort**: 32 points
**Target Timeline**: 7–9 days

---

## Executive Summary

Deployment Sets introduces composable, user-scoped artifact bundles that resolve recursively and batch-deploy to a target project in a single action. Implementation proceeds DB-first (models + migration), adds repository and service layers (with DFS resolution and cycle detection), exposes 11 REST endpoints, then builds the Next.js management UI and batch deploy flow. Phases 1–3 are strictly sequential; frontend types and hooks can begin in parallel with Phase 3 once schemas are drafted. Testing is incremental throughout; documentation runs in parallel with Phase 5–6.

---

## Implementation Strategy

### Architecture Sequence

Following SkillMeat's layered architecture (router → service → repository → DB):

1. **Database Layer** — `DeploymentSet` + `DeploymentSetMember` ORM tables, Alembic migration, indexes
2. **Repository Layer** — CRUD repo, member management repo, position reordering
3. **Service Layer** — Resolution service (DFS, depth limit, dedup), cycle detection, batch deploy orchestration
4. **API Layer** — 11 FastAPI endpoints, Pydantic DTOs, router registration
5. **Frontend Core** — TS types, React Query hooks, list page, detail/edit page, member management dialog
6. **Frontend Deploy** — Batch deploy modal, result display, deploy button integration
7. **Testing + Documentation** — Integration tests, perf test, accessibility pass, OpenAPI export, hook docs

### Parallel Work Opportunities

| Parallelizable Pair | Earliest Start | Notes |
|---------------------|---------------|-------|
| Phase 3 (API schemas draft) + Frontend types | Phase 3 start | Types can be drafted from PRD schema before API is complete |
| Unit tests alongside Phase 2 service code | Phase 2 start | Test resolution logic as it is written |
| Documentation + Phase 5 (Frontend Deploy) | Phase 5 start | OpenAPI auto-generates from FastAPI; hook docs after hooks exist |
| Phase 6 testing + Phase 5 completion | Phase 5 ongoing | Backend integration tests can run while frontend is finishing |

### Critical Path

```
Phase 1 (DB) → Phase 2 (Repo) → Phase 3 (Service+API) → Phase 4 (Frontend Core) → Phase 5 (Frontend Deploy) → Phase 6 (Testing+Docs)
```

The resolution service (DS-004 + DS-005) is the highest-risk item and gates all downstream work. Prioritize it early in Phase 2/3.

---

## Phase Breakdown

### Phase 1: Database + Repository Layer

**Duration**: 1–2 days
**Dependencies**: None
**Assigned Subagents**: `data-layer-expert`, `python-backend-engineer`

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DS-001 | ORM models + migration | Add `DeploymentSet` and `DeploymentSetMember` to `skillmeat/cache/models.py` using string UUID IDs (matching `Group.id` conventions). Write Alembic migration with upgrade + downgrade. Add DB-level CHECK constraint for exactly-one member reference and indexes on `set_id`, `member_set_id`, and `(set_id, position)`. | `alembic upgrade head` completes without error. `alembic downgrade -1` reverts cleanly. Tables, CHECK constraint, and indexes are visible in DB schema. | 2 pts | `data-layer-expert` | None |
| DS-002 | DeploymentSet CRUD repo | Implement `DeploymentSetRepository` in `skillmeat/cache/repositories.py` with `create`, `get`, `list` (paginated, filterable by name/tag), `update`, `delete`. Delete operation must remove parent references where deleted set appears as `member_set_id` (FR-10) before deleting row. Add `owner_id` persistence: all reads/writes filter by `owner_id`. Owner resolution: `owner_id = token if auth_enabled else "local-user"` (no new auth middleware needed for V1 — `TokenDep` returns a string token that serves as identity). Return ORM objects; DTO mapping is service responsibility. | Unit tests cover CRUD, owner-scoped reads/writes (two different owner_ids cannot see each other's sets), and FR-10 delete behavior (parent references removed). `list` accepts `name`, `tag`, `limit`, `offset`. | 2 pts | `python-backend-engineer` | DS-001 |
| DS-003 | Member management repo | Add member operations to `DeploymentSetRepository`: `add_member(set_id, artifact_uuid|group_id|member_set_id, position)`, `remove_member(member_id)`, `update_member_position(member_id, position)`, `get_members(set_id)`. Validate polymorphic constraint at repo layer for clear errors while relying on DB CHECK as final guard. | Unit tests: add each member type, remove, reorder. Constraint violation raises domain/repo error and DB rejects invalid rows. | 1 pt | `python-backend-engineer` | DS-002 |

**Phase 1 Quality Gates:**

- [ ] `alembic upgrade head` / `alembic downgrade -1` both succeed on a clean DB
- [ ] CHECK constraint (exactly one member ref) + indexes (`set_id`, `member_set_id`, `set_id+position`) confirmed in migration
- [ ] Unit tests for repo CRUD pass (SQLite in-memory fixture)
- [ ] FR-10 delete behavior validated: deleting a set removes inbound parent references

---

### Phase 2: Service Layer

**Duration**: 1–2 days
**Dependencies**: Phase 1 complete
**Assigned Subagents**: `python-backend-engineer`, `backend-architect`

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DS-004 | Resolution service | Implement `DeploymentSetService.resolve(set_id) -> list[str]` using DFS traversal. Expand: artifact members → emit `artifact_uuid`; group members → read `GroupArtifact` rows for `artifact_uuid` list; set members → recurse. Deduplicate by `artifact_uuid` (preserve first-seen order). Enforce depth limit of 20; raise `DeploymentSetResolutionError` with traversal path on breach. | Unit tests: 3-level nesting resolves all unique UUIDs; duplicate artifacts appear once; depth-21 set raises error with path; empty set returns `[]`. Resolution is stateless (accepts in-memory member maps for testing without DB). | 3 pts | `backend-architect`, `python-backend-engineer` | DS-003 |
| DS-005 | Circular-reference detection | Implement `DeploymentSetService._check_cycle(set_id, candidate_member_set_id)` using descendant reachability from `candidate_member_set_id`. Called on every `add_member` where `member_set_id` is non-null. Reject insert when `set_id` is reachable from candidate (transitively). Raise `DeploymentSetCycleError` with traversal path. | Unit tests: A→B then B→A raises; A→B→C then C→A raises; valid DAG accepted; self-reference rejected. | 2 pts | `python-backend-engineer` | DS-004 |
| DS-006 | Batch deploy service | Implement `DeploymentSetService.batch_deploy(set_id, project_id, profile_id) -> list[DeployResultDTO]`. `DeploymentSetService.__init__` accepts a `DeploymentManager` (injected from router dependency chain via `CollectionManagerDep`). Call `resolve(set_id)` to get UUID list, then for each `artifact_uuid`: query `CollectionArtifact` table by `uuid` column to get `name` and `type`; construct `artifact_id` as `f"{type}:{name}"`. Resolve `project_id` to `project_path` via `Project` model lookup (`Project.id` → `Project.path`). Invoke `DeploymentManager.deploy_artifacts()` directly (NOT the HTTP deploy endpoint — call the core service layer at `skillmeat/core/deployment.py`; note: the HTTP deploy endpoint lives at `/api/v1/deploy`, not `/deployments`). Catch per-artifact exceptions; never abort loop. Return `list[{artifact_uuid, status: "success"|"skip"|"error", error: str|None}]`. Emit structured logs with `set_id`, `project_id`, `profile_id`, `resolved_count` for success/failure and warning-level logs with full traversal path for missing-member resolution errors. | Unit tests with mocked `DeploymentManager`: mixed-result partial failure, all-success, `CollectionArtifact` mapping failure path (unknown uuid → error result), missing member warning path with `caplog` assertion on traversal path, and deploy exception → `"error"` with message. | 2 pts | `python-backend-engineer` | DS-005 |

**Phase 2 Quality Gates:**

- [ ] Resolution unit tests achieve >90% branch coverage on resolution logic (`pytest --cov`)
- [ ] Cycle detection tests cover: direct cycle, transitive cycle, valid DAG, self-reference
- [ ] Batch deploy adapter validated (`artifact_uuid` → `CollectionArtifact` lookup → deploy request inputs; `project_id` → `Project.path` → `project_path`)
- [ ] Batch deploy calls `DeploymentManager.deploy_artifacts()` directly (not HTTP endpoint)
- [ ] Batch deploy returns per-artifact results regardless of individual failures
- [ ] Warning-level logs with traversal path emitted for missing-member resolution errors
- [ ] `DeploymentSetResolutionError` and `DeploymentSetCycleError` defined in domain exceptions module

---

### Phase 3: API Layer

**Duration**: 1 day
**Dependencies**: Phase 2 complete (schemas can be drafted in parallel from Phase 3 start)
**Assigned Subagents**: `python-backend-engineer`

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DS-007 | Pydantic schemas | Create `skillmeat/api/schemas/deployment_sets.py` with: `DeploymentSetCreate`, `DeploymentSetUpdate`, `DeploymentSetResponse`, `DeploymentSetListResponse`, `MemberCreate`, `MemberUpdatePosition`, `MemberResponse`, `ResolveResponse`, `BatchDeployRequest`, `BatchDeployResponse`, `DeployResultItem`. All response schemas are DTOs — no ORM model exposure. | `pydantic` validation passes for valid payloads. Invalid payloads (missing name, all-null member refs) raise `ValidationError`. | 1 pt | `python-backend-engineer` | DS-006 |
| DS-008 | REST endpoints + router registration + feature flag | Create `skillmeat/api/routers/deployment_sets.py` with all 11 endpoints per PRD §13 API surface. Register router in `skillmeat/api/server.py` with API prefix wiring (follow existing `app.include_router()` pattern at line ~398). Add `deployment_sets_enabled: bool = Field(default=True, ...)` to `APISettings` in `skillmeat/api/config.py` (following `composite_artifacts_enabled` pattern). Map `DeploymentSetCycleError` → HTTP 422; `DeploymentSetResolutionError` → HTTP 422; `not found` → HTTP 404. Enforce owner scoping: `owner_id = token if settings.auth_enabled else "local-user"` (derive from `TokenDep` + `SettingsDep`). Inject `DeploymentManager` via `CollectionManagerDep` for the deploy endpoint. Clone endpoint (`POST /{id}/clone`) duplicates set + all direct member rows, appends " (copy)" to name. | `pytest` integration tests (FastAPI `TestClient`) pass for all 11 endpoints (happy + error paths). HTTP 422 returned for circular-ref attempt. Owner-scope isolation verified in auth-enabled test mode. `deployment_sets_enabled` field present in config. | 3 pts | `python-backend-engineer` | DS-007 |

**Phase 3 Quality Gates:**

- [ ] All 11 endpoints registered and returning correct HTTP status codes
- [ ] Integration tests cover happy path + error cases for every endpoint
- [ ] HTTP 422 for circular-ref add-member confirmed by test
- [ ] No ORM model objects returned in any response (DTOs only)
- [ ] `deployment_sets_enabled` field added to `APISettings` in `config.py`
- [ ] Router registered in `server.py`; FastAPI dev server starts without error

---

### Phase 4: Frontend Core

**Duration**: 2 days
**Dependencies**: Phase 3 complete (types can start in parallel once DS-007 schemas are drafted)
**Assigned Subagents**: `ui-engineer-enhanced`, `frontend-developer`

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DS-009 | TypeScript types + React Query hooks | Create `skillmeat/web/types/deployment-sets.ts` with types mirroring all Pydantic response DTOs. Create `skillmeat/web/hooks/deployment-sets.ts` with hooks: `useDeploymentSets(params)`, `useDeploymentSet(id)`, `useCreateDeploymentSet`, `useUpdateDeploymentSet`, `useDeleteDeploymentSet`, `useCloneDeploymentSet`, `useAddMember`, `useRemoveMember`, `useUpdateMemberPosition`, `useResolveSet(id)`. Export all from `skillmeat/web/hooks/index.ts`. Stale times: list/detail 5 min; resolve 30 sec. | `pnpm type-check` passes. Hook signatures match Pydantic schemas. Mutations invalidate `['deployment-sets']` query key family. | 2 pts | `frontend-developer` | DS-008 |
| DS-010 | Deployment Sets list page | Create `skillmeat/web/app/deployment-sets/page.tsx` (server component shell, client data via hooks). Card grid layout using shadcn `Card`. Each card shows: name, description (truncated), color/icon indicator, resolved member count, action menu (edit, clone, delete). Search input filters by name client-side or via query param. Empty state with "Create your first Deployment Set" CTA. Create dialog with `DeploymentSetCreate` form. Wire UI visibility to `deployment_sets_enabled` feature flag (nav + route affordances). | Page renders list of sets. Empty state shown when no sets. Create dialog opens/submits successfully. Clicking card navigates to `/deployment-sets/[id]`. Feature flag OFF hides nav entry and blocks page affordances gracefully. | 2 pts | `ui-engineer-enhanced` | DS-009 |
| DS-011 | Set detail/edit page + member list | Create `skillmeat/web/app/deployment-sets/[id]/page.tsx`. Layout: metadata section (name, description, color, icon, tags — inline edit via PATCH); member list section with `MemberList` component. `MemberList` shows each member with type badge (`Artifact` / `Group` / `Set`), name/UUID display, position, remove button. "Add Member" button opens `AddMemberDialog`. "Resolved: N artifacts" count from `useResolveSet`. "Deploy Set" button (primary CTA) opens batch deploy modal. | Page renders set metadata and member list. Type badges display correctly. Remove member removes row and refetches. Inline name edit PATCHes and reflects updated name. Resolved count displays. | 3 pts | `ui-engineer-enhanced` | DS-010 |
| DS-012 | Add-member dialog | Create `skillmeat/web/components/deployment-sets/add-member-dialog.tsx`. Three-tab picker: Artifact (search by name/UUID from collection), Group (list existing groups), Set (list other sets — exclude current set). Selecting an item calls `useAddMember` mutation. Show error toast on 422 (circular ref) with message "This would create a circular reference." Close and refetch member list on success. Keyboard navigable (WCAG 2.1 AA). | Dialog opens, tabs switch. Selecting artifact/group/set calls API. Circular-ref 422 shows toast. Success closes dialog and refreshes list. Tab/arrow navigation works without mouse. | 2 pts | `ui-engineer-enhanced` | DS-011 |

**Phase 4 Quality Gates:**

- [ ] `pnpm type-check` passes with no new errors
- [ ] List page renders, paginates, and filters sets
- [ ] Detail page renders members with correct type badges
- [ ] Add-member dialog: all 3 member types addable; circular-ref error surfaced as toast
- [ ] Keyboard navigation through member list and dialog verified manually

---

### Phase 5: Frontend Deploy Integration

**Duration**: 1 day
**Dependencies**: Phase 4 complete
**Assigned Subagents**: `ui-engineer-enhanced`, `frontend-developer`

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DS-013 | useBatchDeploySet hook | Add `useBatchDeploySet` mutation hook to `skillmeat/web/hooks/deployment-sets.ts`. Accepts `{set_id, project_id, profile_id}`. POSTs to `/deployment-sets/{id}/deploy`. Returns `BatchDeployResponse`. Does not invalidate deployment-sets cache (deploy does not modify set data). May invalidate project deployments cache. | Hook compiles. `pnpm type-check` passes. Hook callable from modal with correct params. | 1 pt | `frontend-developer` | DS-009 |
| DS-014 | Batch deploy modal + result table | Create `skillmeat/web/components/deployment-sets/batch-deploy-modal.tsx`. Step 1: project selector (dropdown of user's projects) + profile selector (filtered by selected project). Step 2 (after submit): `DeployResultTable` showing per-artifact rows with status badge (Success / Skipped / Error) and error message column. "Deploy" button triggers `useBatchDeploySet`; loading spinner during in-flight. Summary line: "X succeeded, Y skipped, Z failed." | Modal opens from detail page "Deploy Set" button. Project + profile selectors populated. Submit calls API. Result table renders all artifact rows with correct badges. Summary line correct. Closed via Escape or close button. | 2 pts | `ui-engineer-enhanced` | DS-013 |

**Phase 5 Quality Gates:**

- [ ] `pnpm type-check` passes
- [ ] Batch deploy modal: project and profile selectors work end-to-end against running API
- [ ] Result table renders success / skip / error states (verified with test set)
- [ ] "Deploy Set" button visible on both list card and detail page
- [ ] Loading state shown during in-flight request

---

### Phase 6: Testing + Documentation

**Duration**: 1 day (can overlap with Phase 5 completion)
**Dependencies**: Phase 4 complete for backend tests; Phase 5 complete for frontend tests
**Assigned Subagents**: `python-backend-engineer`, `frontend-developer`, `documentation-writer`, `api-documenter`

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DS-T01 | Integration tests: circular-ref + batch deploy + delete semantics + observability | Extend API integration tests (FastAPI `TestClient`): (1) create set A → B then attempt B → A, assert 422; (2) batch deploy 3-level nested set to mock project, assert all UUIDs appear exactly once and adapter mapping (`CollectionArtifact` lookup) is invoked; (3) delete member-set referenced by parent and assert inbound parent references are removed (FR-10); (4) clone test: modify clone, assert source unchanged; (5) observability: batch deploy with a missing-member UUID — assert warning-level log entry includes `set_id` and traversal path (use `caplog` fixture). | All scenarios pass repeatedly without flakiness. Warning log assertions use `caplog` to verify traversal path content. | 1 pt | `python-backend-engineer` | DS-008 |
| DS-T02 | Performance test: large set resolution | Write pytest benchmark: create set with 5 levels of nesting, 100 total members across levels. Time `resolve()` call. Assert <500 ms. | Benchmark passes on CI hardware. Result logged to test output. | 1 pt | `python-backend-engineer` | DS-004 |
| DS-T03 | Frontend type-check + component tests | Run `pnpm type-check` — zero new errors. Write Jest/RTL component tests for: `AddMemberDialog` (renders 3 tabs, shows error toast on 422 mock), `BatchDeployModal` (renders result table from mock response). | `pnpm type-check` clean. Component tests pass. | 1 pt | `frontend-developer` | DS-014 |
| DS-T04 | Documentation + hook exports + feature flag validation | Confirm `skillmeat/web/hooks/index.ts` exports all new hooks. Verify OpenAPI spec auto-generates correctly from FastAPI router (run `skillmeat web dev --api-only` and check `/docs`). Validate `deployment_sets_enabled` flag (added in DS-008) gates frontend nav/page visibility: flag ON → nav item + pages visible; flag OFF → nav item hidden and pages return graceful empty state. | All hooks exported. OpenAPI `/docs` shows all 11 endpoints. Feature flag toggles nav/page visibility deterministically in both ON and OFF states. | 1 pt | `documentation-writer`, `api-documenter` | DS-013 |

**Phase 6 Quality Gates:**

- [ ] Circular-ref integration test: HTTP 422 on A→B→A cycle
- [ ] Batch deploy integration test: 3-level nested set, all UUIDs in result, no duplicates
- [ ] FR-10 integration test: deleting a set removes inbound parent references
- [ ] Performance test: resolution of 100-member 5-level set <500 ms
- [ ] `pnpm type-check` clean (zero new errors)
- [ ] Component tests for `AddMemberDialog` and `BatchDeployModal` pass
- [ ] OpenAPI `/docs` shows all 11 `/deployment-sets` endpoints
- [ ] All new React Query hooks exported from `hooks/index.ts`

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circular reference causes infinite recursion in resolution | High | Medium | Descendant reachability cycle check at write time (DS-005) + hard depth limit of 20 in resolver (DS-004); both layers independently safe |
| Batch deploy partial failure leaves project inconsistent | Medium | Medium | Non-atomic by design; per-artifact try/except; result list always returned; UI shows per-row status for user to retry |
| UUID-based resolver output cannot call current deploy contract directly | High | Medium | Adapter in DS-006: query `CollectionArtifact` by `uuid` → get `name`/`type` → construct `artifact_id`; resolve `project_id` via `Project` model → `project_path`; call `DeploymentManager.deploy_artifacts()` directly (not HTTP layer). Test mapping failures for unknown UUIDs |
| ORM → DTO schema divergence (known risk from Platform Profiles) | Medium | Low | Create Pydantic schemas in DS-007 immediately after ORM models in DS-001; add round-trip integration test in DS-T01 |
| Missing feature-flag gating causes premature UI exposure | Medium | Medium | Add config + nav/page gating in DS-010/DS-T04 with explicit ON/OFF tests |
| Write-through drift between DB and manifest-backed workflows | Medium | Low | Keep Deployment Sets DB-authoritative in V1; add observability and document optional future manifest sync path |
| Resolution of large sets (100+ members) too slow | Low | Low | Indexes on `set_id`, `member_set_id`, and `set_id+position`; benchmark in DS-T02 catches regressions early |

---

## User Story to Task Mapping

| Story ID | Story Name | Tasks | Total Pts |
|----------|-----------|-------|-----------|
| DS-001 (story) | DB models + migration | DS-001 | 2 pt |
| DS-002 (story) | Repository CRUD | DS-002 | 2 pt |
| DS-003 (story) | Member management | DS-003 | 1 pt |
| DS-004 (story) | Resolution service | DS-004 | 3 pt |
| DS-005 (story) | Circular-ref detection | DS-005 | 2 pt |
| DS-006 (story) | Batch deploy service | DS-006 | 2 pt |
| DS-007 (story) | REST API (CRUD) | DS-007, DS-008 | 4 pt |
| DS-008 (story) | Clone endpoint | DS-008 (included) | — |
| DS-009 (story) | Frontend types + hooks | DS-009, DS-013 | 3 pt |
| DS-010 (story) | Set list page | DS-010 | 2 pt |
| DS-011 (story) | Set detail/edit page | DS-011 | 3 pt |
| DS-012 (story) | Add-member dialog | DS-012 | 2 pt |
| DS-013 (story) | Batch deploy UI | DS-014 | 2 pt |
| DS-014 (story) | Testing + polish | DS-T01, DS-T02, DS-T03, DS-T04 | 4 pt |
| **Total** | | | **32 pt** |

> Note: Estimate aligned to the revised PRD and progress tracking baseline (32 pt total).

---

## Parallelization Strategy

```
Day 1-2   [Phase 1]  DS-001 ──→ DS-002 ──→ DS-003
Day 2-4   [Phase 2]                 DS-004 ──→ DS-005 ──→ DS-006
Day 4-5   [Phase 3]                                 DS-007 ──→ DS-008
                     (parallel: DS-007 schemas available → DS-009 types can start)
Day 5-6   [Phase 4]  DS-009 ──→ DS-010 ──→ DS-011 ──→ DS-012
Day 6-7   [Phase 5]                                         DS-013 ──→ DS-014
Day 7     [Phase 6]  DS-T01, DS-T02 (parallel) + DS-T03 (parallel) + DS-T04 (parallel)
```

Phase 6 tasks are all independent and can run in parallel as a batch delegation.

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to deploy 15 artifacts | <30 sec | Manual timing with test set |
| Circular-ref accepted at API | 0 | Integration test DS-T01 |
| Batch deploy latency (50 artifacts) | <5 sec | Manual test with mocked deploy |
| Resolution perf (100-member, 5-level) | <500 ms | pytest benchmark DS-T02 |
| Resolution unit test branch coverage | >90% | `pytest --cov` on resolution module |
| Frontend type errors | 0 new | `pnpm type-check` DS-T03 |

---

**Progress Tracking:**

See `.claude/progress/deployment-sets-v1/all-phases-progress.md`

---

**Implementation Plan Version**: 1.2
**Last Updated**: 2026-02-24
