---
title: 'Implementation Plan: Artifact Modal Content Viewer Extraction (Initial Slice)'
description: Detailed implementation plan for creating the new UI package foundation
  and extracting/integrating artifact modal content viewer panes with zero-regression
  safeguards.
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- refactor
- ui
- content-viewer
created: 2026-03-04
updated: '2026-03-13'
category: product-planning
status: completed
schema_version: 2
doc_type: implementation_plan
feature_slug: artifact-modal-content-viewer-extraction
feature_version: v1
prd_ref: /docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md
related:
- /docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md
- /docs/project_plans/PRDs/refactors/skillmeat-ui-package-extraction-v1.md
- /.claude/analysis/content-viewing-extraction-inventory.md
- /.claude/analysis/content-viewer-quick-ref.md
- /.claude/analysis/content-viewer-extraction-report.md
---
# Implementation Plan: Artifact Modal Content Viewer Extraction (Initial Slice)

**Plan ID**: `SM-CV-EXTRACT-IMPL-2026-03-04`
**Date**: 2026-03-04
**Author**: Codex (GPT-5) — Implementation Planner
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md`
- **Umbrella PRD**: `/docs/project_plans/PRDs/refactors/skillmeat-ui-package-extraction-v1.md`
- **Analysis README**: `/.claude/analysis/CONTENT-VIEWER-README.md`

**Complexity**: Medium-Large (M/L)
**Total Estimated Effort**: 24 story points across 6 phases
**Target Timeline**: 2-3 weeks

---

## Executive Summary

This plan delivers the first production extraction slice for the new UI package: artifact modal content viewers. It creates package scaffolding, extracts scoped viewer components/utilities, introduces adapter contracts for data fetching, and migrates SkillMeat's Contents tab usage with strict parity checks to avoid user-facing regressions.

---

## Scope Baseline from Analysis

### Tier-1 High-Readiness Units (Primary)

- `FileTree`
- `FrontmatterDisplay`
- Frontmatter utilities (`detect/parse/strip`)
- README extraction utilities
- Generic file response/types and query patterns

### Additional Viewer Pane Units (Initial Slice Extension)

- `ContentPane`
- `SplitPreview`
- `MarkdownEditor`

### Must Stay Local to SkillMeat

- Detection-pattern and semantic tree filtering logic
- Marketplace-specific filter utilities and enums
- SkillMeat API route ownership and domain orchestration

---

## Implementation Strategy

### Architecture Sequence

1. **Foundation**: Create package and build/tooling integration.
2. **Portable Core**: Extract generic viewer components/utilities/types.
3. **Adapter Layer**: Keep backend/domain coupling in SkillMeat.
4. **Integration**: Cut over modal Contents tab imports.
5. **Validation**: Test parity, accessibility, performance.
6. **Release Prep**: Document usage and finalize migration checklist.

### Critical Path

- Package scaffold -> component extraction -> adapter contracts -> in-app cutover -> parity validation.

---

## Phase Breakdown

### Phase 0: Baseline and Guardrails

**Duration**: 1-2 days
**Dependencies**: None
**Assigned Subagent(s)**: frontend-developer, testing specialist

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BASE-001 | Baseline inventory lock | Confirm exact v1 extraction list from analysis docs | Approved extraction matrix committed to plan notes | 1 pt | frontend-developer | None |
| BASE-002 | Parity scenario matrix | Define critical user flows for Contents tab parity | Test matrix covers selection, loading, errors, edit/save, frontmatter, truncation | 1 pt | testing specialist | BASE-001 |

**Phase 0 Quality Gates:**
- [ ] v1 extraction scope finalized and signed off.
- [ ] Parity scenarios documented.

---

### Phase 1: UI Package Scaffold and Tooling

**Duration**: 2-3 days
**Dependencies**: Phase 0 complete
**Assigned Subagent(s)**: frontend-developer, lead-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PKG-101 | Create package structure | Add package location, tsconfig/build configs, entrypoints | Package compiles and exposes typed exports | 2 pts | frontend-developer | BASE-002 |
| PKG-102 | Integrate workspace scripts | Ensure app and package build/test/type-check flow works together | CI and local scripts execute without manual hacks | 2 pts | frontend-developer | PKG-101 |
| PKG-103 | Public API contract | Define export boundaries for content-viewer module | Contract doc + index exports finalized | 1 pt | lead-architect | PKG-101 |

**Phase 1 Quality Gates:**
- [ ] Package build/type-check integrated.
- [ ] Public export map approved.

---

### Phase 2: Extract Generic Utilities, Types, and Tree Components

**Duration**: 3-4 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| EXT-201 | Utility extraction | Extract frontmatter and readme helper utilities | Utility tests pass in package context | 2 pts | frontend-developer | PKG-103 |
| EXT-202 | `FileTree` extraction | Port and stabilize generic file tree component | Keyboard navigation + ARIA parity maintained | 3 pts | ui-engineer-enhanced | EXT-201 |
| EXT-203 | `FrontmatterDisplay` extraction | Port metadata display component | Rendering parity for supported value types | 1 pt | ui-engineer-enhanced | EXT-201 |
| EXT-204 | Shared type exports | Export `FileNode` and content response contracts | Consumers compile with exported types only | 1 pt | frontend-developer | EXT-201 |

**Phase 2 Quality Gates:**
- [ ] Utilities/components compile and test from package.
- [ ] No SkillMeat-specific imports remain in extracted units.

---

### Phase 3: Extract Content Pane Surfaces and Adapterize Data Paths

**Duration**: 3-4 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, react-performance-optimizer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| EXT-301 | `ContentPane` extraction | Port content pane with portable props/events | Supports read-only and editable use in modal/non-modal contexts | 3 pts | ui-engineer-enhanced | EXT-204 |
| EXT-302 | `SplitPreview` + `MarkdownEditor` extraction | Port editor surfaces with optional usage pattern | Heavy editor paths remain optional and documented | 2 pts | ui-engineer-enhanced | EXT-301 |
| EXT-303 | Hook adapter abstraction | Replace hardcoded API hooks with injected fetchers or app adapters | Generic module has no fixed SkillMeat endpoint dependency | 2 pts | frontend-developer | EXT-301 |
| EXT-304 | Perf guardrails | Validate bundle and runtime impact; add lazy boundaries if required | No material regressions in measured baseline | 1 pt | react-performance-optimizer | EXT-302 |

**Phase 3 Quality Gates:**
- [ ] Content pane stack exported and typed.
- [ ] Adapter abstraction implemented and verified.
- [ ] Perf gate passed.

---

### Phase 4: SkillMeat Cutover for Contents Tab

**Duration**: 2-3 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: frontend-developer, ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| INT-401 | Modal integration | Replace local imports in modal content-viewer paths with package imports | Artifact modal Contents tab uses package module in all supported states | 2 pts | frontend-developer | EXT-303 |
| INT-402 | SkillMeat adapters | Implement/verify local adapter glue for API and domain-specific paths | Domain coupling remains outside package core | 1 pt | frontend-developer | INT-401 |
| INT-403 | Cleanup pass | Remove or deprecate duplicate local implementations in scope | No conflicting duplicate import paths in active usage | 1 pt | ui-engineer-enhanced | INT-401 |

**Phase 4 Quality Gates:**
- [ ] Imports switched for scoped surfaces.
- [ ] Adapter integration stable.

---

### Phase 5: Validation, Documentation, and Release Readiness

**Duration**: 2-3 days
**Dependencies**: Phase 4 complete
**Assigned Subagent(s)**: testing specialist, web-accessibility-checker, documentation-writer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| VAL-501 | Parity tests | Execute/update parity suite for modal content viewer behavior | All critical scenarios pass | 2 pts | testing specialist | INT-403 |
| VAL-502 | Accessibility verification | Confirm keyboard/ARIA parity for extracted components | No critical a11y findings | 1 pt | web-accessibility-checker | INT-401 |
| VAL-503 | Consumer docs | Add package docs/examples for modal and non-modal usage | Docs reviewed and runnable examples verified | 1 pt | documentation-writer | VAL-501 |
| VAL-504 | Release checklist | Finalize changelog/version and rollout notes | Initial release candidate approved | 1 pt | frontend-developer | VAL-503 |

**Phase 5 Quality Gates:**
- [ ] Functional parity confirmed.
- [ ] Accessibility parity confirmed.
- [ ] Docs and release checklist complete.

---

## Test Strategy

### Required Coverage

- Unit tests for utilities (frontmatter/readme helpers).
- Component tests for `FileTree`, `FrontmatterDisplay`, `ContentPane` states.
- Integration tests for modal Contents flow in SkillMeat.
- Accessibility checks for keyboard navigation and ARIA semantics.

### Critical Parity Scenarios

- No file selected empty state.
- Tree selection and focus navigation.
- Loading and API error states.
- Markdown frontmatter detection/stripping/display.
- Truncated file warnings and links.
- Edit-mode transitions (where enabled).

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Hidden coupling blocks extraction | High | Medium | Adapter-first extraction and strict keep-local list |
| Behavior drift after cutover | High | Medium | Parity test matrix and staging validation |
| Editor dependencies inflate bundle | Medium | Medium | Optional/lazy exports and perf review |
| Prolonged dual implementation | Medium | Low | Time-boxed cleanup in Phase 4 |

---

## Success Criteria

- Scoped content viewer surfaces are package-based in SkillMeat.
- No critical UX/a11y regressions in Artifact Modal Contents workflows.
- Portable APIs are documented for other projects.

---

## Follow-on Link

Umbrella program plan:
- `/docs/project_plans/implementation_plans/refactors/skillmeat-ui-package-extraction-v1.md`
