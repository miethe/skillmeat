---
title: 'Implementation Plan: Skill-Contained Artifacts'
description: >
  Phased implementation plan to extend the existing CompositeArtifact /
  CompositeMembership infrastructure to model Skills with embedded sub-artifacts,
  enabling atomic import with deduplication, member visibility in the UI,
  coordinated deployment, and three-layer version tracking.
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-02-21
updated: 2026-02-21
feature_slug: skill-contained-artifacts-v1
feature_version: v1
prd_ref: /docs/project_plans/PRDs/features/skill-contained-artifacts-v1.md
plan_ref: null
scope: >
  Extend composite_type to include "skill", wire the import pipeline to create
  CompositeArtifact rows for skills with embedded artifacts, surface membership
  in the UI, and add coordinated deployment and version tracking.
effort_estimate: "30 story points / ~16 days"
architecture_summary: >
  Schema migration → import pipeline extension → associations API fix →
  marketplace UI generalization → collection UI generalization →
  deployment extension → version tracking → testing & validation.
related_documents:
  - /docs/project_plans/PRDs/features/skill-contained-artifacts-v1.md
  - /docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md
  - /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
  - /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
owner: null
contributors: []
priority: high
risk_level: medium
category: product-planning
tags:
  - implementation
  - planning
  - phases
  - skills
  - composite-artifacts
  - embedded-artifacts
  - import
  - deployment
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - skillmeat/cache/models.py
  - skillmeat/cache/composite_repository.py
  - skillmeat/core/services/composite_service.py
  - skillmeat/core/importer.py
  - skillmeat/core/deployment.py
  - skillmeat/api/routers/artifacts.py
  - skillmeat/web/components/artifact/artifact-contains-tab.tsx
  - skillmeat/web/components/artifact/artifact-part-of-section.tsx
  - skillmeat/web/components/marketplace/source-artifact-modal.tsx
---

# Implementation Plan: Skill-Contained Artifacts

**Plan ID**: `SCA-IMPL-2026-02-21`
**Date**: 2026-02-21
**Author**: Claude (Sonnet 4.6) — Implementation Planner
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/skill-contained-artifacts-v1.md`
- **Predecessor plan**: `/docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md`
- **Predecessor plan**: `/docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 30 story points across 8 phases (~16 days)
**Target Timeline**: ~4 weeks at 1 FTE backend + 0.5 FTE frontend (phases overlap)

---

## Executive Summary

This plan extends the proven `CompositeArtifact` / `CompositeMembership` infrastructure — already operational for Plugins — to cover Skills with embedded sub-artifacts. The implementation requires minimal net-new code: one Alembic migration adds `"skill"` to the `composite_type` CHECK constraint, the import pipeline (`importer.py`) is extended to call the existing `CompositeService`, the associations router is wired to resolve the skill UUID → companion `CompositeArtifact`, and two frontend components receive label generalization only. New work appears in deployment (member-aware deploy) and version tracking (per-member drift). All changes are guarded by the `SKILL_CONTAINED_ARTIFACTS_ENABLED` feature flag until Phase 8.

**Success criteria**: Importing a skill with embedded artifacts creates 1 `CompositeArtifact` row and N `CompositeMembership` rows; re-importing creates zero duplicates; the Members tab renders in the collection UI; `skillmeat deploy` places all member files at their correct paths; per-member version drift is surfaced in the sync tab.

---

## Implementation Strategy

### Architecture Sequence

Following the SkillMeat layered architecture:

1. **Schema Layer** (Phase 1) — Alembic migration to extend `composite_type` CHECK; ORM model + `CompositeService` update
2. **Import Pipeline** (Phase 2) — Extend `importer.py` to call `create_skill_composite()` atomically
3. **API Layer** (Phase 3) — Fix `GET /associations` to resolve skill UUID → `CompositeArtifact`
4. **Marketplace UI** (Phase 4) — Generalize source modal "Plugin Breakdown" tab for skills
5. **Collection UI** (Phase 5) — Generalize `artifact-contains-tab.tsx` and verify "Part of" section
6. **Deployment** (Phase 6) — Member-aware `DeploymentManager.deploy()` + CLI flags
7. **Version Tracking** (Phase 7) — Per-member drift in sync tab + `skillmeat list` indicator
8. **Testing & Validation** (Phase 8) — Full E2E suite, regression, performance, feature flag enable

### Parallel Work Opportunities

- **Phases 4 and 5** (UI) can begin once Phase 3 (API) contract is stable, in parallel with Phase 6 (deployment) backend work.
- **Phase 7** (version tracking backend) can run concurrently with Phase 5 (collection UI).
- Unit tests for each phase are written in the same batch as implementation, not deferred to Phase 8.

### Critical Path

Phase 1 (schema) → Phase 2 (import) → Phase 3 (API) → Phase 5 (collection UI) → Phase 8 (E2E)

Phase 4 (marketplace UI) and Phase 6 (deployment) are off the critical path and can run concurrently with Phase 5.

---

## Phase Breakdown

### Phase 1: Schema Extension

**Duration**: 2 days
**Dependencies**: None
**Entry criteria**: Existing DB has `CompositeArtifact` with `composite_type IN ('plugin', 'stack', 'suite')`
**Exit criteria**: Migration up/down succeeds on a DB with existing plugin rows; `CompositeService.create_skill_composite()` method exists and passes unit tests
**Parallelization**: All tasks in this phase are sequential (migration must precede model/service updates)

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P1-01 | Alembic migration | Add `"skill"` to `check_composite_artifact_type` CHECK constraint using `batch_alter_table` for SQLite compatibility. Use DROP + re-create pattern. | `alembic upgrade head` and `alembic downgrade -1` both succeed on a DB containing existing plugin `CompositeArtifact` rows; no existing rows affected | 2 pts | data-layer-expert | None |
| SCA-P1-02 | ORM model update | Update `CompositeArtifact.__table_args__` CHECK constraint literal and model docstring in `skillmeat/cache/models.py` to reflect the new valid values | Model reflects `('plugin', 'stack', 'suite', 'skill')`; existing plugin tests still pass | 0.5 pts | data-layer-expert | SCA-P1-01 |
| SCA-P1-03 | CompositeService extension | Add `create_skill_composite(skill_artifact, embedded_list)` method to `CompositeService`. Creates a `CompositeArtifact` row (`composite_type="skill"`, `metadata_json={"artifact_uuid": skill_uuid}`) and stubs out member creation (dedup logic lands in Phase 2) | Method exists, creates `CompositeArtifact` row, unit test verifies row fields | 1 pt | python-backend-engineer | SCA-P1-02 |

**Phase 1 Quality Gates:**
- [ ] Migration upgrade + downgrade both pass on SQLite and PostgreSQL
- [ ] No existing plugin `CompositeArtifact` rows modified by the migration
- [ ] `create_skill_composite()` unit test: happy path creates 1 `CompositeArtifact` row with correct `composite_type` and `metadata_json`
- [ ] `flake8` and `mypy` pass on changed files

---

### Phase 2: Import Pipeline Extension

**Duration**: 3 days
**Dependencies**: Phase 1 complete
**Entry criteria**: `create_skill_composite()` stub exists in `CompositeService`
**Exit criteria**: Importing a fixture skill with 3 embedded artifacts creates 1 `CompositeArtifact` row, 3 `CompositeMembership` rows, and 0 duplicate `Artifact` rows on re-import
**Parallelization**: SCA-P2-01 through SCA-P2-03 are sequential. SCA-P2-04 (integration test) can overlap with SCA-P2-03 authoring.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P2-01 | Dedup logic in CompositeService | Complete `create_skill_composite()`: for each `DetectedArtifact` in `embedded_list`, check `collection` for existing `Artifact` by content hash; reuse UUID if found, else create new `Artifact` row | Integration test: import two skills sharing a command — command `Artifact` row count stays at 1 | 2 pts | python-backend-engineer | SCA-P1-03 |
| SCA-P2-02 | CompositeMembership creation | After hash dedup, create `CompositeMembership` row linking the `CompositeArtifact` to each child `Artifact` UUID. Use existing `unique(collection_id, composite_id, child_artifact_uuid)` index for idempotency | Membership rows created; re-import of same skill does not create duplicate membership rows (upsert semantics) | 1 pt | python-backend-engineer | SCA-P2-01 |
| SCA-P2-03 | Atomic transaction wiring in importer.py | Extend `importer.py`: after skill `Artifact` row is committed, call `create_skill_composite()` inside the same SQLAlchemy `Session.begin()` block. Any exception triggers full rollback — no partial state persisted. Guard entire block with `SKILL_CONTAINED_ARTIFACTS_ENABLED` feature flag. | Rollback integration test: force failure after `CompositeArtifact` insert, verify no orphaned rows; feature flag off = old behavior unchanged | 2 pts | python-backend-engineer | SCA-P2-02 |
| SCA-P2-04 | Observability instrumentation | Add OpenTelemetry spans for: skill composite creation, member dedup check, membership link creation. Add structured log fields: `skill_artifact_uuid`, `composite_id`, `member_count`, `dedup_hit_count` | Spans present in test trace output; log fields visible in structured output | 1 pt | python-backend-engineer | SCA-P2-03 |

**Phase 2 Quality Gates:**
- [ ] Integration test: import fixture skill with 3 embedded artifacts — verify 1 `CompositeArtifact` + 3 `CompositeMembership` rows in DB
- [ ] Integration test: re-import same skill — verify 0 new `Artifact` rows created (dedup working)
- [ ] Integration test: forced failure mid-import — verify full rollback (no orphaned rows)
- [ ] Feature flag off: existing import behavior unchanged, no composite rows created
- [ ] OpenTelemetry spans emitted for all new code paths

---

### Phase 3: API Wiring

**Duration**: 1 day
**Dependencies**: Phase 2 complete
**Entry criteria**: `CompositeMembership` rows exist in DB for imported test skills
**Exit criteria**: `GET /api/v1/artifacts/{skill_id}/associations` returns the member list for a skill with embedded artifacts
**Parallelization**: Single focused task; no parallelization needed

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P3-01 | Associations router fix | Update `GET /api/v1/artifacts/{artifact_id}/associations` in `skillmeat/api/routers/artifacts.py`: when the artifact is a skill, look up companion `CompositeArtifact` by querying `metadata_json->>'artifact_uuid' = artifact_id`. Then query `CompositeMembership` rows by `composite_id`. Return existing `AssociationsDTO` (no schema change). | API test: `GET /associations` for a skill with 3 members returns 3 children in response; for a skill with no members returns empty (no regression) | 1 pt | python-backend-engineer | SCA-P2-04 |
| SCA-P3-02 | API integration tests | Add pytest integration tests covering: skill with members, skill with no members (empty response), non-skill artifact (existing plugin behavior unchanged), missing skill (404) | All 4 test scenarios pass; existing plugin association tests pass | 1 pt | python-backend-engineer | SCA-P3-01 |

**Phase 3 Quality Gates:**
- [ ] `GET /associations` for skill with members returns correct children
- [ ] `GET /associations` for plugin returns existing behavior (no regression)
- [ ] Response time for 20-member skill under 200 ms (measured in integration test)
- [ ] OpenAPI spec updated (or confirmed unchanged — existing schema covers the response)

---

### Phase 4: Marketplace UI

**Duration**: 2 days
**Dependencies**: Phase 3 complete (API contract stable)
**Entry criteria**: `GET /associations` returns members for skills; existing "Plugin Breakdown" tab renders correctly
**Exit criteria**: Source modal renders "Skill Members" tab for skills with embedded artifacts; member count badge appears on skill source cards
**Parallelization**: Can run concurrently with Phase 6 (deployment backend) once Phase 3 is done

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P4-01 | Generalize source modal tab label | In `skillmeat/web/components/marketplace/source-artifact-modal.tsx`, drive the breakdown tab label from `composite_type`: `"Plugin Members"` for `plugin`, `"Skill Members"` for `skill`. No structural component changes; label substitution only. | Snapshot test: plugin modal still shows "Plugin Members"; skill modal shows "Skill Members"; tab content renders member list | 1 pt | ui-engineer-enhanced | SCA-P3-02 |
| SCA-P4-02 | Member count badge on skill source cards | Surface member count on skill source cards in the marketplace listing (reuse existing badge pattern used for plugin member counts). Query: `embedded_artifacts` count from detection data or `CompositeMembership` count from associations endpoint. | E2E: skill card with 3 members shows `[3]` badge; skill with no members shows no badge; plugin card behavior unchanged | 2 pts | ui-engineer-enhanced | SCA-P4-01 |

**Phase 4 Quality Gates:**
- [ ] Snapshot test: "Plugin Members" label still correct for plugin composites
- [ ] Snapshot test: "Skill Members" label shown for skill composites
- [ ] E2E: member count badge renders on skill cards with members
- [ ] Accessibility: tab has `aria-label`, member list uses role-appropriate semantics
- [ ] No console errors or TypeScript errors introduced

---

### Phase 5: Collection UI

**Duration**: 2 days
**Dependencies**: Phase 3 complete
**Entry criteria**: `GET /associations` wired; `artifact-contains-tab.tsx` renders "Plugin Members" for plugins
**Exit criteria**: `artifact-contains-tab.tsx` renders "{Type} Members" for any composite type; "Part of" section renders on member artifact views linked to their parent skill
**Parallelization**: Can run concurrently with Phase 6 (deployment backend)

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P5-01 | Generalize artifact-contains-tab label | In `skillmeat/web/components/artifact/artifact-contains-tab.tsx`, replace hardcoded `"Plugin Members"` with `"{displayType} Members"` derived from `composite_type` via `ARTIFACT_TYPES` config (or equivalent display name lookup). | Snapshot test: plugin artifact shows "Plugin Members"; skill artifact shows "Skill Members"; component handles unknown composite_type gracefully (fallback label) | 1 pt | ui-engineer-enhanced | SCA-P3-02 |
| SCA-P5-02 | Verify "Part of" section for skills | Verify that `artifact-part-of-section.tsx` renders correctly for member artifacts (commands, agents, hooks) that belong to a skill. Should work automatically once `GET /associations` is wired; confirm with E2E test. Fix any label or query gap if found. | E2E: a command that is a member of a skill shows "Part of: [Skill Name]" in its Links tab; plugin member behavior unchanged | 1 pt | ui-engineer-enhanced | SCA-P5-01 |
| SCA-P5-03 | Collection UI E2E tests | Write Playwright/Jest E2E tests: (1) skill detail modal shows Members tab with correct member count; (2) member artifact shows "Part of" section; (3) plugin detail modal behavior unchanged | All 3 E2E scenarios pass in CI | 2 pts | ui-engineer-enhanced | SCA-P5-02 |

**Phase 5 Quality Gates:**
- [ ] Snapshot test: label generalization correct for plugin and skill composite types
- [ ] E2E: Members tab renders for skill with 3 members (correct count + names)
- [ ] E2E: "Part of" section renders on a member command/agent view
- [ ] E2E: plugin Members tab behavior unchanged (regression check)
- [ ] WCAG 2.1 AA: Members tab keyboard-navigable, `aria-label` present

---

### Phase 6: Deployment

**Duration**: 2 days
**Dependencies**: Phase 3 complete (associations query used by deploy)
**Entry criteria**: `CompositeMembership` rows exist for imported skill; `DeploymentManager.deploy()` exists and works for single-file artifacts
**Exit criteria**: `skillmeat deploy <skill>` deploys skill file + all members to type-specific paths; `--no-members` skips members
**Parallelization**: Can run concurrently with Phases 4 and 5 (UI work)

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P6-01 | Member-aware DeploymentManager | Extend `skillmeat/core/deployment.py` `DeploymentManager.deploy()` with `include_members: bool = True` parameter. When `True`: query `CompositeMembership` children via associations, deploy each to its type-specific path (`commands/` → `.claude/commands/`, `agents/` → `.claude/agents/`, etc.). Wrap in atomic operation; rollback on any failure. Apply existing conflict detection before overwriting user-customized files. | Integration test: deploy fixture skill with 3 members; verify all 4 files written at correct paths; forced failure mid-deploy: no partial writes persist | 3 pts | python-backend-engineer | SCA-P3-02 |
| SCA-P6-02 | CLI flags for deploy | Add `--members` / `--no-members` boolean flags to `skillmeat deploy` CLI command. Default: `--members` (include members). Update `--help` text. | `skillmeat deploy skill-name --no-members` deploys skill file only; `skillmeat deploy skill-name` deploys skill + members; `skillmeat deploy skill-name --help` shows both flags | 1 pt | python-backend-engineer | SCA-P6-01 |
| SCA-P6-03 | Deployment integration tests | Pytest integration tests: deploy with members (verify paths), deploy with `--no-members` (verify member paths absent), deploy of non-skill artifact (existing behavior unchanged), conflict detection triggers prompt on locally-modified member file | All 4 test scenarios pass | 1 pt | python-backend-engineer | SCA-P6-02 |

**Phase 6 Quality Gates:**
- [ ] Integration test: skill deploy with members places all member files at correct type-specific paths
- [ ] Integration test: `--no-members` deploys skill file only
- [ ] Integration test: atomic rollback on partial deployment failure
- [ ] Conflict detection works for member files (no silent overwrites)
- [ ] CLI `--help` updated; `mypy` and `flake8` pass

---

### Phase 7: Version Tracking & Sync

**Duration**: 2 days
**Dependencies**: Phase 2 complete (membership rows exist); Phase 5 partially (sync tab component)
**Entry criteria**: Skill `CompositeMembership` rows populated in DB; existing sync diff logic handles individual artifact version comparison
**Exit criteria**: Sync status tab shows per-member drift rows for skills; `skillmeat list` shows `[+N members]` indicator
**Parallelization**: Backend (SCA-P7-01) can run concurrently with Phase 5 UI work. Frontend (SCA-P7-02) depends on SCA-P7-01.

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P7-01 | Sync diff logic for skill members | Extend sync diff logic to generate per-member version comparison rows for skills (source version vs. collection version vs. deployed version). Each member appears as a child row under its parent skill row in the diff result. | Unit test: sync diff for a skill with 3 members produces 4 rows (1 skill + 3 members); member row includes `source_version`, `collection_version`, `deployed_version` fields | 2 pts | python-backend-engineer | SCA-P2-04 |
| SCA-P7-02 | Surface member drift in sync status tab | Update `skillmeat/web/components/sync-status/sync-status-tab.tsx` to render per-member drift rows as collapsible children under the parent skill row. Reuse existing diff row component; add expand/collapse toggle. | E2E: sync tab for a skill with drift shows skill row + expandable member rows each with source/collection/deployed version; members with no drift shown as "up to date" | 2 pts | ui-engineer-enhanced | SCA-P7-01 |
| SCA-P7-03 | CLI list member count indicator | Extend `skillmeat list` output to show `[+N members]` beside skills that have `CompositeMembership` rows. Reuse associations query. | Unit test: `skillmeat list` output for a skill with 3 members contains `[+3 members]`; skill with no members shows no indicator; plugin cards unchanged | 1 pt | python-backend-engineer | SCA-P7-01 |

**Phase 7 Quality Gates:**
- [ ] Unit test: sync diff produces correct per-member row structure
- [ ] E2E: sync status tab renders per-member drift rows for a skill with version differences
- [ ] `skillmeat list` member count indicator correct for skills with and without members
- [ ] No regression in existing single-artifact sync diff behavior

---

### Phase 8: Testing & Validation

**Duration**: 2 days
**Dependencies**: All previous phases complete
**Entry criteria**: All functional tasks (Phases 1-7) complete and locally verified; feature flag off by default
**Exit criteria**: Full E2E suite passes; no regressions in existing plugin composite tests; performance benchmarks met; feature flag enabled by default
**Parallelization**: SCA-P8-01 (full E2E), SCA-P8-02 (regression suite), and SCA-P8-03 (performance) can run in parallel

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------------|--------------|
| SCA-P8-01 | Full E2E test flow | Write/run end-to-end test: marketplace browse skill → view "Skill Members" tab → import skill → verify collection Members tab → deploy skill + members → verify file placement at correct paths | All steps pass in CI with fixture skill containing 3 embedded artifacts | 2 pts | task-completion-validator | All Phase 1-7 tasks |
| SCA-P8-02 | Plugin regression suite | Run existing plugin composite tests in full. Fix any regressions introduced by label generalization or associations API changes. | All pre-existing plugin composite tests pass without modification | 0.5 pts | python-backend-engineer | All Phase 1-7 tasks |
| SCA-P8-03 | Performance benchmarks | Measure: (1) import skill with 10 embedded artifacts (target <5s); (2) `GET /associations` for skill with 20 members (target P95 <200ms). Add `idx_composite_artifacts_metadata_json` index if (2) is slow. | Both benchmarks meet targets; results documented in PR description | 1 pt | python-backend-engineer | SCA-P8-01 |
| SCA-P8-04 | Enable feature flag | Set `SKILL_CONTAINED_ARTIFACTS_ENABLED` default to `true` in feature flag configuration. Update `CHANGELOG.md`. | Feature flag default is `true`; full test suite passes with flag enabled; `CHANGELOG.md` has v1 entry for skill-contained artifacts | 0.5 pts | python-backend-engineer | SCA-P8-03 |

**Phase 8 Quality Gates:**
- [ ] Full E2E test flow passes in CI
- [ ] Zero regressions in existing plugin composite tests
- [ ] Import benchmark: 10-member skill import < 5 seconds
- [ ] Associations API benchmark: P95 < 200 ms for 20-member skill
- [ ] `SKILL_CONTAINED_ARTIFACTS_ENABLED` default set to `true`
- [ ] `CHANGELOG.md` entry present
- [ ] `skillmeat deploy --help` documents `--members` / `--no-members`

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| SQLite `batch_alter_table` migration fails on CHECK constraint recreation | High | Low | Test migration against SQLite fixture DB before merging; PRD Q4 resolution requires `batch_alter_table` explicitly |
| `metadata_json` JSON lookup (`->>'artifact_uuid'`) is slow at scale | Medium | Low | Benchmark in SCA-P8-03; add `idx_composite_artifacts_metadata_json` GIN index if needed |
| `embedded_artifacts` list from `heuristic_detector.py` is incomplete for edge-case skill layouts | Medium | Medium | Validate against 10 real-world GitHub skill repos before Phase 2 merge; add fixture-based unit tests for detection edge cases |
| Partial import state on failure leaves orphaned `CompositeArtifact` rows | High | Low | Entire Phase 2 import wrapped in single `Session.begin()` block; rollback integration test required for Phase 2 exit |
| Coordinated deployment overwrites user-customized member files | Medium | Medium | Conflict detection applied to each member file before overwrite (Phase 6); prompt user if conflict found |
| UI label generalization introduces plugin view regressions | Low | Low | Snapshot tests for plugin modal taken before and after change; SCA-P8-02 regression suite |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Phase 2 import dedup is more complex than estimated | Medium | Medium | Hash-based dedup pattern already exists in plugin import; reuse directly — estimate is conservative |
| Phase 7 sync tab UI requires larger refactor than expected | Medium | Low | FR-10 is a "Should" requirement; can defer sync tab UI to follow-on PR while keeping SCA-P7-01 backend diff logic |
| FR-12 (re-import reconciliation) scope creep | Medium | Medium | Explicitly out of scope for v1; warning log added in SCA-P2-03 when re-importing a skill with existing membership rows |

---

## Resource Requirements

### Team Composition

- **python-backend-engineer**: Primary for Phases 1-3, 6-8 backend tasks
- **data-layer-expert**: Phase 1 migration and ORM model tasks
- **ui-engineer-enhanced**: Phases 4, 5, 7 frontend tasks
- **task-completion-validator**: Phase 8 E2E validation

### Key Files

| File | Phase | Change Type |
|------|-------|-------------|
| `skillmeat/cache/models.py` | 1 | CHECK constraint update |
| `skillmeat/core/services/composite_service.py` | 1-2 | New method `create_skill_composite()` |
| `skillmeat/core/importer.py` | 2 | Call `create_skill_composite()` in import transaction |
| `skillmeat/api/routers/artifacts.py` | 3 | Skill UUID → CompositeArtifact lookup |
| `skillmeat/web/components/marketplace/source-artifact-modal.tsx` | 4 | Tab label generalization |
| `skillmeat/web/components/artifact/artifact-contains-tab.tsx` | 5 | Tab label generalization |
| `skillmeat/web/components/artifact/artifact-part-of-section.tsx` | 5 | Verify (likely no change) |
| `skillmeat/core/deployment.py` | 6 | Member-aware deploy + `include_members` param |
| `skillmeat/web/components/sync-status/sync-status-tab.tsx` | 7 | Per-member drift rows |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| `CompositeArtifact` rows created on skill import | 1 per skill with embedded artifacts | DB query in integration test |
| Duplicate artifacts on re-import | 0 | Integration test: import twice, verify artifact count |
| UI Members tab renders for skills | 100% of skills with `CompositeMembership` rows | E2E test |
| Coordinated deploy success rate | 100% (all members at correct paths) | Integration test |
| Version drift detection coverage | All embedded members tracked | Unit test on sync diff |
| Import performance (10 members) | < 5 seconds | Benchmark in Phase 8 |
| Associations API P95 (20 members) | < 200 ms | Benchmark in Phase 8 |
| Plugin composite regression | 0 regressions | Phase 8 regression suite |

---

## Post-Implementation

- Monitor `composite_artifacts` table growth per ingestion cycle.
- Track dedup hit rate (ratio of reused to new member `Artifact` rows) in structured logs.
- Follow-on scope: FR-12 re-import reconciliation (add/remove members on upstream update) — deferred to a separate PR.
- Follow-on scope: Membership mutation UI (add/remove members from the collection UI) — explicitly out of scope for v1.

---

**Progress Tracking:**

See `.claude/progress/skill-contained-artifacts-v1/all-phases-progress.md` (created when implementation begins)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-21
