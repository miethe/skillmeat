---
title: 'Implementation Plan: SkillMeat UI Package Extraction Program'
description: Phased plan to create and adopt a reusable SkillMeat UI package, beginning with modal content viewer extraction and expanding to additional modal tab viewer surfaces.
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- refactor
- ui
- package
created: 2026-03-04
updated: 2026-03-04
category: product-planning
status: draft
schema_version: 2
doc_type: implementation_plan
feature_slug: skillmeat-ui-package-extraction
feature_version: v1
prd_ref: /docs/project_plans/PRDs/refactors/skillmeat-ui-package-extraction-v1.md
related:
- /docs/project_plans/PRDs/refactors/skillmeat-ui-package-extraction-v1.md
- /docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md
- /.claude/analysis/CONTENT-VIEWER-README.md
---
# Implementation Plan: SkillMeat UI Package Extraction Program

**Plan ID**: `SM-UI-PKG-IMPL-2026-03-04`
**Date**: 2026-03-04
**Author**: Codex (GPT-5) — Implementation Planner
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/refactors/skillmeat-ui-package-extraction-v1.md`
- **Initial Slice PRD**: `/docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md`
- **Analysis**: `/.claude/analysis/CONTENT-VIEWER-README.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 40 story points across 5 phases
**Target Timeline**: 3-5 weeks (incremental migration)

---

## Executive Summary

This plan creates a reusable UI package and migrates SkillMeat's modal viewer surfaces in controlled waves. Phase 1 establishes package governance and toolchain integration, Phase 2 delivers the initial content viewer module, and subsequent phases extend portability to additional modal tab viewer areas with parity gates to guarantee no user-facing regressions.

---

## Implementation Strategy

### Architecture Sequence

1. **Package Foundation**: workspace integration, build/test/release conventions, public API boundaries
2. **Initial Module Extraction**: content viewer module extraction and adapterization
3. **In-App Integration**: SkillMeat import migration with parity verification
4. **Expansion Waves**: additional modal tab viewer surfaces extracted via same pattern
5. **Stabilization and Versioning**: release discipline and deprecation of legacy local implementations

### Parallel Work Opportunities

- Documentation can be authored in parallel with extraction once public API shape stabilizes.
- Parity test scaffolding can start before full import cutover.
- Expansion-wave discovery can run during initial module hardening.

### Critical Path

1. Package scaffold + tooling integration
2. Initial content viewer extraction and adapter contracts
3. SkillMeat cutover for Contents tab
4. Regression/a11y validation gates
5. Expansion waves and cleanup

---

## Phase Breakdown

### Phase 1: Package Foundation and Governance

**Duration**: 4-5 days
**Dependencies**: None
**Assigned Subagent(s)**: frontend-developer, ui-engineer-enhanced, lead-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PKG-001 | Workspace strategy | Define package location and workspace mechanics | Package can be built/tested from repo workflow | 3 pts | lead-architect, frontend-developer | None |
| PKG-002 | Package skeleton | Create `packages/ui` scaffold with exports and build config | Package compiles and exports typed API | 3 pts | frontend-developer | PKG-001 |
| PKG-003 | API boundary policy | Establish public export surface and internal-only modules | No deep/private imports required by consumers | 2 pts | lead-architect | PKG-002 |
| PKG-004 | Versioning/release policy | Define semver/changelog/release checklist | Release checklist documented and reviewable | 1 pt | documentation-writer | PKG-002 |

**Phase 1 Quality Gates:**
- [ ] Package builds and type-checks in CI.
- [ ] Public API boundary documented.
- [ ] Release/versioning policy approved.

---

### Phase 2: Initial Content Viewer Module Delivery

**Duration**: 6-8 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, react-performance-optimizer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CVM-001 | Extract Tier-1 viewer units | Extract high-readiness viewer components/utils into package module | Component and utility exports match scoped checklist | 5 pts | ui-engineer-enhanced | PKG-003 |
| CVM-002 | Adapterize data hooks | Move API-specific fetching into SkillMeat adapters/injected fetchers | Generic module has no hardcoded SkillMeat API paths | 4 pts | frontend-developer | CVM-001 |
| CVM-003 | Define content viewer contracts | Finalize props/types for modal and non-modal usage | Typed contracts documented and consumed in app | 3 pts | lead-architect, frontend-developer | CVM-001 |
| CVM-004 | Bundle/perf controls | Add optional/lazy boundaries for heavier editor paths if required | No material bundle/perf regression vs baseline | 2 pts | react-performance-optimizer | CVM-001 |

**Phase 2 Quality Gates:**
- [ ] Content viewer module is consumable from package exports.
- [ ] SkillMeat-specific logic remains outside generic package core.
- [ ] Performance baseline checks pass.

---

### Phase 3: SkillMeat Integration and Parity Validation

**Duration**: 5-6 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: frontend-developer, testing specialist, web-accessibility-checker

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| INT-001 | Import migration | Switch SkillMeat content-viewer imports to package exports | Contents tab runs with package components in all supported flows | 4 pts | frontend-developer | CVM-003 |
| INT-002 | Parity test suite | Add/update component/integration tests for behavior parity | All parity tests pass and cover critical interactions | 3 pts | testing specialist | INT-001 |
| INT-003 | Accessibility regression pass | Validate keyboard navigation/ARIA parity for extracted components | No critical a11y regressions found | 2 pts | web-accessibility-checker | INT-001 |
| INT-004 | Rollback protocol | Document temporary rollback path to local implementation | Rollback path verified in staging environment | 1 pt | frontend-developer | INT-001 |

**Phase 3 Quality Gates:**
- [ ] No P0/P1 regressions in Artifact Modal Contents flows.
- [ ] a11y parity confirmed.
- [ ] Rollback strategy documented and tested.

---

### Phase 4: Additional Modal Viewer Waves

**Duration**: 6-8 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, lead-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| WAVE-001 | Candidate inventory | Identify and classify additional modal tab viewer surfaces | Wave backlog prioritized with coupling assessment | 2 pts | lead-architect | INT-002 |
| WAVE-002 | Extract selected wave | Extract next approved viewer group using same adapter pattern | Wave components exported and integrated without regressions | 4 pts | ui-engineer-enhanced | WAVE-001 |
| WAVE-003 | Repeat parity hardening | Execute parity/a11y/perf gates for each wave | Each migrated wave passes same gate set | 3 pts | testing specialist, web-accessibility-checker | WAVE-002 |

**Phase 4 Quality Gates:**
- [ ] Wave scope approved before extraction.
- [ ] Each wave passes parity checks before merge.
- [ ] Domain leakage into package core remains zero.

---

### Phase 5: Stabilization, Cleanup, and Adoption

**Duration**: 4-5 days
**Dependencies**: Phase 4 complete
**Assigned Subagent(s)**: documentation-writer, frontend-developer, lead-pm

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| STAB-001 | Remove legacy duplicates | Delete/reduce superseded local implementations | No dead duplicate viewer implementations remain in scope areas | 2 pts | frontend-developer | WAVE-003 |
| STAB-002 | Consumer docs/examples | Publish usage docs for modal + non-modal embedding | External consumer path is documented and validated | 2 pts | documentation-writer | STAB-001 |
| STAB-003 | Release hardening | Finalize changelog/version and release candidate | Tagged release candidate available | 2 pts | lead-pm, frontend-developer | STAB-002 |

**Phase 5 Quality Gates:**
- [ ] Legacy duplicates removed from scoped areas.
- [ ] Documentation complete and reviewed.
- [ ] Release candidate passes CI gates.

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Migration introduces subtle UI behavior drift | High | Medium | Parity tests and side-by-side validation checklist |
| Package API churn causes downstream breakage | Medium | Medium | API review gate + semver discipline |
| Styling token mismatch between projects | Medium | Medium | Explicit style/token requirements and reference stylesheet |
| Expanded scope delays delivery | Medium | Medium | Keep wave backlog prioritized; ship initial slice first |

---

## Success Metrics

- Initial content viewer extraction completed and used in SkillMeat.
- Zero critical regressions in migrated modal paths.
- At least one additional viewer wave planned and sequenced post-initial slice.
- Package release process documented and operational.

---

## Implementation Order Recommendation

1. Execute initial slice via dedicated plan (`artifact-modal-content-viewer-extraction-v1`).
2. Promote package foundation into standard frontend development workflow.
3. Run additional extraction waves only after initial slice parity stabilizes.

---

## Linked Detailed Plan

- `/docs/project_plans/implementation_plans/refactors/artifact-modal-content-viewer-extraction-v1.md`
