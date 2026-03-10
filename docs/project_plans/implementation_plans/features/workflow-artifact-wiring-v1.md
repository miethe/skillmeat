---
title: 'Implementation Plan: Workflow-Artifact Collection Wiring'
schema_version: 2
doc_type: implementation_plan
status: in-progress
created: '2026-03-10'
updated: '2026-03-10'
feature_slug: workflow-artifact-wiring
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/workflow-artifact-wiring-v1.md
plan_ref: null
scope: Backend sync service + deployment set integration + frontend UI wiring to make
  workflows discoverable and deployable alongside artifacts
effort_estimate: 26 story points
architecture_summary: Write-through sync from workflows table to artifacts table;
  extend DeploymentSetMember with workflow_id; wire collection UI to artifact endpoints
related_documents:
- docs/project_plans/PRDs/features/workflow-artifact-wiring-v1.md
- docs/project_plans/implementation_plans/features/workflow-orchestration-v1.md
- docs/project_plans/PRDs/features/deployment-sets-v1.md
- docs/project_plans/architecture/ADRs/adr-008-artifact-tiering-composition-hierarchy.md
owner: null
contributors: []
priority: high
risk_level: medium
category: product-planning
tags:
- implementation
- workflow
- artifact
- collection
- wiring
- tiering
- deployment
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/cache/models.py
- skillmeat/cache/workflow_repository.py
- skillmeat/cache/migrations/versions/*.py
- skillmeat/core/workflow/service.py
- skillmeat/core/services/workflow_artifact_sync_service.py
- skillmeat/api/routers/workflows.py
- skillmeat/api/routers/deployment_sets.py
- skillmeat/api/routers/artifacts.py
- skillmeat/web/types/artifact.ts
- skillmeat/web/app/collection/page.tsx
- skillmeat/web/app/manage/page.tsx
---

# Implementation Plan: Workflow-Artifact Collection Wiring

**Plan ID**: `IMPL-2026-03-10-WORKFLOW-ARTIFACT-WIRING`
**Date**: 2026-03-10
**Author**: Claude (Opus 4.6) — Implementation Planner
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/workflow-artifact-wiring-v1.md`
- **Workflow Orchestration**: `docs/project_plans/implementation_plans/features/workflow-orchestration-v1.md`
- **Deployment Sets**: `docs/project_plans/PRDs/features/deployment-sets-v1.md`
- **ADR-008**: `docs/project_plans/architecture/ADRs/adr-008-artifact-tiering-composition-hierarchy.md`

**Complexity**: Large
**Total Estimated Effort**: 26 story points
**Target Timeline**: 3 weeks (2 weeks implementation + 1 week testing/review)

## Executive Summary

This plan wires the isolated Workflow Orchestration Engine into the unified Artifact Collection system so workflows become discoverable, deployable, and searchable alongside skills, agents, and composites. The approach uses a write-through sync service that maintains a derived `artifacts` record whenever a workflow is created, updated, or deleted, without blocking primary workflow writes on sync failure. Deployment sets gain a `workflow_id` column (nullable, polymorphic with existing member variants), and the collection UI surfaces real workflow artifacts instead of an empty placeholder tab.

**Key Phases**:
1. **Data Layer** — Alembic migration + sync repository methods (2 pts)
2. **Service Layer** — `WorkflowArtifactSyncService` + hooks (3 pts)
3. **API Layer** — Deployment set extension + collection endpoint wiring (2 pts)
4. **Frontend** — Collection/Manage page data binding (3 pts)
5. **Testing & Validation** — Unit, integration, E2E coverage (16 pts)

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Database Layer** — Additive migration: `deployment_set_members.workflow_id` (UUID, FK to workflows.id)
2. **Repository Layer** — Sync methods on `WorkflowArtifactRepository`: upsert, delete, query by workflow_id
3. **Service Layer** — `WorkflowArtifactSyncService` with failure isolation, OTel span, structured logging
4. **Service Integration** — Hooks in `WorkflowService.create()`, `update()`, `delete()` (post-primary-write)
5. **API Layer** — Deployment set member schema extension; collection artifact query updates
6. **Frontend** — Reuse existing artifact card/row components; data binding via API
7. **Testing** — Unit (sync service), integration (round-trip), E2E (UI flow)

### Parallel Work Opportunities

- **Phase 1** (Data) and **Phase 2** (Service) can overlap — schema migration can run independently of service implementation
- **Phase 4** (Frontend) design can start before Phase 3 (API) completes — UI components reuse existing patterns
- **Phase 5** (Testing) unit tests can run as soon as individual modules are ready (no blocking dependencies)

### Critical Path

1. Phase 1 (Migration) → Phase 2 (Service hooks) → Phase 3 (API)
2. Phase 3 (API) gates Phase 4 (Frontend data binding)
3. Phase 4 complete gates Phase 5 E2E tests
4. **Critical sequence**: Data → Service → API → Frontend
5. **Parallel**: Testing can begin on individual units after Phase 2

---

## Phase Breakdown

### Phase 1: Data Layer — Schema Migration & Sync Repository

**Duration**: 1-2 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|--------------|
| WAW-P1.1 | Alembic migration | Create additive migration: add `workflow_id` (UUID, nullable) to `deployment_set_members` with FK to `workflows.id` | Migration applies cleanly; FK constraint enforced in all DB dialects (SQLite, PostgreSQL) | 2 pts | None |
| WAW-P1.2 | Artifact model validation | Verify `Artifact` model in `cache/models.py` supports `type='workflow'` rows without additional columns | No schema changes needed to `artifacts` table; workflow records can store metadata in JSON `metadata` column | 1 pt | WAW-P1.1 |
| WAW-P1.3 | Sync repository methods | Implement in `WorkflowArtifactRepository`: `upsert_artifact_from_workflow()`, `delete_artifact_for_workflow()`, `get_by_workflow_id()` | Methods use SQLAlchemy 2.x `select()` style; upsert is idempotent (ON CONFLICT DO UPDATE); supports concurrent calls | 2 pts | WAW-P1.1 |
| WAW-P1.4 | Mutual exclusivity validation | Add validation to ensure `DeploymentSetMember` has exactly one of: `artifact_uuid`, `group_id`, `member_set_id`, `workflow_id` (not null) | Service-layer validation enforced on create/update; optional DB CHECK constraint for extra safety | 1 pt | WAW-P1.3 |

**Phase 1 Quality Gates**:
- [ ] Migration applies without errors
- [ ] FK constraint exists and prevents invalid workflow_id references
- [ ] Artifact model supports workflow records in `artifacts` table
- [ ] Repository methods handle concurrent upserts without duplicate rows
- [ ] Mutual exclusivity enforced (tests verify exactly one member type per row)

---

### Phase 2: Service Layer — Sync Service & Hooks

**Duration**: 1-2 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|--------------|
| WAW-P2.1 | Sync service implementation | Implement `WorkflowArtifactSyncService` with `sync_from_workflow(workflow_id, operation: "create"|"update"|"delete")` — idempotent upsert, OTel span, structured log | Service is failure-isolated (exception doesn't propagate); primary workflow write succeeds even on sync failure; logs are at INFO level with operation metadata | 3 pts | WAW-P1.3 |
| WAW-P2.2 | Service hooks | Add sync hook calls in `WorkflowService.create()`, `update()`, `delete()` immediately after primary write (post-commit in transaction) | Sync called with correct operation; hooks do not affect primary workflow write on failure; hooks honor `workflow_artifact_sync_enabled` feature flag | 2 pts | WAW-P2.1 |
| WAW-P2.3 | Role validation service | Implement `ArtifactReferenceValidator` with `resolve_stage_roles(workflow_id)` — parses role strings from workflow definition and attempts to match against `artifacts` table | Non-blocking: returns resolved + unresolved lists; missing artifacts log warning but don't raise exception | 2 pts | WAW-P1.3 |
| WAW-P2.4 | Feature flag integration | Add `workflow_artifact_sync_enabled` flag in `APISettings` / `ConfigManager`, default `true`; guard sync service calls | Flag can be toggled without redeployment (config reload); disabling flag prevents all sync calls | 1 pt | WAW-P2.1 |
| WAW-P2.5 | Full re-sync path | Implement sync callable from `POST /api/v1/cache/refresh` — iterate all workflows, call sync service with "create" operation | Idempotent: re-running sync does not create duplicate artifacts rows; all existing workflows synced after call | 1 pt | WAW-P2.1 |

**Phase 2 Quality Gates**:
- [ ] Sync service unit tests pass (create/update/delete/concurrent calls)
- [ ] Sync failure (DB error) does not rollback primary workflow write
- [ ] OTel span emitted with correct attributes (workflow.id, operation, duration)
- [ ] Structured log written on every sync event (JSON format with operation, workflow_id, artifact_id, duration_ms)
- [ ] Feature flag works: toggling it stops/starts sync calls
- [ ] Full re-sync is idempotent: running twice produces same state

---

### Phase 3: API Layer — Deployment Sets & Collection Endpoints

**Duration**: 1 day
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer, openapi-expert

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|--------------|
| WAW-P3.1 | Deployment set schema | Update `DeploymentSetMemberRequest` and response DTO to include optional `workflow_id` field | POST with `workflow_id` persists to DB; GET returns `workflow_id` in response; field is mutually exclusive with other member types | 2 pts | WAW-P1.3 |
| WAW-P3.2 | Deployment set API handler | Update create/update/delete handlers in `/api/v1/deployment-sets` to accept and persist `workflow_id` rows | POST with `workflow_id` returns 2xx; validates workflow exists (FK); GET member list returns workflow members with `workflow_id` field | 2 pts | WAW-P3.1 |
| WAW-P3.3 | Collection listing endpoint | Verify `GET /api/v1/artifacts?type=workflow` returns all synced workflow artifact DTOs with `workflow_id` reference field | Query returns count == workflows table count (under normal conditions); DTO includes `workflow_id`, `name`, `description`, `type='workflow'`, last-updated timestamp | 1 pt | WAW-P2.1 |
| WAW-P3.4 | Workflow detail endpoint | Add optional `?resolve_roles=true` query param to `GET /api/v1/workflows/{id}` returning `resolved_roles` field with artifact references | Query param is opt-in (not computed by default); response includes array of resolved + unresolved role references | 1 pt | WAW-P2.3 |
| WAW-P3.5 | OpenAPI documentation | Update `openapi.json` to reflect workflow_id field in DeploymentSetMember and resolved_roles in workflow response | Schema correctly reflects new fields; Swagger UI shows new endpoint parameters and response structures | 1 pt | WAW-P3.4 |

**Phase 3 Quality Gates**:
- [ ] POST `/api/v1/deployment-sets/{id}/members` with `workflow_id` succeeds and persists
- [ ] GET `/api/v1/deployment-sets/{id}` returns workflow members with `workflow_id` field
- [ ] GET `/api/v1/artifacts?type=workflow` returns all synced workflows
- [ ] FK constraint prevents adding invalid workflow IDs to deployment sets
- [ ] `openapi.json` updated with new fields
- [ ] N+1 query test passes on collection listing (no join explosion)

---

### Phase 4: Frontend Wiring — Collection & Manage Pages

**Duration**: 1 day
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|--------------|
| WAW-P4.1 | Collection tab wiring | Wire collection Workflows tab to `GET /api/v1/artifacts?type=workflow` query using React Query | Tab fetches artifact list on mount; tab is empty state when query returns empty; tab shows loading spinner during fetch | 2 pts | WAW-P3.3 |
| WAW-P4.2 | Artifact card rendering | Render workflow artifact cards using existing artifact card component; display name, description, type badge, last-updated date | Cards render for each artifact; cards are keyboard-navigable and accessible | 2 pts | WAW-P4.1 |
| WAW-P4.3 | Card link-through | Add click handler to workflow cards; navigate to `/workflows/{workflow_id}` on click; handle 404 gracefully | Click on card navigates to detail page; if workflow record is gone (soft-delete), show "archived" badge or 404 message | 1 pt | WAW-P4.2 |
| WAW-P4.4 | Manage page rows | Update Manage page to list workflow artifacts with name, type badge ('workflow'), description, last-updated; include standard row operations (delete, duplicate, details link) | Workflow rows appear alongside other artifact type rows; row styling/layout consistent with existing rows | 2 pts | WAW-P4.3 |
| WAW-P4.5 | TypeScript types | Update `skillmeat/web/types/artifact.ts` to include `workflow_id` field on artifact DTO type | Type matches API response structure; TypeScript compilation passes with no errors | 1 pt | WAW-P4.1 |

**Phase 4 Quality Gates**:
- [ ] Collection Workflows tab renders real cards (not placeholder) when workflows exist
- [ ] Each card navigates to `/workflows/{id}`
- [ ] Manage page lists workflow artifacts in table
- [ ] Workflow rows include all required columns and operations
- [ ] All TypeScript types compile without errors
- [ ] Tab is empty state when no workflows exist

---

### Phase 5: Testing & Validation

**Duration**: 2-3 days
**Dependencies**: Phases 1-4 complete
**Assigned Subagent(s)**: python-backend-engineer, ui-engineer-enhanced, senior-code-reviewer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|-------------------|----------|--------------|
| WAW-P5.1 | Unit tests: sync service | Test `WorkflowArtifactSyncService` in isolation: create, update, delete, idempotent upsert, failure isolation, OTel span | >80% code coverage; all test cases pass; concurrent upsert produces single row; sync failure doesn't propagate | 3 pts | WAW-P2.1 |
| WAW-P5.2 | Unit tests: role validator | Test `ArtifactReferenceValidator` resolve method: matching artifacts, unresolved artifacts, warning logs | >80% coverage; returns correct resolved/unresolved lists; warnings logged but no exceptions raised | 2 pts | WAW-P2.3 |
| WAW-P5.3 | Integration tests: end-to-end round-trip | Create workflow → verify artifact record created → add to deployment set → delete workflow → verify artifact removed | All steps complete without error; artifact record matches workflow data; deployment set member references correctly deleted when workflow deleted | 3 pts | WAW-P3.2, WAW-P4.1 |
| WAW-P5.4 | Integration tests: collection API | Test `GET /api/v1/artifacts?type=workflow` query: count matches workflows table; DTO structure correct; filter by type works; no N+1 queries | Query assertion passes; no N+1 queries detected in query log (query count ≤ 2 for 100 workflows) | 2 pts | WAW-P3.3 |
| WAW-P5.5 | Integration tests: deployment set members | Test POST, GET, DELETE workflows members in deployment set; verify FK constraint prevents invalid workflow IDs | CRUD operations succeed; FK constraint prevents orphaned references; GET returns correct member type | 2 pts | WAW-P3.2 |
| WAW-P5.6 | E2E tests: UI flow | Test collection Workflows tab renders, cards show correct data, click navigates to detail page; Manage page shows workflow rows | E2E test passes; tab renders real data; cards are clickable and navigable; Manage page includes workflow rows | 3 pts | WAW-P4.4 |
| WAW-P5.7 | E2E tests: CLI integration | Test `skillmeat list --type workflow` CLI command returns synced workflows in correct format | CLI output includes all synced workflows; format matches other artifact type output | 1 pt | WAW-P3.3 |

**Phase 5 Quality Gates**:
- [ ] All unit tests pass; coverage >80% for new code
- [ ] All integration tests pass; no N+1 query issues
- [ ] E2E tests pass; critical user journeys work
- [ ] No regressions in existing artifact types (skills, agents, composites)
- [ ] CLI integration test passes
- [ ] Load test confirms sync call completes within 100 ms p99

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|:------:|:----------:|-------------------|
| Sync failure causes silent data inconsistency | Medium | Medium | Emit structured log + metric on every sync; expose via `/health` endpoint; provide manual re-sync via `POST /cache/refresh` |
| Migration breaks existing deployment set queries | High | Low | Additive migration only (nullable column); existing queries unaffected; CI tests before merge |
| Duplicate `artifacts` rows on concurrent create | Medium | Low | DB-level `ON CONFLICT DO UPDATE` upsert (SQLite + PostgreSQL); idempotent by design; unit test concurrent calls |
| N+1 query on collection listing | Medium | Medium | Batch-load or join in repository; validate with query assertion in integration test |
| Frontend link-through breaks for soft-deleted workflows | Low | Medium | Check workflow existence before rendering link; show "archived" badge if workflow record is gone |

---

## Resource Requirements

### Team Composition

- **Backend Engineers** (Data/Service/API): 2 FTE for Phases 1-3 (5-6 days)
- **Frontend Engineers** (UI): 1 FTE for Phase 4 (1 day) + part-time testing
- **Code Reviewers**: Senior code reviewer for Phase 5 (part-time during testing)

### Skills Required

- Python/FastAPI, SQLAlchemy 2.x, Alembic migrations
- TypeScript/React, React Query, Next.js App Router
- PostgreSQL + SQLite, Git, CI/CD, OpenTelemetry, pytest

---

## Success Metrics

### Delivery Metrics
- On-time delivery (±10%)
- All 13 user stories completed
- Code coverage >80% for new code
- Zero breaking changes to existing API endpoints

### Functional Metrics
- Workflow artifact count in collection == workflows table count
- Deployment sets accept workflow_id parameter and persist correctly
- Collection Workflows tab renders real artifact cards (not empty)
- `skillmeat list --type workflow` returns synced workflows

### Technical Metrics
- Sync service completes within 100 ms p99
- No N+1 queries in collection listing
- OTel spans emitted correctly
- Feature flag can be toggled without redeployment

---

## Communication Plan

- Daily standups (15 min) for blockers/progress
- Phase-end reviews (30 min) before moving to next phase
- Weekly stakeholder updates (status, risks, blockers)

---

## Post-Implementation

- Monitor sync latency metrics in production
- Validate data consistency (artifact count == workflows count)
- Collect user feedback on collection UI improvements
- Plan Tier 3 Deployment feature (dependent on this wiring)

---

**Progress Tracking:**

See `.claude/progress/workflow-artifact-wiring/all-phases-progress.md`

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-10
