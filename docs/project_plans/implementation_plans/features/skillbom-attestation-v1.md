---
schema_version: 2
doc_type: implementation_plan
title: "SkillBOM & Attestation System - Implementation Plan"
description: >
  Comprehensive phased implementation plan for cryptographic tracking and provenance of AI artifacts,
  with separate artifact activity history, RBAC-scoped attestation metadata, and multi-surface viewing.
audience:
  - ai-agents
  - developers
  - security-engineers
  - platform-engineers
tags:
  - implementation-plan
  - planning
  - features
  - skillbom
  - security
  - attestation
created: 2026-03-10
updated: 2026-03-10
category: product-planning
status: draft
priority: HIGH
risk_level: high
feature_slug: skillbom-attestation
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: null
scope: full-stack
effort_estimate: "78-90 story points"
timeline: "12-16 weeks"
critical_path: "Phase 1 → Phase 2 → Phase 3 → Phase 7 → Phase 9"
parallelization_strategy: "Parallel tracks after Phase 2 (DB models established)"
related_documents:
  - /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
  - /.claude/context/key-context/repository-architecture.md
  - /.claude/context/key-context/data-flow-patterns.md
  - /.claude/context/key-context/auth-architecture.md
---

# SkillBOM & Attestation System - Implementation Plan

**Complexity**: Large (L) | **Track**: Full Track | **Estimated Effort**: 78-90 story points | **Timeline**: 12-16 weeks

---

## Executive Summary

This implementation plan breaks down the SkillBOM & Attestation System (from PRD: `skillbom-attestation-v1.md`) into 11 phased workstreams with explicit subagent assignments. The system introduces cryptographic bill-of-materials tracking for all 13+ AI artifact types, with separate artifact activity history, owner-scoped attestation metadata, and multi-surface viewing (CLI, API, web app, Backstage backend integration).

The plan follows MeatyPrompts' layered hexagonal architecture, with clear separation between database models, repositories, services, and API routers. Both local (SQLite + SQLAlchemy 1.x) and enterprise (PostgreSQL + SQLAlchemy 2.x) editions are designed in parallel through the `RepositoryFactory` pattern.

**Key Milestones:**
- **Phase 1-2** (Weeks 1-3): Universal schema and BOM generation foundation
- **Phase 3-4** (Weeks 4-6): Artifact activity capture and RBAC metadata integration
- **Phase 5-6** (Weeks 7-9): Git integration and cryptographic signing
- **Phase 7-8** (Weeks 10-12): API layer and CLI commands
- **Phase 9-10** (Weeks 13-15): Web app and Backstage backend integration
- **Phase 11** (Week 16): Testing, docs, and deployment

**Critical Dependencies:**
- Completion of Phase 1 (models) gates all subsequent phases
- Phase 2 (BOM generator) must complete before Phase 3 (history capture)
- Phase 7 (API) is gateway to Phases 9-10 (front-end surfaces)

---

## Phase Overview

| Phase | Title | Duration | Effort | Key Deliverables | Assigned Agents |
|-------|-------|----------|--------|------------------|-----------------|
| 1 | Universal Schema & Data Models | 2 wks | 13-15 pts | SQLAlchemy models (6), Pydantic schemas, Alembic migrations | data-layer-expert |
| 2 | BOM Generation Service | 2 wks | 14-16 pts | BomGenerator service, 13+ type adapters, serializer | python-backend-engineer |
| 3 | Artifact Activity History | 2 wks | 12-14 pts | Activity repository, explicit event capture, provenance query service | python-backend-engineer, data-layer-expert |
| 4 | AAA/RBAC Scoped Metadata | 1 wk | 8-10 pts | AttestationScopeResolver, owner enrichment, policy enforcement | python-backend-engineer |
| 5 | Git Commit Integration | 1 wk | 8-10 pts | Git hook installer, commit-linked BOM retrieval, agent tool | python-backend-engineer |
| 6 | Cryptographic Signing | 1 wk | 6-8 pts | Ed25519 signing/verification, signature chain validation | python-backend-engineer |
| 7 | API Layer | 2 wks | 16-18 pts | 8 endpoints, auth middleware, response pagination | python-backend-engineer |
| 8 | CLI Commands | 2 wks | 12-14 pts | bom/history/attest commands, scaffolder integration | python-backend-engineer |
| 9 | Web App Integration | 2 wks | 14-16 pts | ProvenanceTab, BomViewer, AttestationBadge, HistoryTimeline, hooks | ui-engineer-enhanced |
| 10 | Backstage Backend Integration | 1 wk | 5-7 pts | Extend idp_integration router, payload contract, scaffolder actions | python-backend-engineer |
| 11 | Testing, Docs, Deployment | 2 wks | 14-16 pts | Unit, integration, migration tests; API docs; CI/CD guides | python-backend-engineer, documentation-writer |

**Total Estimated Effort: 78-90 story points**
**Recommended Team**: 1-2 backend engineers (Sonnet), 1 data-layer expert (Sonnet), 1-2 UI engineers (Sonnet)

---

## Implementation Strategy

### Architecture Patterns

1. **Hexagonal Repositories**: All BOM data access through `IBomRepository` ABC with local/enterprise implementations via `RepositoryFactory`.
2. **Dual History Model**: Existing version-lineage history remains intact; new artifact activity history captures audit/provenance events and feeds SkillBOM views.
3. **Explicit Domain Event Capture**: Activity events are emitted from repository/service boundaries in write-through flows, not inferred from ORM listeners.
4. **Owner-Scoped Queries**: All attestation/activity queries filtered by resolved `user|team|enterprise` ownership — no cross-tenant/cross-owner data leakage.
5. **Deterministic BOM Payloads**: BOM content ordering and hashing are deterministic; ephemeral generation metadata is stored separately from signed/hashed payloads.

### Parallel Work Opportunities

**After Phase 2 (models + generator ready):**
- Phase 3 (history capture) can run parallel to Phase 4 (RBAC metadata)
- Phase 5-6 (Git + crypto) are largely independent, can parallelize
- Phase 9-10 (web + Backstage) can parallelize after Phase 7 API is stable

**Sequential Dependencies (Critical Path):**
1. Phase 1 (models) → Phase 2 (BomGenerator) → Phase 7 (API)
2. Phase 3 (history) → Phase 7 (API) [history endpoint needs history data]
3. Phase 7 (API) → Phases 9-10 (front-end surfaces)

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Activity capture misses filesystem-first mutations | Emit events explicitly from repository/service boundaries in deploy/sync/BOM flows; do not rely on ORM listeners |
| `context.lock` grows too large | Track only active deployed artifacts; configurable artifact limit (50 default) |
| Enterprise/local schema divergence | Strict type checking; unit tests for both SQLite and PostgreSQL paths |
| Version skew in restored state | Restore uses content_hash + parent_hash chain; validation before write |
| Backstage frontend scope leaks into backend module | Restrict Phase 10 to backend/scaffolder work; track frontend EntityPage card as follow-on |

---

## Detailed Phase Breakdown

Implementation details for each phase are in the following linked documents:

### Phases 1-2: Foundation
**File**: [`phase-1-2-foundation.md`](./skillbom-attestation-v1/phase-1-2-foundation.md)
- Phase 1: Universal Schema & Data Models
- Phase 2: BOM Generation Service

### Phases 3-4: Activity & RBAC
**File**: [`phase-3-4-history-rbac.md`](./skillbom-attestation-v1/phase-3-4-history-rbac.md)
- Phase 3: Artifact Activity History
- Phase 4: AAA/RBAC Scoped Metadata

### Phases 5-6: Git & Crypto
**File**: [`phase-5-6-git-crypto.md`](./skillbom-attestation-v1/phase-5-6-git-crypto.md)
- Phase 5: Git Commit Integration
- Phase 6: Cryptographic Signing

### Phases 7-8: API & CLI
**File**: [`phase-7-8-api-cli.md`](./skillbom-attestation-v1/phase-7-8-api-cli.md)
- Phase 7: API Layer
- Phase 8: CLI Commands

### Phases 9-10: Web & Backstage Backend
**File**: [`phase-9-10-web-backstage.md`](./skillbom-attestation-v1/phase-9-10-web-backstage.md)
- Phase 9: Web App Integration
- Phase 10: Backstage Backend Integration

### Phase 11: Validation & Deployment
**File**: [`phase-11-validation.md`](./skillbom-attestation-v1/phase-11-validation.md)
- Phase 11: Testing, Docs, Deployment

---

## Quality Gates

### Phase 1 Exit Criteria
- All 6 models (AttestationRecord, ArtifactHistoryEvent, BomSnapshot, AttestationPolicy, BomMetadata, ScopeValidator) defined in `cache/models.py`
- Alembic migrations pass on both SQLite and PostgreSQL test databases
- Pydantic schemas in `api/schemas/bom.py` validate all 13+ artifact types
- Unit tests for model relationships pass (foreign keys, cascades, indexes)

### Phase 2 Exit Criteria
- `BomGenerator` class instantiates and generates valid JSON per BOM v2.0 schema
- All 13+ artifact type adapters implemented and tested
- `context.lock` file produced with correct format and content hashes
- Performance: BOM generation for 50 artifacts completes in < 2s

### Phase 3 Exit Criteria
- Activity events recorded on artifact, deployment, sync, BOM, and attestation actions
- Fire-and-forget write does not block mutation responses (verified with load test)
- Activity query service returns paginated results with filters (artifact_id, event_type, time_range, actor_id)
- Unit tests for activity repository CRUD operations pass

### Phase 4 Exit Criteria
- AttestationRecord populated with owner_type/owner_id from resolved ownership context
- Owner-scope filtering enforced (user/team/enterprise)
- Enterprise policy fields (required_artifacts, required_scopes) configurable per tenant
- RBAC tests verify correct access control per owner type

### Phase 5 Exit Criteria
- `skillmeat bom install-hook` creates valid Git hook set in `.git/hooks/`
- Commit-message footer appended via `prepare-commit-msg` or `commit-msg`, with final commit linkage handled post-commit
- `skillmeat restore --commit <hash>` fetches BOM from target commit and rehydrates `.claude/`
- `generate_attestation` tool callable from Claude Code agents

### Phase 6 Exit Criteria
- Ed25519 signing/verification using existing `skillmeat/security/crypto.py`
- `skillmeat bom sign` produces valid signature file with correct format
- `skillmeat bom verify` validates signature chain and reports VALID/INVALID
- Signature verification unit tests pass for both signed and tampered BOMs

### Phase 7 Exit Criteria
- All 8 API endpoints implemented with correct HTTP status codes
- Auth middleware enforces scope-based access (artifact:read, artifact:write, admin:*)
- Response pagination (cursor-based) implemented per project standard
- OpenAPI spec updated and auto-generated documentation correct
- Integration tests verify all endpoints with both local and enterprise auth flows

### Phase 8 Exit Criteria
- `skillmeat bom generate`, `verify`, `restore` CLI commands fully functional
- `skillmeat history [artifact-name]` returns formatted timeline
- `skillmeat attest create/list/show` commands manage attestation records
- CLI help text and error messages clear and actionable
- All commands work in local and enterprise editions

### Phase 9 Exit Criteria
- ProvenanceTab component renders on artifact detail pages
- BomViewer displays structured context.lock contents
- HistoryTimeline shows time-ordered events with keyboard navigation
- WCAG 2.1 AA compliance verified with accessibility audit
- API hooks (`useArtifactActivityHistory`, `useBomSnapshot`, `useAttestations`) tested

### Phase 10 Exit Criteria
- `/integrations/idp/bom-card/{project_id}` endpoint returns Backstage-renderable payload
- Payload contract documented for future Backstage frontend consumers
- Scaffolder plugin actions (`skillmeat:attest`, `skillmeat:bom-generate`) integrated
- Backend tests verify payload shape and scaffolder action behavior

### Phase 11 Exit Criteria
- Unit test coverage for all repositories, services, routers >= 80%
- Integration tests for BOM generation, signing, history, attestation pass
- Migration tests verify schema compatibility (SQLite → PostgreSQL upgrade path)
- API documentation complete with examples for all endpoints
- User guide published with BOM workflow diagrams
- CI/CD integration guide provided (GitHub Actions snippet)

---

## Key Files & Artifacts

### Models (Phase 1)
- `skillmeat/cache/models.py` — Add 6 new models (AttestationRecord, ArtifactHistoryEvent, etc.)
- `skillmeat/cache/migrations/` — Alembic migrations for new tables (both SQLite and PostgreSQL)

### Repositories (Phases 1-3)
- `skillmeat/core/interfaces/repositories.py` — Add `IBomRepository` ABC
- `skillmeat/core/repositories/local_bom.py` — Local BOM repository (SQLAlchemy 1.x)
- `skillmeat/cache/enterprise_repositories.py` — Enterprise BOM repository (SQLAlchemy 2.x)
- `skillmeat/core/interfaces/repositories.py` — Add artifact activity repository interface adjacent to existing history interfaces

### Core Services (Phases 2-6)
- `skillmeat/core/bom/generator.py` — BomGenerator class + artifact adapters
- `skillmeat/core/bom/history.py` — Artifact activity capture and provenance selection service
- `skillmeat/core/bom/signing.py` — Ed25519 signing/verification
- `skillmeat/core/bom/scope.py` — AttestationScopeResolver

### API Layer (Phases 7-10)
- `skillmeat/api/schemas/bom.py` — Pydantic schemas (BomSchema, AttestationSchema, etc.)
- `skillmeat/api/routers/bom.py` — BOM API endpoints (8 routes)
- `skillmeat/api/routers/artifact_activity.py` or equivalent — Activity-history API surface
- `skillmeat/api/routers/idp_integration.py` — Extended with `/integrations/idp/bom-card` endpoint

### CLI (Phase 8)
- `skillmeat/cli/__init__.py` — Register new command groups: `bom`, `history`, `attest`
- `skillmeat/cli/commands/` — New BOM/attestation command modules if the CLI split continues

### Web (Phase 9)
- `skillmeat/web/components/provenance/provenance-tab.tsx` — Artifact detail provenance tab
- `skillmeat/web/components/bom/bom-viewer.tsx` — context.lock viewer
- `skillmeat/web/components/bom/history-timeline.tsx` — Event timeline
- `skillmeat/web/hooks/useArtifactActivityHistory.ts` — Provenance/activity history hook
- `skillmeat/web/hooks/useBomSnapshot.ts` / `useAttestations.ts` — BOM and attestation data hooks

### Tests (Phase 11)
- `skillmeat/cache/tests/test_bom_models.py` — Model tests
- `skillmeat/core/tests/test_bom_generator.py` — Generator tests
- `skillmeat/api/tests/test_bom_endpoints.py` — API endpoint tests
- `skillmeat/web/__tests__/provenance-tab.test.tsx` — React component tests

---

## Success Metrics

### Deliverable Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Artifact types in BOM schema | 13+ | Schema validation test |
| History event capture latency | < 50ms p95 | OpenTelemetry span timing |
| BOM generation time (50 artifacts) | < 2s | CLI benchmark |
| API response for history query (100 events) | < 200ms p95 | Load test |
| Backstage card load time | < 500ms | E2E test |
| API endpoint code coverage | >= 80% | pytest coverage report |
| Repository tests (local + enterprise) | 100% pass | pytest run on both editions |

### User Stories Completed
- Security engineer can audit AI-authored commits with cryptographic provenance (FR-01–FR-07)
- Team admin views team-scoped attestation records (FR-05–FR-06)
- Developer uses time-travel restore for debugging (FR-08)
- Backstage user receives BOM payload and scaffolder actions through the existing IDP backend integration (FR-12)

---

## Timeline & Dependencies

```
Week 1-2: Phase 1 (Models)
  └─→ Phase 2 (BOM Generator) Weeks 2-3
      ├─→ Phase 3 (History) Weeks 4-5 [parallel with Phase 4]
      └─→ Phase 4 (RBAC) Weeks 4-5
          ├─→ Phase 5-6 (Git+Crypto) Weeks 6-8 [parallel]
          └─→ Phase 7 (API) Weeks 9-10 [gate for Phases 9-10]
              ├─→ Phase 8 (CLI) Weeks 10-11 [parallel with Phase 9]
              ├─→ Phase 9 (Web) Weeks 11-12 [parallel with Phase 10]
              └─→ Phase 10 (Backstage) Weeks 12-13
                  └─→ Phase 11 (Testing+Docs) Weeks 14-16
```

**Critical Path**: Phase 1 → 2 → 3 → 7 → 9 (12 weeks minimum)
**With Parallelization**: 12-16 weeks depending on team size

---

## Architecture Decisions

### 1. Repository Pattern
All BOM data access goes through `IBomRepository` ABC with local/enterprise implementations. This decouples the API from database details and enables future multi-backend support.

**Reference**: `.claude/context/key-context/repository-architecture.md`

### 2. Artifact Activity History
Artifact activity history is a separate audit/provenance stream from the existing version-lineage history. Events are recorded asynchronously where possible, but emitted explicitly from service/repository boundaries so filesystem-first flows are not missed.

**Rationale**: Version lineage and provenance/audit history solve different problems and should not be conflated in either storage or UI.

### 3. Owner-Scoped Queries
All attestation/activity queries are filtered by resolved `user|team|enterprise` ownership — team members cannot see other teams' records, and enterprise-owned records follow tenant admin policy.

**Reference**: `.claude/context/key-context/auth-architecture.md`

### 4. Edition-Based Schema
`AttestationPolicy` model is enterprise-only (PostgreSQL + SQLAlchemy 2.x). `OwnerType.enterprise` is part of this feature track and must be represented consistently in local and enterprise code paths.

**Rationale**: Keeps local edition lightweight; enterprise can layer compliance on top.

### 5. Content Hash for Versioning
BOM snapshots use SHA-256 content hashes (from existing drift detection) as the versioning primitive — no sequential version numbers.

**Rationale**: Aligns with Git's commit-hash model; enables cryptographic trust.

---

## Known Constraints & Assumptions

### Constraints
1. **Ed25519 Signing**: Uses existing `skillmeat/security/crypto.py` — no new crypto primitives introduced.
2. **Backstage Auth**: Plugin uses Enterprise PAT (`verify_enterprise_pat`) — consistent with existing scaffold endpoint.
3. **Memory Items**: Already modeled in `MemoryItem` ORM — no schema changes needed, just adapter.
4. **Deployment Sets**: Already modeled per `20260224_1000_add_deployment_set_tables.py` migration.

### Assumptions
1. Cache DB (SQLite local, PostgreSQL enterprise) is always available during BOM generation.
2. Deployment tracking via `DeploymentTracker` provides complete list of active artifacts.
3. Content hashing utilities from drift detection (`content_hash`) are available and stable.
4. Pre-commit hooks work in all development environments (Linux, macOS, Windows Git Bash).

---

## Next Steps

1. **Review & Approve**: Stakeholders review this plan and phase breakdown.
2. **Phase 1 Kickoff**: Schedule data-layer-expert to begin `cache/models.py` updates.
3. **Create Progress Tracking**: Use `.claude/skills/artifact-tracking/` to create phase-by-phase progress YAML.
4. **Set Up CI/CD**: Add migration tests (SQLite + PostgreSQL) to pre-commit hooks and GitHub Actions.
5. **Begin Phase 1**: Models must lock before any service work proceeds.

---

## Related Documents

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md`
- **Architecture Guide**: `.claude/context/key-context/repository-architecture.md`
- **Auth Reference**: `.claude/context/key-context/auth-architecture.md`
- **Data Flow**: `.claude/context/key-context/data-flow-patterns.md`
- **Signing Policy**: `/docs/ops/security/SIGNING_POLICY.md`
- **Version Tracking ADR**: `/docs/dev/architecture/decisions/004-artifact-version-tracking.md`
