---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 3-4: Activity & RBAC"
description: >
  Artifact activity history layer (Phase 3) + AAA/RBAC scoped metadata (Phase 4).
  Establishes a provenance-grade audit stream separate from existing version-lineage history.
audience:
  - ai-agents
  - developers
  - backend-engineers
  - security-engineers
tags:
  - implementation-plan
  - phases
  - skillbom
  - history
  - activity-log
  - rbac
created: 2026-03-10
updated: 2026-03-11
phase: 3-4
phase_title: "Activity & RBAC: Event Capture & Owner Scoping"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 1-2 models and generators complete and tested
  - BomSnapshot and ArtifactHistoryEvent models available
  - AttestationRecord model with owner_type/owner_id fields ready
exit_criteria:
  - Artifact activity repository + query interface complete
  - Activity events recorded from artifact/deploy/sync/BOM/attestation flows
  - Fire-and-forget writes verified to not block mutations
  - Ownership resolution supports user/team/enterprise
  - AttestationScopeResolver enforces owner-scoped visibility
  - Enterprise policy fields configurable per tenant
  - RBAC unit tests verify correct access control per owner type
feature_slug: skillbom-attestation
effort_estimate: "20-24 story points"
timeline: "2 weeks"
parallelization: "Phase 3 and Phase 4 can run in parallel after models lock"
---

# SkillBOM & Attestation System - Phases 3-4: Activity & RBAC

## Overview

Phases 3-4 add two critical capabilities:
1. **Phase 3**: Immutable artifact activity history captured from explicit service/repository events
2. **Phase 4**: Owner-scoped attestation metadata (`user`/`team`/`enterprise`) with RBAC enforcement

These phases enable time-ordered audit trails, provenance selection for BOM views, team and enterprise reporting, and policy enforcement.

Important architectural boundary:

- The existing `/api/v1/artifacts/{id}/history` surface remains the version-lineage / rollback timeline.
- `ArtifactHistoryEvent` becomes the backing store for a separate activity/audit stream used by BOM provenance and attestation workflows.

---

## Phase 3: Artifact Activity History

**Duration**: 2 weeks | **Effort**: 12-14 story points | **Assigned**: python-backend-engineer, data-layer-expert

### Overview

Implement the artifact activity history pipeline around `ArtifactHistoryEvent`. Capture must happen from explicit domain events in write-through repository/service flows so filesystem-first operations are not missed.

Key design: activity writes must not block or fail the primary mutation path. Failures are logged as warnings but do not propagate.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 3.1 | Create `IArtifactActivityRepository` ABC | Interface in `skillmeat/core/interfaces/repositories.py`, adjacent to the existing version-lineage history interfaces. Methods: `create_event(...)`, `list_events(...)`, `get_event(...)`, `list_provenance_slice(...)`. | Interface defined with clear contracts; naming distinguishes activity history from existing artifact version history; DTOs specified | 2 | Pending |
| 3.2 | Implement `LocalArtifactActivityRepository` | SQLAlchemy 1.x style repository for SQLite using `ArtifactHistoryEvent` as the backing table. | Repository instantiates; CRUD operations work on SQLite; events are immutable; queries return correct filtered results | 3 | Pending |
| 3.3 | Implement `EnterpriseArtifactActivityRepository` | SQLAlchemy 2.x style repository for PostgreSQL. Supports multi-tenant filtering and enterprise ownership semantics. | Repository instantiates; select() queries work on PostgreSQL; tenant isolation enforced; performance acceptable for large event logs | 3 | Pending |
| 3.4 | Create `ArtifactActivityService` | Service layer in `skillmeat/core/bom/history.py`. Responsibilities: accept explicit activity events from services/repos, extract diff where relevant, capture actor and ownership context, queue async write, return immediately. | Service instantiates; `record_event()` returns immediately without blocking; background task executes write; failures logged without propagating | 3 | Pending |
| 3.5 | Emit events from write-through boundaries | Add explicit event emission to artifact mutations, deployment flows, sync flows, memory operations, BOM generation/sign/verify/restore, and attestation actions. Do not rely on ORM listeners. | Events recorded for filesystem-first and DB-backed flows; deployment/sync/BOM actions represented; capture points documented; no measurable mutation regression | 3 | Pending |
| 3.6 | Activity query service with provenance filters | Service methods support filters by artifact, actor, event_type, time_range, owner scope, and provenance relevance. | Query service returns correct filtered events; pagination works correctly; provenance slice for BOM surfaces derived without duplicating storage | 2 | Pending |
| 3.7 | Diff generation for activity records | Utility function to compute compact JSON diffs between before/after states where relevant. Store diff in `ArtifactHistoryEvent.diff_json`. | Diff captures meaningful field/file changes; stored compactly; non-diffable actions use structured metadata instead of empty placeholder diffs | 2 | Pending |
| 3.8 | Integration: Memory item activity capture | Extend activity capture to `MemoryItem` create/update/delete and BOM inclusion/exclusion actions. | Memory-item events recorded alongside artifact events; provenance queries can include or exclude memory actions intentionally | 1 | Pending |
| 3.9 | Load test: Activity writes don't block mutations | Load test with 100 concurrent mutation requests. Verify no blocking and no response-time degradation. | Load test completes without errors; mutation response times unchanged (< 50ms p95) with activity recording enabled; background tasks complete within 5s | 2 | Pending |

### Key Design Notes

- **Separate from Existing Artifact History**: Keep the current version-lineage history surface intact. This phase adds a new audit/provenance stream, not a replacement.
- **Fire-and-Forget Pattern**: Use FastAPI `BackgroundTasks` or equivalent to queue activity writes. Do not use synchronous writes on critical mutation paths.
- **Capture Strategy**: Emit from service/repository/domain-event boundaries, especially filesystem-first write-through flows. Do not rely on SQLAlchemy listeners.
- **Diff Generation**: Use compact JSON diffs where relevant; store structured metadata for operational events such as sign/verify/restore.
- **Actor Attribution**: Capture `actor_id` from `AuthContext.user_id` and store as string UUID.
- **Owner Attribution**: Capture resolved `owner_type` and `owner_id` from the ownership resolver (`user`/`team`/`enterprise`).

### Deliverables

1. **Code**:
   - `skillmeat/core/interfaces/repositories.py` — Add `IArtifactActivityRepository` ABC
   - `skillmeat/core/repositories/local_artifact_activity.py` — Local activity repository
   - `skillmeat/cache/enterprise_repositories.py` — Add enterprise activity repository
   - `skillmeat/core/bom/history.py` — `ArtifactActivityService` + provenance selection
   - `skillmeat/api/dependencies.py` — Add activity repository DI alias

2. **Tests**:
   - `skillmeat/core/tests/test_artifact_activity_repository.py` — Repository CRUD tests
   - `skillmeat/core/tests/test_artifact_activity_service.py` — Service and event-emission tests
   - `skillmeat/core/tests/test_activity_load.py` — Load test for non-blocking writes

### Exit Criteria

- [ ] `IArtifactActivityRepository` ABC defined with complete contracts
- [ ] Local and enterprise repository implementations pass all CRUD tests
- [ ] Explicit event emission wired into artifact/deploy/sync/BOM/attestation flows
- [ ] Activity events recorded without blocking mutation responses
- [ ] Load test verifies no response time degradation with activity enabled
- [ ] Memory-item activity capture integrated
- [ ] Query service returns filtered, paginated results

---

## Phase 4: AAA/RBAC Scoped Metadata

**Duration**: 1 week | **Effort**: 8-10 story points | **Assigned**: python-backend-engineer

### Overview

Integrate owner-scoping from `AuthContext` and ownership-resolution helpers into attestation records. Implement `AttestationScopeResolver` to enforce visibility rules across `user`, `team`, and `enterprise` ownership.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 4.1 | Create ownership resolver for `user|team|enterprise` | Utility in `skillmeat/core/bom/scope.py` that resolves effective `owner_type` / `owner_id` from auth context plus membership/tenant data. Do not assume raw `team_id` on `AuthContext`. | Resolver instantiates; ownership resolution works for user, team, and enterprise cases; precedence rules documented | 2 | Pending |
| 4.2 | Create `AttestationScopeResolver` | Utility in `skillmeat/core/bom/scope.py` for filtering attestations and checking visibility. | Resolver instantiates; filters apply correct RBAC rules; team members cannot see other teams' records; enterprise visibility follows admin policy | 2 | Pending |
| 4.3 | Populate `AttestationRecord` on BOM creation | When BomGenerator produces a snapshot, create corresponding AttestationRecord with owner_type/owner_id/roles/scopes from resolved ownership context. | AttestationRecord created alongside BomSnapshot; owner fields populated correctly; visibility set based on creator scope | 2 | Pending |
| 4.4 | Owner type enrichment on activity events | `ArtifactHistoryEvent` records include resolved owner_type for the acting principal. | Activity events include owner_type; owner_id populated consistently for user/team/enterprise scopes | 2 | Pending |
| 4.5 | Enterprise policy enforcement model | Extend `AttestationPolicy` with enforcement logic. Methods: `validate_required_artifacts(...)`, `extract_compliance_metadata(...)`. | Policy model supports required_artifacts validation; compliance metadata extracted and stored; local edition stubs these methods | 2 | Pending |
| 4.6 | RBAC unit tests for attestation visibility | Tests verify: user isolation, team isolation, enterprise-owner visibility, and system-admin visibility. | All visibility tests pass; no cross-tenant/cross-user leakage; role hierarchy respected | 2 | Pending |

### Key Design Notes

- **Owner Type Enum**: Extend and use `OwnerType` from `skillmeat/cache/auth_types.py` with `user`, `team`, and `enterprise`.
- **Ownership Resolution**: Resolve team and enterprise ownership via a dedicated resolver/membership lookup; do not assume `team_id` is present on `AuthContext`.
- **Role/Scope Attribution**: Capture roles and scopes at time of attestation for future compliance audits.
- **Visibility Enum**: Use existing `Visibility` (`private`, `team`, `public`) combined with owner type.
- **Enterprise Policy**: Keep policy enforcement in the service layer; routers call services which apply policy before returning data.

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/scope.py` — Ownership resolver + `AttestationScopeResolver`
   - `skillmeat/core/services/bom_service.py` — Service layer for BOM/attestation with policy enforcement
   - `skillmeat/api/dependencies.py` — Add scope/ownership resolver dependencies as needed

2. **Tests**:
   - `skillmeat/core/tests/test_ownership_resolver.py` — Ownership resolution tests
   - `skillmeat/core/tests/test_attestation_scope_resolver.py` — Visibility and filtering tests
   - `skillmeat/api/tests/test_bom_attestation_rbac.py` — Integration tests for RBAC enforcement

### Exit Criteria

- [ ] Ownership resolution works for user/team/enterprise
- [ ] `AttestationScopeResolver` enforces correct visibility per user/team/enterprise
- [ ] `AttestationRecord` populated with owner_type/owner_id on creation
- [ ] Activity events include owner_type for team/enterprise auditing
- [ ] Enterprise policy fields configurable per tenant
- [ ] No cross-tenant or cross-user data leakage in queries
- [ ] All RBAC unit tests pass
- [ ] Role hierarchy (`system_admin > team_admin > team_member > viewer`) enforced

---

## Integration Points

### From Phase 3 → Phase 4
- `AttestationScopeResolver` uses owner_type from `ArtifactHistoryEvent`
- Activity query service respects owner-scoped visibility

### To Phase 7 (API)
- API endpoints use activity and attestation services separately
- Existing artifact version-history endpoint remains unchanged
- New provenance/activity surfaces are owner-scoped by design

### To Phase 5-6 (Git & Crypto)
- Attestation owner info is included in signed BOMs for auditability
- Signature chains track which user/team/enterprise authorized each version

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Activity write blocks mutations under load | Fire-and-forget with background tasks; monitor task queue depth |
| Audit gaps in filesystem-first flows | Emit activity from repository/service boundaries; avoid ORM-listener dependence |
| RBAC bypass vulnerability | Comprehensive unit tests for all visibility rules; code review by security expert |
| Data leakage across tenants | Unit tests for cross-tenant visibility; never skip owner_type filter in queries |

---

## Success Metrics

- **Activity Recording**: 100% of targeted artifact/deploy/sync/BOM/attestation actions logged, < 50ms capture latency
- **Query Performance**: Activity query (100 events) returns in < 200ms p95
- **RBAC Correctness**: 100% of visibility tests pass; no data leakage
- **Load Test**: 100 concurrent mutations without response time degradation

---

## Next Steps (Gate to Phase 5)

1. ✅ Phase 3-4 exit criteria verified
2. ✅ Activity repository tested with both SQLite and PostgreSQL
3. ✅ RBAC visibility rules validated by security engineer
4. ✅ Phase 5 (Git Integration) can begin

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-03, FR-04, FR-05, FR-06
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **Auth Architecture**: `.claude/context/key-context/auth-architecture.md`
- **Repository Pattern**: `.claude/context/key-context/repository-architecture.md`
- **Data Flow**: `.claude/context/key-context/data-flow-patterns.md`
