---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 3-4: History & RBAC"
description: >
  History capture layer (Phase 3) + AAA/RBAC scoped metadata (Phase 4).
  Integrates owner scoping and event recording into the core architecture.
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
  - rbac
created: 2026-03-10
updated: 2026-03-10
phase: 3-4
phase_title: "History & RBAC: Event Capture & Owner Scoping"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 1-2 models and generators complete and tested
  - BomSnapshot and ArtifactHistoryEvent models available
  - AttestationRecord model with owner_type/owner_id fields ready
exit_criteria:
  - ArtifactHistoryRepository CRUD + query interface complete
  - History events recorded on all artifact mutations (create/update/delete/deploy/sync)
  - Fire-and-forget writes verified to not block mutations
  - AttestationScopeResolver enforces owner-scoped visibility
  - Enterprise policy fields configurable per tenant
  - RBAC unit tests verify correct access control per owner type
feature_slug: skillbom-attestation
effort_estimate: "20-24 story points"
timeline: "2 weeks"
parallelization: "Phase 3 and Phase 4 can run in parallel after models lock"
---

# SkillBOM & Attestation System - Phases 3-4: History & RBAC

## Overview

Phases 3-4 add two critical capabilities:
1. **Phase 3**: Immutable history event logging with SQLAlchemy event listeners on artifact mutations
2. **Phase 4**: Owner-scoped attestation metadata (user/team/enterprise) with RBAC enforcement

These phases enable time-ordered querying, audit trails per team, and enterprise policy enforcement.

---

## Phase 3: History Capture Layer

**Duration**: 2 weeks | **Effort**: 12-14 story points | **Assigned**: python-backend-engineer, data-layer-expert

### Overview

Implement the `ArtifactHistoryRepository` and integrate SQLAlchemy event listeners to capture lifecycle events on all artifact mutations. Events are recorded asynchronously (fire-and-forget) to avoid blocking mutation responses.

Key design: History writes must not block or fail mutations. Failures are logged as warnings but do not propagate.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 3.1 | Create `IArtifactHistoryRepository` ABC | Interface in `skillmeat/core/interfaces/repositories.py`. Methods: create_event(artifact_id, event_type, actor_id, diff_json, content_hash) → event_id; list_events(artifact_id, event_type=None, time_range=None, actor_id=None) → List[HistoryEventDTO]; get_event(event_id) → HistoryEventDTO; event count by artifact/type. | ABC defined with clear contracts; all methods documented; return types (DTOs) specified | 2 | Pending |
| 3.2 | Implement `LocalArtifactHistoryRepository` | SQLAlchemy 1.x style repository for SQLite. Uses session.query() on ArtifactHistoryEvent table. Supports all IArtifactHistoryRepository methods. | Repository instantiates; CRUD operations work on SQLite; events are immutable (no UPDATE/DELETE exposed); queries return correct filtered results | 3 | Pending |
| 3.3 | Implement `EnterpriseArtifactHistoryRepository` | SQLAlchemy 2.x style repository for PostgreSQL. Uses select() syntax. Supports all IArtifactHistoryRepository methods plus multi-tenant filtering (tenant_id). | Repository instantiates; select() queries work on PostgreSQL; tenant isolation enforced (no cross-tenant leakage); performance acceptable for large event logs | 3 | Pending |
| 3.4 | Create `ArtifactHistoryService` | Service layer in `skillmeat/core/bom/history.py`. Responsibilities: (1) Accept mutation event from router/service, (2) Extract diff (before/after JSON), (3) Capture actor_id from AuthContext, (4) Queue async write via background task, (5) Return immediately without waiting. Fire-and-forget pattern. | Service instantiates; record_event() returns immediately without blocking; background task executes write; failures logged without propagating | 3 | Pending |
| 3.5 | SQLAlchemy event listeners on Artifact/Collection/etc | Register after_insert, after_update, after_delete event listeners on Artifact ORM model. Listeners trigger ArtifactHistoryService.record_event() in background. Listeners must not fail (wrapped in try-except). | Listeners register and fire on artifact mutations; history events recorded; listener failures logged but mutations continue; no impact on mutation response time | 3 | Pending |
| 3.6 | History query service with filters | Service methods: query_by_artifact(artifact_id, limit, offset), query_by_actor(actor_id, limit, offset), query_by_time_range(start, end, limit, offset), query_by_event_type(event_type, limit, offset). All return paginated DTOs. | Query service returns correct filtered events; pagination works correctly; queries execute in < 200ms p95 for 100-event result sets | 2 | Pending |
| 3.7 | Diff generation between history snapshots | Utility function to compute JSON diff between two artifact states (before/after). Store diff in ArtifactHistoryEvent.diff_json for later analysis. Option: use simple dict diff or library like deepdiff. | Diff captures all field changes; stored as compact JSON; diff can be reversed to reconstruct prior state; size reasonable (not bloating DB) | 2 | Pending |
| 3.8 | Integration: Memory item history capture | Extend history capture to MemoryItem model. When a memory item is created/updated/deleted, record event with item.id, item.project_id, and content_hash of item.text. | Memory item events recorded alongside artifact events; query service filters by memory_item type; content hashes capture text changes | 1 | Pending |
| 3.9 | Load test: History writes don't block mutations | Load test with 100 concurrent mutation requests, verify no blocking and no response time degradation. Use OpenTelemetry spans to measure. | Load test completes without errors; mutation response times unchanged (< 50ms p95) with history recording enabled; background tasks complete within 5s | 2 | Pending |

### Key Design Notes

- **Fire-and-Forget Pattern**: Use FastAPI `BackgroundTasks` or Celery (if available) to queue history writes. Do not use sync writes.
- **Error Handling**: If history write fails, log the error and continue. Never block mutations.
- **Diff Generation**: Use `json.dumps(dict_diff(before, after))` for simple diffs; consider library for complex structures but keep it lightweight.
- **Event Ordering**: Rely on database timestamp ordering (created_at) and immutability to ensure event log is chronologically ordered.
- **Actor Attribution**: Capture actor_id from `AuthContext.user_id` at time of mutation. Store as string UUID.
- **Owner Type**: Inherit owner_type from mutation's AuthContext (user/team/enterprise).

### Deliverables

1. **Code**:
   - `skillmeat/core/interfaces/repositories.py` — Add IArtifactHistoryRepository ABC
   - `skillmeat/core/repositories/local_artifact_history.py` — LocalArtifactHistoryRepository
   - `skillmeat/cache/enterprise_repositories.py` — Add EnterpriseArtifactHistoryRepository
   - `skillmeat/core/bom/history.py` — ArtifactHistoryService + event listeners
   - `skillmeat/api/dependencies.py` — Add HistoryRepositoryDep DI alias

2. **Tests**:
   - `skillmeat/core/tests/test_artifact_history_repository.py` — Repository CRUD tests
   - `skillmeat/core/tests/test_artifact_history_service.py` — Service and listener tests
   - `skillmeat/core/tests/test_history_load.py` — Load test for non-blocking writes

### Exit Criteria

- [ ] IArtifactHistoryRepository ABC defined with complete contracts
- [ ] Local and enterprise repository implementations pass all CRUD tests
- [ ] SQLAlchemy event listeners fire correctly on artifact mutations
- [ ] History events recorded without blocking mutation responses
- [ ] Load test verifies no response time degradation with history enabled
- [ ] Memory item history capture integrated
- [ ] Query service returns filtered, paginated results

---

## Phase 4: AAA/RBAC Scoped Metadata

**Duration**: 1 week | **Effort**: 8-10 story points | **Assigned**: python-backend-engineer

### Overview

Integrate owner-scoping from `AuthContext` into attestation records. Implement `AttestationScopeResolver` to enforce visibility rules (users see only their records, teams see team records, admins see all).

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 4.1 | Create `AttestationScopeResolver` | Utility in `skillmeat/core/bom/scope.py`. Methods: (1) determine_owner_type(auth_context) → OwnerType enum, (2) filter_attestations(auth_context, all_attestations) → visible_attestations, (3) check_visibility(auth_context, attestation_record) → bool. | Resolver instantiates; filters apply correct RBAC rules; team members cannot see other teams' records; users see only own records | 2 | Pending |
| 4.2 | Populate `AttestationRecord` on BOM creation | When BomGenerator produces a snapshot, create corresponding AttestationRecord with owner_type/owner_id/roles/scopes from AuthContext. Service layer handles this. | AttestationRecord created alongside BomSnapshot; owner fields populated from AuthContext; visibility set based on creator's scope | 2 | Pending |
| 4.3 | Owner type enrichment on mutation events | ArtifactHistoryEvent records include owner_type from AuthContext of the mutating actor. This enables team-level audit trails. | History events include owner_type; team_id (if applicable) stored for team-scoped filtering | 2 | Pending |
| 4.4 | Enterprise policy enforcement model | Extend AttestationPolicy model (from Phase 1) with enforcement logic. Methods: (1) validate_required_artifacts(bom, policy) → bool, (2) extract_compliance_metadata(audit_context) → dict. Enterprise edition only. | Policy model supports required_artifacts validation; compliance metadata extracted and stored; local edition stubs these methods | 2 | Pending |
| 4.5 | RBAC unit tests for attestation visibility | Tests verify: (1) User A cannot see User B's attestation records, (2) Team member sees all team records, (3) Team admin sees enterprise records, (4) System admin sees everything. | All visibility tests pass; no cross-tenant/cross-user data leakage; role hierarchy respected | 2 | Pending |

### Key Design Notes

- **Owner Type Enum**: Use existing `OwnerType` from `skillmeat/cache/auth_types.py` (user/team/enterprise).
- **Team ID**: If AuthContext includes team_id, store in AttestationRecord for team-scoped filtering.
- **Role/Scope Attribution**: Capture roles and scopes at time of attestation (AuthContext.roles, AuthContext.scopes) for future compliance audits.
- **Visibility Enum**: Use existing `Visibility` (private/team/public) — combine with owner_type for complete access control.
- **Enterprise Policy**: Keep policy enforcement in service layer; routers call service which applies policy before returning data.

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/scope.py` — AttestationScopeResolver utility
   - `skillmeat/core/services/bom_service.py` — Service layer for BOM/attestation with policy enforcement
   - Modified `skillmeat/api/dependencies.py` — Add ScopeResolverDep

2. **Tests**:
   - `skillmeat/core/tests/test_attestation_scope_resolver.py` — Visibility and filtering tests
   - `skillmeat/api/tests/test_bom_attestation_rbac.py` — Integration tests for RBAC enforcement

### Exit Criteria

- [ ] AttestationScopeResolver enforces correct visibility per user/team/enterprise
- [ ] AttestationRecord populated with owner_type/owner_id on creation
- [ ] History events include owner_type for team-level auditing
- [ ] Enterprise policy fields configurable per tenant
- [ ] No cross-tenant or cross-user data leakage in queries
- [ ] All RBAC unit tests pass
- [ ] Role hierarchy (system_admin > team_admin > team_member > viewer) enforced

---

## Integration Points

### From Phase 3 → Phase 4
- AttestationScopeResolver uses owner_type from ArtifactHistoryEvent
- History query service respects owner-scoped visibility

### To Phase 7 (API)
- API endpoints use AttestationScopeResolver to filter results before returning
- History and attestation endpoints are owner-scoped by design

### To Phase 5-6 (Git & Crypto)
- Attestation owner info is included in signed BOM for auditability
- Signature chains track which user/team authorized each version

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| History write blocks mutations under load | Fire-and-forget with background tasks; monitor task queue depth |
| RBAC bypass vulnerability | Comprehensive unit tests for all visibility rules; code review by security expert |
| Performance regression on history queries | Indexes on (artifact_id, timestamp) and (event_type, timestamp); paginated queries only |
| Data leakage across tenants | Unit tests for cross-tenant visibility; NEVER skip owner_type filter in queries |

---

## Success Metrics

- **History Recording**: 100% of artifact mutations logged, < 50ms latency
- **Query Performance**: History query (100 events) returns in < 200ms p95
- **RBAC Correctness**: 100% of visibility tests pass; no data leakage
- **Load Test**: 100 concurrent mutations without response time degradation

---

## Next Steps (Gate to Phase 5)

1. ✅ Phase 3-4 exit criteria verified
2. ✅ History repository tested with both SQLite and PostgreSQL
3. ✅ RBAC visibility rules validated by security engineer
4. ✅ Phase 5 (Git Integration) can begin

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-03, FR-04, FR-05, FR-06
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **Auth Architecture**: `.claude/context/key-context/auth-architecture.md`
- **Repository Pattern**: `.claude/context/key-context/repository-architecture.md`
- **Data Flow**: `.claude/context/key-context/data-flow-patterns.md`
