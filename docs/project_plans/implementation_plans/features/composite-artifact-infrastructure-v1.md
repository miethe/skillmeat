---
title: 'Implementation Plan: Composite Artifact Infrastructure'
description: Phased implementation plan for relational model enabling many-to-many
  artifact relationships, graph-aware discovery, smart import with deduplication,
  and web UI relationship browsing.
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- composite-artifacts
- database
- api
- frontend
created: 2026-02-17
updated: '2026-02-18'
category: product-planning
status: in-progress
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
- **ADR-007**: `/docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 64 story points across 5 phases
**Target Timeline**: 18-23 days (4-5 weeks at 1 FTE backend + 1 FTE frontend)

---

## Executive Summary

This implementation plan outlines the phased rollout of the Composite Artifact Infrastructure feature. We will introduce a `COMPOSITE` value in the `ArtifactType` enum alongside a `CompositeType` enum (with `PLUGIN` as the first composite type), UUID-backed FK membership via ADR-007, and deployable composite entities that reference atomic artifacts (Skills, Commands, Agents, etc.) without mutating those artifact records.

**Key outcomes**:
1. **Phase 1** establishes the `COMPOSITE` artifact type, `CompositeType` enum, UUID identity column (per ADR-007), database schema, ORM models, and repository layer for composite membership metadata with UUID FK-backed child references.
2. **Phase 2** implements graph-aware discovery that detects composite roots and builds in-memory dependency graphs using `DiscoveredGraph` Pydantic BaseModel.
3. **Phase 3** orchestrates smart transactional import with deduplication (reusing existing `content_hash` fields), version pinning, and atomic rollback on failure.
4. **Phase 4** exposes relationships in the web UI with "Contains" tabs, "Part of" sections, import preview dialogs (3 buckets: New, Existing, Conflict), and CLI composite listing.

**Success is measured by**: Zero duplicate artifacts on re-import, transactional atomicity, <5% false positive rate in composite detection, and complete UI relationship browsing within 2 clicks.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Database Layer** (Phase 1) — composite entity + membership metadata tables with scoped keys, relationship metadata, version pinning; UUID identity column per ADR-007
2. **Repository Layer** (Phase 1) — CRUD operations on memberships, parent/child lookups via UUID FK-backed membership, transaction handling
3. **Service Layer** (Phase 2-3) — Composite detection logic, deduplication, import orchestration; `CompositeType` enum drives type-specific behavior
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

0. **UUID column migration** (ADR-007) → adds UUID identity column to `CachedArtifact`; blocks composite membership FK
1. **Enum update** (FR-1) → `COMPOSITE` in `ArtifactType` + `CompositeType` enum; blocks all downstream work
2. **ORM model + migration** (FR-2 to FR-4) → requires UUID column; required before repository and service layers
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

**Overview**: Establish database schema and ORM layer for composite entities and membership metadata. This is the foundation for all downstream phases. Includes adding the UUID identity column to `CachedArtifact` per ADR-007.

See detailed phase breakdown: [Phase 1: Core Relationships](./composite-artifact-infrastructure-v1/phase-1-core-relationships.md)

**Key Deliverables**:
- `COMPOSITE` added to `ArtifactType` enum (not PLUGIN); `CompositeType` enum with `PLUGIN` value for composite subtyping
- UUID identity column added to `CachedArtifact` per ADR-007
- `CompositeArtifact` + membership metadata ORM models with scoped keys, `composite_type` (from `CompositeType` enum), `relationship_type`, `pinned_version_hash`; `CompositeMembership.child_artifact_uuid` FK references `CachedArtifact.uuid`
- Atomic artifact schema remains unchanged; parent/child linkage represented via metadata rows
- Alembic migration with reversible down() migration
- Repository methods: `get_associations()`, `create_membership()`, `delete_membership()`
- Unit tests for model validation and repository CRUD

**Phase 1 Quality Gates**:
- [ ] Enum change does not break existing type-checking (run type-check full suite)
- [ ] UUID column migration applies cleanly per ADR-007
- [ ] Alembic migration applies cleanly to fresh DB
- [ ] Alembic migration rolls back cleanly
- [ ] FK constraints enforced by database (including UUID FK on membership)
- [ ] Repository CRUD methods pass unit tests (>80% coverage)
- [ ] No regression in existing artifact queries/imports

---

### Phase 2: Enhanced Discovery (Core)

**Duration**: 2-3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

**Overview**: Update discovery layer to detect composite roots, recursively enumerate children, and return `DiscoveredGraph` structure instead of flat list.

See detailed phase breakdown: [Phase 2: Enhanced Discovery](./composite-artifact-infrastructure-v1/phase-2-enhanced-discovery.md)

**Key Deliverables**:
- `DiscoveredGraph` Pydantic `BaseModel` (parent artifact + list of children + linkage metadata)
- `detect_composites(root_path)` function with signature detection (plugin.json OR 2+ artifact-type subdirectories)
- Updated `discover_artifacts()` class method to return `DiscoveredGraph` for composites, flat `DiscoveryResult` for atomic
- False positive guard: require at least 2 distinct artifact-type children to qualify as composite
- Unit tests with 10-15 fixture repos covering true positives and false positive validation
- Feature flag: `composite_artifacts_enabled` gates new discovery path

**Phase 2 Quality Gates**:
- [ ] Composite detection returns `DiscoveredGraph` with correct parent/children linkage
- [ ] False positive rate <5% on fixture repo set (10-15 repos)
- [ ] Existing flat discovery tests pass (no regression)
- [ ] Feature flag properly gates new behavior
- [ ] Discovery scan time adds <500ms overhead

---

### Phase 3: Import Orchestration & Deduplication (Core)

**Duration**: 3-4 days
**Dependencies**: Phase 1 complete, Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

**Overview**: Implement transactional smart import orchestration with deduplication (leveraging existing `Artifact.content_hash` and `ArtifactVersion.content_hash` fields), version pinning, and atomic rollback on failure.

See detailed phase breakdown: [Phase 3: Import Orchestration](./composite-artifact-infrastructure-v1/phase-3-import-orchestration.md)

**Key Deliverables**:
- Deduplication leveraging existing `Artifact.content_hash` and `ArtifactVersion.content_hash` fields (no new hash computation needed for artifacts that already have content hashes)
- Dedup logic: hash lookup → link existing / new version / create new
- Transaction wrapper for plugin import: all children + composite entity + memberships in single DB transaction
- Rollback on any child failure: no partial imports
- Record `pinned_version_hash` in membership metadata at import time
- Propagate composite membership metadata to project deployments (Claude Code in v1)
- Plugin meta-file storage: `~/.skillmeat/collections/{collection}/plugins/<name>/`
- Import preview with 3 buckets: "New" (create), "Existing" (link), "Conflict" (resolution needed)
- Enhanced import handling for same-name-different-hash artifacts deferred to future enhancement
- Integration tests: happy path, dedup scenarios, rollback validation
- `GET /artifacts/{id}/associations` API endpoint with `AssociationsDTO` response
- Bundle export: `skillmeat export` updated to export Composites as Bundles

**Phase 3 Quality Gates**:
- [ ] Plugin import happy path: all children + composite entity + memberships created in single transaction
- [ ] Dedup scenario: re-importing same plugin creates 0 new artifact rows for exact matches
- [ ] Rollback scenario: simulated mid-import failure leaves collection in pre-import state
- [ ] Pinned hash recorded correctly and readable via membership repo
- [ ] Project deployment propagation preserves composite membership context for Claude Code
- [ ] Non-Claude platforms return explicit unsupported response for plugin deployment
- [ ] API endpoint returns 200 with `AssociationsDTO` for known artifact, 404 for unknown
- [ ] Import preview correctly categorizes artifacts into New/Existing/Conflict buckets

---

### Phase 4: Web UI Relationship Browsing (Frontend + API Integration)

**Duration**: 3-4 days
**Dependencies**: Phase 3 complete (API endpoint stable)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, python-backend-engineer (API endpoints)

**Overview**: Surface parent/child relationships in artifact detail page and implement import preview modal showing composite breakdown. Conflict resolution dialog wired to real backend API (no stubs). Plugin deployment for Claude Code deploys child artifacts to standard locations and composite non-artifact files to `.claude/plugins/{plugin_name}/`. CLI listing updated so composites appear alongside artifacts, platform-profile-specific.

See detailed phase breakdown: [Phase 4: Web UI Implementation](./composite-artifact-infrastructure-v1/phase-4-web-ui.md)

**Key Deliverables**:
- `AssociationsDTO` TypeScript type (auto-sync from OpenAPI spec)
- `useArtifactAssociations(artifactId)` React hook calling `GET /artifacts/{id}/associations`
- Artifact detail page: "Contains" tab listing child artifacts (conditional on composite type), including a11y
- Artifact detail page: "Part of" sidebar section listing parent plugins (conditional on `parents.length > 0`), including a11y
- Import modal: composite detection preview ("1 Plugin + N children: X new, Y existing, Z conflicts"), including a11y
- Version conflict resolution dialog wired to real backend API, no stubs (warn on pinned hash mismatch during deploy), including a11y
- WCAG 2.1 AA keyboard navigation and screen-reader support (folded into component tasks)
- Core import flow E2E test (Playwright); skip non-critical E2E scenarios
- CLI composite listing: composites appear alongside artifacts, platform-profile-specific
- Plugin deployment layout for Claude Code: child artifacts to standard locations + composite non-artifact files to `.claude/plugins/{plugin_name}/`

**Phase 4 Quality Gates**:
- [ ] "Contains" tab renders for plugins, lists correct children
- [ ] "Part of" section renders for atomic artifacts with parents
- [ ] Import preview modal shows correct composite breakdown (3 buckets)
- [ ] User can navigate parent↔child relationships within 2 clicks
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] Screen readers announce tab/section content correctly
- [ ] Core import flow E2E test passes
- [ ] CLI lists composites alongside artifacts

---

### Phase 5: UUID Migration for Existing Join Tables (Backend)

**Duration**: 4-5 days
**Dependencies**: Phase 4 complete
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

**Overview**: Migrate existing join tables (`collection_artifacts`, `group_artifacts`, `artifact_tags`) from `type:name` string references to UUID FK references per ADR-007 Phase 2. This is cleanup that improves referential integrity across the entire data layer, enabled by the UUID column added in Phase 1.

See detailed phase breakdown: [Phase 5: UUID Migration](./composite-artifact-infrastructure-v1/phase-5-uuid-migration.md)

**Key Deliverables**:
- `collection_artifacts` migrated to `artifact_uuid` FK with cascading deletes
- `group_artifacts` migrated to `artifact_uuid` FK with cascading deletes
- `artifact_tags` migrated to `artifact_uuid` FK with cascading deletes
- All repository methods updated for UUID-based joins
- Assessment of `type:name` PK to unique index feasibility
- Comprehensive regression tests across all migrated tables
- Phase 1 compatibility layer retired

**Phase 5 Quality Gates**:
- [ ] All join tables use UUID FK with referential integrity enforced
- [ ] Cascading deletes work across all join tables
- [ ] All Alembic migrations apply and rollback cleanly
- [ ] No API surface changes — external consumers see same type:name identifiers
- [ ] No regression in collection management, tagging, or grouping features
- [ ] >80% test coverage on migrated repository methods

---

## Task Breakdown (Consolidated View)

### Phase 1: Core Relationships

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P1-01 | Add COMPOSITE enum + CompositeType | Add `COMPOSITE` to `ArtifactType` enum; add `CompositeType` enum with `PLUGIN` value; audit all call sites | Enums added; all tests pass; no type-checking errors | 1 pt | data-layer-expert | None |
| CAI-P1-02 | Add UUID column to CachedArtifact | Add `uuid` column (String, unique, non-null, indexed, default=uuid4().hex) per ADR-007 | UUID column present; auto-populated for new rows | 1 pt | data-layer-expert | None |
| CAI-P1-03 | UUID Alembic migration | Add nullable uuid, backfill existing rows, apply NOT NULL + unique index | Migration applies and rolls back cleanly; all rows have UUID | 2 pts | data-layer-expert | CAI-P1-02 |
| CAI-P1-04 | Composite ORM models | Define `CompositeArtifact` + `CompositeMembership` with UUID FK (`child_artifact_uuid` → `artifacts.uuid`, ondelete=CASCADE) | Models validate; UUID FK enforced; no atomic artifact schema mutation | 2 pts | data-layer-expert | CAI-P1-01, CAI-P1-03 |
| CAI-P1-05 | Composite tables Alembic migration | Create `composite_artifacts` and `composite_memberships` tables (separate from UUID migration) | Migration applies/rolls back cleanly; FK targets `artifacts.uuid` | 1 pt | data-layer-expert | CAI-P1-04 |
| CAI-P1-06 | Membership repository + service | Implement CRUD + service-layer `type:name` → UUID resolution (`composite_service.py`) | CRUD methods work; resolution handles not-found; pagination | 2 pts | python-backend-engineer | CAI-P1-05 |
| CAI-P1-07 | Filesystem manifest UUID writes | Write `CachedArtifact.uuid` into `.skillmeat-deployed.toml` and `manifest.toml` additively | UUID appears in manifests; backward-compatible (old readers unaffected) | 1 pt | python-backend-engineer | CAI-P1-03 |
| CAI-P1-08 | Unit tests | UUID generation, uniqueness, CompositeMembership CRUD, service-layer resolution (>80% coverage) | All tests pass; >80% coverage on new code | 2 pts | python-backend-engineer | CAI-P1-06 |
| CAI-P1-09 | Integration tests | FK constraints, cascading deletes, type:name → UUID resolution end-to-end, migration round-trip | All integration scenarios pass; FK constraints enforced | 2 pts | python-backend-engineer | CAI-P1-08 |

**Phase 1 Total**: 14 story points

---

### Phase 2: Enhanced Discovery

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P2-01 | DiscoveredGraph BaseModel | Define `DiscoveredGraph` as Pydantic `BaseModel` with parent + children + linkage metadata | BaseModel serializable; integrates with existing DiscoveryResult | 1 pt | python-backend-engineer | CAI-P1-07 |
| CAI-P2-02 | detect_composites() | Implement composite root detection (plugin.json OR 2+ artifact-type subdirs) | Returns correct parent/children for test repos; <5% false positive rate | 2 pts | backend-architect | CAI-P2-01 |
| CAI-P2-03 | Discovery integration | Update `discover_artifacts()` class method to return `DiscoveredGraph` for composites | Flat discovery unaffected; graph path returns correct structure | 2 pts | python-backend-engineer | CAI-P2-02 |
| CAI-P2-04 | Discovery tests | Unit tests with 10-15 fixture repos covering true positives and false positives | <5% false positive rate; >90% true positive rate on fixtures | 2 pts | backend-architect | CAI-P2-03 |
| CAI-P2-05 | Feature flag integration | Implement `composite_artifacts_enabled` feature flag gating discovery | Flag properly gates new detection path; can be toggled safely | 1 pt | python-backend-engineer | CAI-P2-04 |

**Phase 2 Total**: 8 story points

---

### Phase 3: Import Orchestration & Deduplication

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P3-01 | Content hash deduplication | Leverage existing `Artifact.content_hash` and `ArtifactVersion.content_hash` for dedup; extend hashing for skills (tree hash) where content hash not yet populated | Hashing consistent; same content → same hash; different content → different hash; reuses existing content_hash fields | 1 pt | python-backend-engineer | CAI-P2-05 |
| CAI-P3-02 | Dedup logic | Implement hash lookup + decision logic (link/new-version/create) | All 3 scenarios handled; unit tests pass | 2 pts | backend-architect | CAI-P3-01 |
| CAI-P3-03 | Transaction wrapper | Wrap plugin import (children + composite entity + memberships) in single DB transaction | All-or-nothing semantics; rollback on any child failure | 2 pts | python-backend-engineer | CAI-P3-02 |
| CAI-P3-04 | Version pinning | Record `pinned_version_hash` in membership metadata at import time | Hash stored; retrievable via membership repo | 1 pt | python-backend-engineer | CAI-P3-03 |
| CAI-P3-05 | Project propagation | Carry composite membership metadata into project deployment records (Claude Code in v1) | Deployed children retain parent composite context; unsupported platforms return clear message | 1 pt | backend-architect | CAI-P3-04 |
| CAI-P3-06 | Plugin storage | Implement `plugins/` directory structure in collection | Meta-files stored at `~/.skillmeat/collections/{collection}/plugins/<name>/` | 1 pt | python-backend-engineer | CAI-P3-05 |
| CAI-P3-07 | Associations API endpoint | Implement `GET /artifacts/{id}/associations` returning `AssociationsDTO` | Endpoint returns 200 with DTO for valid ID, 404 for unknown | 2 pts | python-backend-engineer | CAI-P3-06 |
| CAI-P3-08 | Import integration tests | Integration tests for happy path, dedup scenarios, rollback validation | All scenarios pass; dedup verified; rollback works | 2 pts | python-backend-engineer | CAI-P3-07 |
| CAI-P3-09 | Observability | Add OpenTelemetry spans + structured logs for composite detection, hash check, import transaction | Spans/logs visible in tracing tools; metrics recorded | 1 pt | backend-architect | CAI-P3-08 |
| CAI-P3-10 | Bundle export for composites | Update `skillmeat export` to export Composite as Bundle | Export produces valid bundle format; round-trip import/export verified | 1 pt | python-backend-engineer | CAI-P3-07 |

**Phase 3 Total**: 14 story points

---

### Phase 4: Web UI Implementation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P4-01 | AssociationsDTO TypeScript type | Generate/sync TypeScript type from OpenAPI schema | Type matches backend `AssociationsDTO`; imports correctly | 1 pt | frontend-developer | CAI-P3-07 |
| CAI-P4-02 | useArtifactAssociations hook | Create React hook calling `GET /artifacts/{id}/associations` | Hook handles loading/error/success states; caches results | 2 pts | frontend-developer | CAI-P4-01 |
| CAI-P4-03 | Contains tab UI | Add "Contains" tab to artifact detail showing children (conditional on composite type), including a11y (keyboard nav, ARIA labels, WCAG 2.1 AA) | Tab visible only for plugins; lists children with types/versions; keyboard/screen-reader accessible | 2 pts | ui-engineer-enhanced | CAI-P4-02 |
| CAI-P4-04 | Part of section UI | Add "Part of" section to detail page showing parent plugins, including a11y (keyboard nav, ARIA labels, WCAG 2.1 AA) | Section visible for artifacts with parents; links to parent detail; keyboard/screen-reader accessible | 2 pts | ui-engineer-enhanced | CAI-P4-02 |
| CAI-P4-05 | Import preview modal | Update import modal to show composite breakdown preview with 3 buckets (New, Existing, Conflict), including a11y (keyboard nav, ARIA labels, WCAG 2.1 AA) | Modal shows "X children: Y new, Z existing, W conflicts" before confirm; keyboard/screen-reader accessible | 2 pts | ui-engineer-enhanced | CAI-P4-02 |
| CAI-P4-06 | Conflict resolution dialog | Implement version conflict warning (pinned vs current hash) wired to real backend API, no stubs, including a11y (keyboard nav, ARIA labels, WCAG 2.1 AA) | Dialog shows side-by-side comparison; offers overwrite/side-by-side options; connected to backend; keyboard/screen-reader accessible | 2 pts | frontend-developer | CAI-P4-05 |
| CAI-P4-08 | Core import flow E2E test | Core import flow E2E test only (Playwright); skip non-critical E2E scenarios | Core import path tested; test passes in CI | 1 pt | ui-engineer-enhanced | CAI-P4-06 |
| CAI-P4-09 | CLI composite listing | Update CLI to list composites alongside artifacts, platform-profile-specific | `skillmeat list` shows composites; filtered by platform profile | 1 pt | python-backend-engineer | CAI-P3-07 |

**Phase 4 Total**: 13 story points

---

### Phase 5: UUID Migration for Existing Join Tables

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CAI-P5-01 | Migrate collection_artifacts | Add `artifact_uuid` FK column, migrate data, drop old `artifact_id` string column | FK enforced; cascading deletes work; migration reversible | 2 pts | data-layer-expert | CAI-P4-08 |
| CAI-P5-02 | Migrate group_artifacts | Same pattern as P5-01 for group_artifacts table | FK enforced; cascading deletes work; migration reversible | 2 pts | data-layer-expert | CAI-P5-01 |
| CAI-P5-03 | Migrate artifact_tags | Same pattern for artifact_tags table (PK change: artifact_id → artifact_uuid) | FK enforced; cascading deletes work; migration reversible | 2 pts | data-layer-expert | CAI-P5-02 |
| CAI-P5-04 | Update repository queries | Update all repository methods to use UUID-based joins | All queries work with UUID FKs; no API surface changes | 3 pts | python-backend-engineer | CAI-P5-03 |
| CAI-P5-05 | Update service/API layer | Verify all endpoints handle UUID-based join table queries | All endpoints return correct data; external API unchanged | 2 pts | python-backend-engineer | CAI-P5-04 |
| CAI-P5-06 | Assess PK change feasibility | Evaluate making `type:name` a unique index instead of PK; document decision | Decision documented; implemented if feasible, deferred if risky | 3 pts | data-layer-expert | CAI-P5-05 |
| CAI-P5-07 | Regression tests | Comprehensive tests across all migrated tables | >80% coverage; no regressions in collection/tag/group features | 2 pts | python-backend-engineer | CAI-P5-05 |
| CAI-P5-08 | Retire compatibility layer | Remove any dual-path code from Phase 1 | Clean codebase; no stale compatibility shims | 1 pt | python-backend-engineer | CAI-P5-06, CAI-P5-07 |

**Phase 5 Total**: 15 story points

---

## Story ID Cross-Reference

Mapping from PRD story IDs to implementation task IDs:

| PRD Story | Implementation Tasks |
|-----------|---------------------|
| CAI-001 | CAI-P1-01 |
| CAI-002 | CAI-P1-02, CAI-P1-03, CAI-P1-04 |
| CAI-003 | CAI-P1-05 |
| CAI-004 | CAI-P2-01, CAI-P2-02 |
| CAI-005 | CAI-P2-03 |
| CAI-006 | CAI-P3-01, CAI-P3-02 |
| CAI-007 | CAI-P3-03 |
| CAI-008 | CAI-P3-04 |
| CAI-009 | CAI-P3-07 |
| CAI-010 | CAI-P4-03 |
| CAI-011 | CAI-P4-04 |
| CAI-012 | CAI-P4-05 |
| CAI-013 | CAI-P4-06 |
| CAI-014 | CAI-P3-09 |
| CAI-015 | CAI-P2-05 |

---

## Overall Summary

| Phase | Title | Duration | Effort | Key Deliverables |
|-------|-------|----------|--------|------------------|
| 1 | Core Relationships (Backend) | 3-4 days | 14 pts | COMPOSITE enum, CompositeType, UUID column (ADR-007), ORM models, migrations, repository layer |
| 2 | Enhanced Discovery (Core) | 2-3 days | 8 pts | Graph-aware detection, DiscoveredGraph BaseModel |
| 3 | Import Orchestration (Core) | 3-4 days | 14 pts | Transactional smart import, dedup logic, API endpoint, bundle export |
| 4 | Web UI Implementation (Frontend) | 3-4 days | 13 pts | Relationship tabs, import preview (3 buckets), conflict dialog (real backend), CLI listing, core E2E test |
| 5 | UUID Migration (Backend) | 4-5 days | 15 pts | Migrate existing join tables to UUID FK, retire compatibility layer (ADR-007 Phase 2) |
| **Total** | **Composite Artifact Infrastructure** | **18-23 days** | **64 pts** (Phases 1-4: **49 pts**) | **Full relational model + UI + UUID migration** |

---

## Deferred Items

The following items are explicitly deferred to future enhancements:

- **Enhanced version conflict handling during import**: Same-name-different-hash resolution logic (currently defaults to `CREATE_NEW_VERSION`; enhanced UI for conflict resolution deferred)
- **Cross-platform plugin deployment**: Deployment support beyond Claude Code (other platforms return explicit unsupported response in v1)
- **ADR-007 Phase 2 — UUID migration for existing join tables**: Planned as Phase 5. Migrate `collection_artifacts`, `group_artifacts`, `artifact_tags` from `type:name` strings to UUID FK references. Phase 1 of ADR-007 (UUID column + CompositeMembership FK) is in Phase 1; Phase 2 is in Phase 5 (post-UI completion).

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Alembic migration breaks existing artifact rows or FK constraints | High | Low | Write reversible migration with down(); test on copy of production schema before deploy; Phase 1 quality gate requires clean rollback validation |
| Discovery false positives (flat repos mis-detected as composites) | Medium | Medium | Require threshold of 2+ distinct artifact-type subdirectories; use `plugin.json` as authoritative signal; unit test against 10-15 fixture repos; Phase 2 acceptance criteria enforce <5% false positive rate |
| Performance regression from graph traversal on large repos | Medium | Low | Limit composite detection to first 3 directory levels; add scan time telemetry; gate behind feature flag; Phase 2 quality gate requires <500ms overhead |
| Dedup hash collision (two different artifacts with same SHA-256) | Low | Very Low | SHA-256 collision probability negligible (~2^-128); document assumption; add name+hash pair check as secondary guard in Phase 3 |
| Version conflict resolution UX is confusing | Medium | Medium | Design conflict dialog (Phase 4) with clear side-by-side vs overwrite options; add escape hatch to skip plugin deploy; user testing on conflict scenarios |
| `ArtifactType` enum change breaks existing callers | High | Medium | Audit all call sites in Phase 1-01; ensure all `match`/`if-elif` chains are exhaustive; PR review enforces this; type-checking catches missed cases |
| Partial import leaves orphaned child artifacts | High | Low | Wrap plugin import in single DB transaction (Phase 3-03); use existing temp-dir + atomic move pattern; Phase 3 quality gate tests rollback scenario |
| Import modal doesn't load discovery graph before user confirms | Medium | Low | Ensure discovery completes and returns `DiscoveredGraph` before UI shows import button; Phase 4 E2E test validates this flow |
| Plugin deployment behavior differs by platform | Medium | Medium | Scope deploy conflict workflow to Claude Code for v1; return explicit unsupported response for other platforms |
| UUID column migration disrupts existing data | Medium | Low | ADR-007 specifies backfill strategy; migration tested on copy of production schema; Phase 1 quality gate validates UUID column |

---

## Key Files & Implementation References

### Database & ORM
- `skillmeat/cache/models.py` — Add composite entity + membership metadata models
- `skillmeat/cache/migrations/versions/` — Alembic migration for UUID column (ADR-007) + composite entity + membership metadata tables
- `skillmeat/cache/repositories.py` — Membership CRUD repository methods
- `skillmeat/core/artifact_detection.py` — Add `COMPOSITE` to `ArtifactType` enum; add `CompositeType` enum
- `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — UUID identity column design decision

### Discovery & Import
- `skillmeat/core/artifact_detection.py` — Update `ArtifactType`, add composite detection signatures
- `skillmeat/core/discovery.py` — Implement `DiscoveredGraph` BaseModel, update `discover_artifacts()` class method
- `skillmeat/core/importer.py` — Add hash-based dedup (leveraging existing content_hash), transaction wrapper, version pinning
- `skillmeat/core/sync.py` — Propagate composite membership metadata into project deployment state (Claude Code v1 scope)

### API & Frontend
- `skillmeat/api/routers/artifacts.py` — Add `GET /artifacts/{id}/associations` endpoint
- `skillmeat/api/schemas/` — Add `AssociationsDTO` schema
- `skillmeat/api/openapi.json` — Regenerate after new endpoint
- `skillmeat/web/app/artifacts/[id]/page.tsx` — Add "Contains" and "Part of" sections
- `skillmeat/web/hooks/useArtifactAssociations.ts` — React hook for fetching associations
- `skillmeat/web/components/import-modal.tsx` — Update import preview UI

### Testing
- `tests/test_composite_memberships.py` — Unit tests for composite entity/membership ORM model and repository
- `tests/test_composite_detection.py` — Discovery unit tests with fixture repos
- `tests/integration/test_plugin_import_integration.py` — Integration tests for smart import
- `skillmeat/web/__tests__/components/entity/content-pane.test.tsx` — Component tests for relationship tabs
- `skillmeat/web/tests/e2e/discovery.spec.ts` — E2E tests for core import flow

---

## Success Metrics

### Functional Success
- [ ] Plugin import end-to-end: source URL → detection → preview → confirm → DB rows + filesystem
- [ ] Deduplication verified: re-importing same plugin creates 0 new artifact rows for exact matches
- [ ] Transactional rollback verified: simulated mid-import failure leaves collection clean
- [ ] UI relationship discovery: users can navigate parent↔child within 2 clicks

### Technical Success
- [ ] Alembic migration applies & rolls back cleanly (including UUID column)
- [ ] API returns `AssociationsDTO` with correct parent/child lists
- [ ] Code coverage >80% for all new code
- [ ] False positive rate <5% in composite detection
- [ ] Observability: OTel spans logged for all key operations

### Quality Success
- [ ] Zero P0/P1 regressions in existing artifact import tests
- [ ] WCAG 2.1 AA compliance for UI relationship tabs
- [ ] Feature flag properly gates new behavior
- [ ] All acceptance criteria from PRD met

---

## Progress Tracking

See detailed progress tracking (one file per phase):
- `.claude/progress/composite-artifact-infrastructure/phase-1-progress.md`
- `.claude/progress/composite-artifact-infrastructure/phase-2-progress.md`
- `.claude/progress/composite-artifact-infrastructure/phase-3-progress.md`
- `.claude/progress/composite-artifact-infrastructure/phase-4-progress.md`
- `.claude/progress/composite-artifact-infrastructure/phase-5-progress.md`

These files will be created and updated as work progresses through each phase using the artifact-tracking CLI scripts.

---

**Implementation Plan Version**: 1.1
**Last Updated**: 2026-02-18
**Status**: Draft (awaiting approval)
