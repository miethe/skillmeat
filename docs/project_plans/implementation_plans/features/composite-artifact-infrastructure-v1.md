---
title: "Implementation Plan: Composite Artifact Infrastructure"
description: "Phased implementation plan for relational model enabling many-to-many artifact relationships, graph-aware discovery, smart import with deduplication, and web UI relationship browsing."
audience: [ai-agents, developers]
tags: [implementation, planning, phases, composite-artifacts, database, api, frontend]
created: 2026-02-17
updated: 2026-02-17
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md
  - /docs/project_plans/design-specs/composite-artifact-infrastructure.md
---

# Implementation Plan: Composite Artifact Infrastructure

**Plan ID**: `CAI-IMPL-2026-02-17`
**Date**: 2026-02-17
**Author**: Claude (Haiku 4.5) — Implementation Planner
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md`
- **Design Spec**: `/docs/project_plans/design-specs/composite-artifact-infrastructure.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 35 story points across 4 phases
**Target Timeline**: 12-14 days (3-4 weeks at 1 FTE backend + 1 FTE frontend)

---

## Executive Summary

This implementation plan outlines the phased rollout of the Composite Artifact Infrastructure feature. We will introduce a relational model (`ArtifactAssociation` table) that enables Plugins to own many-to-many relationships with atomic artifacts (Skills, Commands, Agents, etc.), each of which can be independently versioned and reused across multiple Plugins.

**Key outcomes**:
1. **Phase 1** establishes database schema, ORM models, and repository layer for artifact associations.
2. **Phase 2** implements graph-aware discovery that detects composite roots and builds in-memory dependency graphs.
3. **Phase 3** orchestrates smart transactional import with SHA-256 deduplication and version pinning.
4. **Phase 4** exposes relationships in the web UI with "Contains" tabs, "Part of" sections, and import preview dialogs.

**Success is measured by**: Zero duplicate artifacts on re-import, transactional atomicity, <5% false positive rate in composite detection, and complete UI relationship browsing within 2 clicks.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Database Layer** (Phase 1) — `artifact_associations` table with composite PK, FKs, relationship metadata, version pinning
2. **Repository Layer** (Phase 1) — CRUD operations on associations, parent/child lookups, transaction handling
3. **Service Layer** (Phase 2-3) — Composite detection logic, deduplication, import orchestration
4. **API Layer** (Phase 3-4) — `GET /artifacts/{id}/associations` endpoint returning `AssociationsDTO`
5. **UI Layer** (Phase 4) — Artifact detail tabs, import preview modal, relationship rendering
6. **Testing Layer** (All phases) — Unit, integration, E2E coverage >80%
7. **Documentation Layer** (All phases) — API docs, component docs, architecture notes
8. **Deployment Layer** (Phase 4) — Feature flag, observability, monitoring

### Parallel Work Opportunities

- **Phase 1 & 2**: While backend implements migration, frontend can design UI components (non-blocking).
- **Phase 3 & 4**: Frontend integration with API can begin before import orchestration finishes if endpoint contract is stable.
- **Testing**: Unit tests for each phase can run in parallel with next phase's implementation.

### Critical Path

1. **Enum update** (FR-1) → blocks all downstream work
2. **ORM model + migration** (FR-2 to FR-4) → required before repository and service layers
3. **Repository methods** (Phase 1) → required before discovery and import
4. **Composite detection** (Phase 2) → required before import orchestration can be tested
5. **Import transaction wrapper** (Phase 3) → required before API endpoint is useful
6. **API endpoint** (Phase 3) → required before frontend can fetch associations
7. **UI implementation** (Phase 4) → depends on stable API contract

---

## Phase Breakdown

### Phase 1: Core Relationships (Backend)

**Duration**: 3-4 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

**Overview**: Establish database schema and ORM layer for artifact associations. This is the foundation for all downstream phases.

See detailed phase breakdown: [Phase 1: Core Relationships](./composite-artifact-infrastructure-v1/phase-1-core-relationships.md)

**Key Deliverables**:
- `PLUGIN` added to `ArtifactType` enum with exhaustive call-site audit
- `ArtifactAssociation` ORM model with composite PK, FKs, `relationship_type`, `pinned_version_hash`
- Bidirectional `parent_associations` / `child_associations` relationships on `Artifact`
- Alembic migration with reversible down() migration
- Repository methods: `get_associations()`, `create_association()`, `delete_association()`
- Unit tests for model validation and repository CRUD

**Phase 1 Quality Gates**:
- [x] Enum change does not break existing type-checking (run type-check full suite)
- [x] Alembic migration applies cleanly to fresh DB
- [x] Alembic migration rolls back cleanly
- [x] FK constraints enforced by database
- [x] Repository CRUD methods pass unit tests (>80% coverage)
- [x] No regression in existing artifact queries/imports

---

### Phase 2: Enhanced Discovery (Core)

**Duration**: 2-3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

**Overview**: Update discovery layer to detect composite roots, recursively enumerate children, and return `DiscoveredGraph` structure instead of flat list.

See detailed phase breakdown: [Phase 2: Enhanced Discovery](./composite-artifact-infrastructure-v1/phase-2-enhanced-discovery.md)

**Key Deliverables**:
- `DiscoveredGraph` dataclass (parent artifact + list of children + linkage metadata)
- `detect_composites(root_path)` function with signature detection (plugin.json OR 2+ artifact-type subdirectories)
- Updated `discover_artifacts()` to return `DiscoveredGraph` for composites, flat `DiscoveryResult` for atomic
- False positive guard: require at least 2 distinct artifact-type children to qualify as composite
- Unit tests with fixture repos covering true positives and false positive validation
- Feature flag: `composite_artifacts_enabled` gates new discovery path

**Phase 2 Quality Gates**:
- [x] Composite detection returns `DiscoveredGraph` with correct parent/children linkage
- [x] False positive rate <5% on fixture repo set (40+ repos)
- [x] Existing flat discovery tests pass (no regression)
- [x] Feature flag properly gates new behavior
- [x] Discovery scan time adds <500ms overhead

---

### Phase 3: Import Orchestration & Deduplication (Core)

**Duration**: 3-4 days
**Dependencies**: Phase 1 complete, Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

**Overview**: Implement transactional smart import orchestration with SHA-256 deduplication, version pinning, and atomic rollback on failure.

See detailed phase breakdown: [Phase 3: Import Orchestration](./composite-artifact-infrastructure-v1/phase-3-import-orchestration.md)

**Key Deliverables**:
- SHA-256 content hash computation for skills (directory tree hash) and single-file artifacts
- Dedup logic: hash lookup → link existing / new version / create new
- Transaction wrapper for plugin import: all children + parent + associations in single DB transaction
- Rollback on any child failure: no partial imports
- Record `pinned_version_hash` in `ArtifactAssociation` at import time
- Sync engine update: `_get_artifact_type_plural()` extension for `PLUGIN` type
- Plugin meta-file storage: `~/.skillmeat/collection/plugins/<name>/`
- Integration tests: happy path, dedup scenarios, rollback validation
- `GET /artifacts/{id}/associations` API endpoint with `AssociationsDTO` response

**Phase 3 Quality Gates**:
- [x] Plugin import happy path: all children + parent + associations created in single transaction
- [x] Dedup scenario: re-importing same plugin creates 0 new artifact rows for exact matches
- [x] Rollback scenario: simulated mid-import failure leaves collection in pre-import state
- [x] Pinned hash recorded correctly and readable via association repo
- [x] Sync engine handles `PLUGIN` type correctly
- [x] API endpoint returns 200 with `AssociationsDTO` for known artifact, 404 for unknown

---

### Phase 4: Web UI Relationship Browsing (Frontend + API Integration)

**Duration**: 3-4 days
**Dependencies**: Phase 3 complete (API endpoint stable)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, python-backend-engineer (API endpoints)

**Overview**: Surface parent/child relationships in artifact detail page and implement import preview modal showing composite breakdown.

See detailed phase breakdown: [Phase 4: Web UI Implementation](./composite-artifact-infrastructure-v1/phase-4-web-ui.md)

**Key Deliverables**:
- `AssociationsDTO` TypeScript type (auto-sync from OpenAPI spec)
- `useArtifactAssociations(artifactId)` React hook calling `GET /artifacts/{id}/associations`
- Artifact detail page: "Contains" tab listing child artifacts (conditional on composite type)
- Artifact detail page: "Part of" sidebar section listing parent plugins (conditional on `parents.length > 0`)
- Import modal: composite detection preview ("1 Plugin + N children: X new, Y existing")
- Version conflict resolution dialog (warn on pinned hash mismatch during deploy)
- WCAG 2.1 AA keyboard navigation and screen-reader support
- Playwright E2E tests: import flow, "Contains" tab rendering, "Part of" section rendering

**Phase 4 Quality Gates**:
- [x] "Contains" tab renders for plugins, lists correct children
- [x] "Part of" section renders for atomic artifacts with parents
- [x] Import preview modal shows correct composite breakdown
- [x] User can navigate parent↔child relationships within 2 clicks
- [x] Keyboard navigation works (Tab, Enter, Esc)
- [x] Screen readers announce tab/section content correctly
- [x] E2E tests pass for all relationship browsing scenarios

---

## Task Breakdown (Consolidated View)

### Phase 1: Core Relationships

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P1-01 | Add PLUGIN enum | Add `PLUGIN` to `ArtifactType` enum; audit all call sites for exhaustiveness | Enum added; all tests pass; no type-checking errors in IDE/CI | 1 pt | data-layer-expert | None |
| CAI-P1-02 | ArtifactAssociation model | Define `ArtifactAssociation` ORM with composite PK, FKs, `relationship_type`, `pinned_version_hash` | Model validates; relationships defined; follows `GroupArtifact` pattern | 2 pts | data-layer-expert | CAI-P1-01 |
| CAI-P1-03 | Artifact relationships | Add `parent_associations` and `child_associations` to `Artifact` ORM | Backrefs work; can traverse parent→child and child→parent | 1 pt | data-layer-expert | CAI-P1-02 |
| CAI-P1-04 | Alembic migration | Generate and apply migration for `artifact_associations` table | Migration applies cleanly; rolls back cleanly; no schema errors | 2 pts | data-layer-expert | CAI-P1-03 |
| CAI-P1-05 | Association repository | Implement `get_associations()`, `create_association()`, delete methods | CRUD methods pass unit tests; pagination handled correctly | 2 pts | python-backend-engineer | CAI-P1-04 |
| CAI-P1-06 | Repository tests | Unit tests for association repository CRUD and queries | >80% code coverage; all scenarios tested | 1 pt | python-backend-engineer | CAI-P1-05 |
| CAI-P1-07 | Integration tests (Phase 1) | Integration tests for model + repository layer | Tests create/read/delete associations; FK constraints enforced | 1 pt | python-backend-engineer | CAI-P1-06 |

**Phase 1 Total**: 10 story points

---

### Phase 2: Enhanced Discovery

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P2-01 | DiscoveredGraph dataclass | Define `DiscoveredGraph` with parent + children + linkage metadata | Dataclass serializable; integrates with existing DiscoveryResult | 1 pt | python-backend-engineer | CAI-P1-07 |
| CAI-P2-02 | detect_composites() | Implement composite root detection (plugin.json OR 2+ artifact-type subdirs) | Returns correct parent/children for test repos; <5% false positive rate | 2 pts | backend-architect | CAI-P2-01 |
| CAI-P2-03 | Discovery integration | Update `discover_artifacts()` to return `DiscoveredGraph` for composites | Flat discovery unaffected; graph path returns correct structure | 2 pts | python-backend-engineer | CAI-P2-02 |
| CAI-P2-04 | Discovery tests | Unit tests with 40+ fixture repos covering true positives and false positives | <5% false positive rate; >90% true positive rate on fixtures | 2 pts | backend-architect | CAI-P2-03 |
| CAI-P2-05 | Feature flag integration | Implement `composite_artifacts_enabled` feature flag gating discovery | Flag properly gates new detection path; can be toggled safely | 1 pt | python-backend-engineer | CAI-P2-04 |

**Phase 2 Total**: 8 story points

---

### Phase 3: Import Orchestration & Deduplication

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P3-01 | Content hash computation | Implement SHA-256 hashing for skills (tree hash) and single-file artifacts | Hashing consistent; same content → same hash; different content → different hash | 1 pt | python-backend-engineer | CAI-P2-05 |
| CAI-P3-02 | Dedup logic | Implement hash lookup + decision logic (link/new-version/create) | All 3 scenarios handled; unit tests pass | 2 pts | backend-architect | CAI-P3-01 |
| CAI-P3-03 | Transaction wrapper | Wrap plugin import (children + parent + associations) in single DB transaction | All-or-nothing semantics; rollback on any child failure | 2 pts | python-backend-engineer | CAI-P3-02 |
| CAI-P3-04 | Version pinning | Record `pinned_version_hash` in `ArtifactAssociation` at import time | Hash stored; retrievable via association repo | 1 pt | python-backend-engineer | CAI-P3-03 |
| CAI-P3-05 | Sync engine update | Extend `_get_artifact_type_plural()` in sync.py for `PLUGIN` type | Sync handles plugins correctly | 1 pt | backend-architect | CAI-P3-04 |
| CAI-P3-06 | Plugin storage | Implement `plugins/` directory structure in collection | Meta-files stored at `~/.skillmeat/collection/plugins/<name>/` | 1 pt | python-backend-engineer | CAI-P3-05 |
| CAI-P3-07 | Associations API endpoint | Implement `GET /artifacts/{id}/associations` returning `AssociationsDTO` | Endpoint returns 200 with DTO for valid ID, 404 for unknown | 2 pts | python-backend-engineer | CAI-P3-06 |
| CAI-P3-08 | Import integration tests | Integration tests for happy path, dedup scenarios, rollback validation | All scenarios pass; dedup verified; rollback works | 2 pts | python-backend-engineer | CAI-P3-07 |
| CAI-P3-09 | Observability | Add OpenTelemetry spans + structured logs for composite detection, hash check, import transaction | Spans/logs visible in tracing tools; metrics recorded | 1 pt | backend-architect | CAI-P3-08 |

**Phase 3 Total**: 13 story points

---

### Phase 4: Web UI Implementation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P4-01 | AssociationsDTO TypeScript type | Generate/sync TypeScript type from OpenAPI schema | Type matches backend `AssociationsDTO`; imports correctly | 1 pt | frontend-developer | CAI-P3-07 |
| CAI-P4-02 | useArtifactAssociations hook | Create React hook calling `GET /artifacts/{id}/associations` | Hook handles loading/error/success states; caches results | 2 pts | frontend-developer | CAI-P4-01 |
| CAI-P4-03 | Contains tab UI | Add "Contains" tab to artifact detail showing children (conditional on composite type) | Tab visible only for plugins; lists children with types/versions | 2 pts | ui-engineer-enhanced | CAI-P4-02 |
| CAI-P4-04 | Part of section UI | Add "Part of" section to detail page showing parent plugins | Section visible for artifacts with parents; links to parent detail | 2 pts | ui-engineer-enhanced | CAI-P4-02 |
| CAI-P4-05 | Import preview modal | Update import modal to show composite breakdown preview | Modal shows "X children: Y new, Z existing" before confirm | 2 pts | ui-engineer-enhanced | CAI-P4-02 |
| CAI-P4-06 | Conflict resolution dialog | Implement version conflict warning (pinned vs current hash) | Dialog shows side-by-side comparison; offers overwrite/side-by-side options | 2 pts | frontend-developer | CAI-P4-05 |
| CAI-P4-07 | Accessibility (a11y) | Implement keyboard navigation and screen-reader support | Tab/Enter/Esc work; ARIA labels present; WCAG 2.1 AA compliance | 1 pt | ui-engineer-enhanced | CAI-P4-06 |
| CAI-P4-08 | E2E tests (Playwright) | Create end-to-end tests for import flow, "Contains" tab, "Part of" section | All critical paths tested; tests pass in CI | 2 pts | ui-engineer-enhanced | CAI-P4-07 |

**Phase 4 Total**: 14 story points

---

## Overall Summary

| Phase | Title | Duration | Effort | Key Deliverables |
|-------|-------|----------|--------|------------------|
| 1 | Core Relationships (Backend) | 3-4 days | 10 pts | ORM model, migration, repository layer |
| 2 | Enhanced Discovery (Core) | 2-3 days | 8 pts | Graph-aware detection, DiscoveredGraph structure |
| 3 | Import Orchestration (Core) | 3-4 days | 13 pts | Transactional smart import, dedup logic, API endpoint |
| 4 | Web UI Implementation (Frontend) | 3-4 days | 14 pts | Relationship tabs, import preview, E2E tests |
| **Total** | **Composite Artifact Infrastructure** | **12-14 days** | **35 pts** | **Full relational model + UI relationship browsing** |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Alembic migration breaks existing artifact rows or FK constraints | High | Low | Write reversible migration with down(); test on copy of production schema before deploy; Phase 1 quality gate requires clean rollback validation |
| Discovery false positives (flat repos mis-detected as composites) | Medium | Medium | Require threshold of 2+ distinct artifact-type subdirectories; use `plugin.json` as authoritative signal; unit test against 40+ fixture repos; Phase 2 acceptance criteria enforce <5% false positive rate |
| Performance regression from graph traversal on large repos | Medium | Low | Limit composite detection to first 3 directory levels; add scan time telemetry; gate behind feature flag; Phase 2 quality gate requires <500ms overhead |
| Dedup hash collision (two different artifacts with same SHA-256) | Low | Very Low | SHA-256 collision probability negligible (~2^-128); document assumption; add name+hash pair check as secondary guard in Phase 3 |
| Version conflict resolution UX is confusing | Medium | Medium | Design conflict dialog (Phase 4) with clear side-by-side vs overwrite options; add escape hatch to skip plugin deploy; user testing on conflict scenarios |
| `ArtifactType` enum change breaks existing callers | High | Medium | Audit all call sites in Phase 1-01; ensure all `match`/`if-elif` chains are exhaustive; PR review enforces this; type-checking catches missed cases |
| Partial import leaves orphaned child artifacts | High | Low | Wrap plugin import in single DB transaction (Phase 3-03); use existing temp-dir + atomic move pattern; Phase 3 quality gate tests rollback scenario |
| Import modal doesn't load discovery graph before user confirms | Medium | Low | Ensure discovery completes and returns `DiscoveredGraph` before UI shows import button; Phase 4 E2E test validates this flow |

---

## Key Files & Implementation References

### Database & ORM
- `skillmeat/cache/models.py` — Add `ArtifactAssociation` model, update `Artifact` relationships
- `skillmeat/cache/migrations/versions/` — Alembic migration for `artifact_associations` table
- `skillmeat/cache/repositories/` — Association CRUD repository methods
- `skillmeat/core/enums.py` — Add `PLUGIN` to `ArtifactType` enum

### Discovery & Import
- `skillmeat/core/artifact_detection.py` — Update `ArtifactType`, add composite detection signatures
- `skillmeat/core/discovery.py` — Implement `DiscoveredGraph`, update `discover_artifacts()`
- `skillmeat/core/importer.py` — Add hash-based dedup, transaction wrapper, version pinning
- `skillmeat/core/sync.py` — Extend `_get_artifact_type_plural()` for `PLUGIN` type

### API & Frontend
- `skillmeat/api/routers/artifacts.py` — Add `GET /artifacts/{id}/associations` endpoint
- `skillmeat/api/schemas/` — Add `AssociationsDTO` schema
- `skillmeat/api/openapi.json` — Regenerate after new endpoint
- `skillmeat/web/app/artifacts/[id]/page.tsx` — Add "Contains" and "Part of" sections
- `skillmeat/web/hooks/useArtifactAssociations.ts` — React hook for fetching associations
- `skillmeat/web/components/import-modal.tsx` — Update import preview UI

### Testing
- `tests/test_artifact_associations.py` — Unit tests for ORM model and repository
- `tests/test_composite_detection.py` — Discovery unit tests with fixture repos
- `tests/test_import_orchestration.py` — Integration tests for smart import
- `skillmeat/web/__tests__/artifact-detail.test.tsx` — Component tests for relationship tabs
- `skillmeat/web/__tests__/e2e/import-flow.spec.ts` — E2E tests for import preview and tabs

---

## Success Metrics

### Functional Success
- [x] Plugin import end-to-end: source URL → detection → preview → confirm → DB rows + filesystem
- [x] Deduplication verified: re-importing same plugin creates 0 new artifact rows for exact matches
- [x] Transactional rollback verified: simulated mid-import failure leaves collection clean
- [x] UI relationship discovery: users can navigate parent↔child within 2 clicks

### Technical Success
- [x] Alembic migration applies & rolls back cleanly
- [x] API returns `AssociationsDTO` with correct parent/child lists
- [x] Code coverage >80% for all new code
- [x] False positive rate <5% in composite detection
- [x] Observability: OTel spans logged for all key operations

### Quality Success
- [x] Zero P0/P1 regressions in existing artifact import tests
- [x] WCAG 2.1 AA compliance for UI relationship tabs
- [x] Feature flag properly gates new behavior
- [x] All acceptance criteria from PRD met

---

## Progress Tracking

See detailed progress tracking: `.claude/progress/composite-artifact-infrastructure/all-phases-progress.md`

This file will be created and updated as work progresses through each phase using the artifact-tracking CLI scripts.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-17
**Status**: Draft (awaiting approval)
