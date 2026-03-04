---
title: 'PRD: Artifact Modal Content Viewer Extraction (Initial Slice)'
description: Extract and package the artifact modal content viewer panes as reusable, backend-agnostic components while keeping SkillMeat behavior unchanged.
audience:
- ai-agents
- developers
- architects
tags:
- prd
- planning
- refactor
- ui
- content-viewer
- artifact-modal
created: 2026-03-04
updated: 2026-03-04
category: product-planning
status: draft
related:
- /docs/project_plans/PRDs/refactors/skillmeat-ui-package-extraction-v1.md
- /.claude/analysis/CONTENT-VIEWER-README.md
- /.claude/analysis/content-viewing-extraction-inventory.md
- /.claude/analysis/content-viewer-quick-ref.md
- /.claude/analysis/content-viewer-extraction-report.md
schema_version: 2
doc_type: prd
feature_slug: artifact-modal-content-viewer-extraction
feature_version: v1
---
# PRD: Artifact Modal Content Viewer Extraction (Initial Slice)

**Feature Name:** Artifact Modal Content Viewer Extraction

**Filepath Name:** `artifact-modal-content-viewer-extraction-v1`

**Date:** 2026-03-04

**Author:** Codex (GPT-5)

**Version:** 1.0

**Status:** Planned

**Priority:** HIGH

**Scope:** Initial extraction phase focused on content viewer panes used by the Artifact Modal Contents experience.

---

## 1. Executive Summary

This PRD defines the first deliverable of the UI package initiative: extracting the artifact modal content viewer panes into reusable components that work in SkillMeat and other projects. The extraction prioritizes high-readiness units from the analysis set while introducing adapter boundaries so data-fetching remains app-specific.

**Key Outcomes:**
- Portable content viewer module shipped in new UI package.
- SkillMeat Contents tab re-integrated via package imports with no behavioral changes.
- Component APIs support both modal and non-modal usage contexts.

---

## 2. Context & Background

### Current State

Analysis documents identify the content viewer stack as the strongest extraction starting point:

- High-readiness units (Tier 1): `FileTree`, `FrontmatterDisplay`, frontmatter/readme utilities, catalog file hooks pattern, generic file response types.
- Additional viewer-pane candidates from extraction report: `ContentPane`, `SplitPreview`, `MarkdownEditor` with limited adaptation.
- Domain-coupled logic (`tree-filter-utils`, `folder-filter-utils`, detection patterns, marketplace enums) should remain in SkillMeat.

### Problem Space

- Current component placement blocks reuse outside SkillMeat.
- Data-fetching hooks embed app-specific API paths.
- Viewer panes are not currently published with stable contracts.

### Current Alternatives / Workarounds

- Copying content viewer components into other projects.
- Rebuilding similar viewers from scratch.

These approaches duplicate effort and diverge behavior.

---

## 3. Problem Statement

SkillMeat needs a low-risk first extraction slice that proves package portability without destabilizing the modal experience.

**User Story:**
> As a developer reusing SkillMeat UI patterns, when I need file/content viewing panes, I want to import and compose them from a package instead of copying internal app files.

**Technical Root Cause:**
- No package-level viewer exports.
- Tight coupling between some hooks and SkillMeat-specific API routes.

---

## 4. Goals & Success Metrics

### Primary Goals

**Goal 1: Deliver Portable Content Viewer Module**
- Move approved viewer components and utilities behind a public package API.

**Goal 2: Preserve Existing UX and Behavior**
- Keep SkillMeat Contents tab behavior unchanged post-migration.

**Goal 3: Establish Adapter Contract for Data Fetching**
- Decouple generic viewer rendering from marketplace-specific data acquisition.

### Success Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Extracted content-viewer units in package | 0 | All v1 scoped units exported | Export map + checklist |
| Regression count in Artifact Modal Contents tab | Unknown | 0 P0/P1 regressions | Automated tests + manual QA |
| Package API coverage for modal/non-modal embedding | None | 100% of scoped components documented with examples | README + story/examples audit |
| Domain-coupled code moved into package | Mixed | 0 domain-only utilities in package | Architectural review against scope table |

---

## 5. User Personas & Journeys

**Primary Persona: SkillMeat Web Engineer**
- Needs: Extract and consume without changing user-facing behavior.
- Pain Point: Coupled import graph and risky migration.

**Secondary Persona: External Consumer Project Engineer**
- Needs: Content viewer UI primitives independent of SkillMeat APIs.
- Pain Point: No portable module available.

---

## 6. Requirements

### 6.1 Functional Requirements

| ID | Requirement | Priority | Notes |
| :-: | ----------- | :------: | ----- |
| CV-1 | Create content-viewer module in new UI package | Must | Includes package exports and typing |
| CV-2 | Extract `FileTree` and `FrontmatterDisplay` as reusable components | Must | Preserve keyboard and ARIA behavior |
| CV-3 | Extract frontmatter/readme utility functions | Must | Keep generic implementation |
| CV-4 | Extract `ContentPane`, `SplitPreview`, and `MarkdownEditor` with portable props | Should | Ensure non-modal embeddability |
| CV-5 | Convert data-fetching to adapter-based or injectable fetcher pattern | Must | No hard-coded SkillMeat routes in generic layer |
| CV-6 | Keep domain-specific filtering/types/hooks in SkillMeat app | Must | No marketplace-specific leakage into package |
| CV-7 | Reintegrate SkillMeat Contents tab to consume package exports | Must | Import migration complete |
| CV-8 | Provide migration + consumer documentation | Should | Include minimal integration examples |

### 6.2 Non-Functional Requirements

**Performance:**
- No material degradation in file tree and content pane interaction times.

**Accessibility:**
- Preserve keyboard navigation and ARIA semantics for tree/collapsible controls.

**Reliability:**
- Extraction must include rollback-safe integration path.

**Maintainability:**
- Public API intentionally narrow and semantically versioned.

---

## 7. Scope

### In Scope

- Contents tab viewer surfaces and their reusable support logic.
- Initial UI package scaffolding required to host this module.
- SkillMeat re-integration for this slice.

### Out of Scope

- Extraction of non-content modal tabs (Sources, Deployments, Sync, Links, History, Collections).
- Marketplace-specific filtering and detection configuration logic.
- Backend endpoint changes.

---

## 8. Dependencies & Assumptions

### Dependencies

- `.claude/analysis/content-viewing-extraction-inventory.md`
- `.claude/analysis/content-viewer-quick-ref.md`
- Existing Contents tab wiring in `skillmeat/web/components/entity/unified-entity-modal.tsx`

### Assumptions

- Package scaffold from umbrella initiative is available.
- SkillMeat remains the first consumer and parity baseline.
- CodeMirror-heavy editor paths may be optional/lazy as needed.

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
| ---- | :----: | :--------: | ---------- |
| API over-generalization delays delivery | Medium | Medium | Start from current props and minimally generalize |
| Hidden coupling discovered mid-migration | High | Medium | Adapter layer + explicit keep-local list |
| Tree navigation a11y regressions | High | Low | Focused keyboard/a11y test suite before cutover |
| Bundle growth from editor dependencies | Medium | Medium | Optional exports and lazy-loading strategy |

---

## 10. Target State (Post-Implementation)

- `artifact-modal` Contents UI in SkillMeat is powered by package exports.
- Portable content viewer components can be dropped into other projects with adapter-supplied data.
- Domain-specific marketplace concerns remain local to SkillMeat.

---

## 11. Overall Acceptance Criteria (Definition of Done)

- [ ] Scoped content viewer components/utilities are extracted and exported.
- [ ] SkillMeat imports switched for the scoped Contents tab surfaces.
- [ ] Tests confirm no critical behavior/accessibility regressions.
- [ ] Consumer documentation exists for modal and non-modal composition.
- [ ] Domain-coupled utilities remain in SkillMeat and are not reintroduced into package core.

---

## 12. Implementation Link

Implementation plan:
- `/docs/project_plans/implementation_plans/refactors/artifact-modal-content-viewer-extraction-v1.md`
