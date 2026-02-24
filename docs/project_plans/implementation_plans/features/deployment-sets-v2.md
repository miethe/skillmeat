---
title: "Implementation Plan: Deployment Sets v2 \u2014 UI Enhancement"
schema_version: 2
doc_type: implementation_plan
status: in-progress
created: 2026-02-24
updated: '2026-02-24'
feature_slug: deployment-sets
feature_version: v2
prd_ref: null
plan_ref: null
scope: "Frontend-only UI enhancement \u2014 clickable set cards, modal-based detail\
  \ view with tabbed layout, ArtifactBrowseCard variant for members, and redesigned\
  \ AddMemberDialog with MiniArtifactCard grid and filtering."
effort_estimate: 14 pts
architecture_summary: "Pure frontend refactor: DeploymentSetCard becomes full-card-click\
  \ \u2192 new DeploymentSetDetailsModal (Overview + Members tabs) replaces dedicated\
  \ detail page \u2192 DeploymentSetMemberCard (ArtifactBrowseCard variant, actions\
  \ stripped) renders in Members tab \u2192 AddMemberDialog upgraded with MiniArtifactCard\
  \ grid + type/search filters."
related_documents:
- docs/project_plans/implementation_plans/features/deployment-sets-v1.md
- docs/project_plans/design-specs/ui-component-specs-page-refactor.md
- skillmeat/web/components/deployment-sets/deployment-set-card.tsx
- skillmeat/web/components/deployment-sets/add-member-dialog.tsx
- skillmeat/web/components/collection/artifact-details-modal.tsx
- skillmeat/web/components/collection/artifact-browse-card.tsx
- skillmeat/web/components/collection/mini-artifact-card.tsx
- skillmeat/web/types/deployment-sets.ts
- skillmeat/web/hooks/deployment-sets.ts
owner: null
contributors: []
priority: medium
risk_level: low
category: product-planning
tags:
- implementation
- planning
- deployment-sets
- ui-enhancement
- modal
- frontend
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/web/components/deployment-sets/deployment-set-card.tsx
- skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx
- skillmeat/web/components/deployment-sets/deployment-set-member-card.tsx
- skillmeat/web/components/deployment-sets/add-member-dialog.tsx
- skillmeat/web/components/deployment-sets/deployment-set-list.tsx
- skillmeat/web/app/deployment-sets/[id]/page.tsx
- skillmeat/web/app/deployment-sets/[id]/deployment-set-detail-client.tsx
- skillmeat/web/app/deployment-sets/deployment-sets-page-client.tsx
---

# Implementation Plan: Deployment Sets v2 — UI Enhancement

**Plan ID**: `IMPL-2026-02-24-DEPLOYMENT-SETS-V2`
**Date**: 2026-02-24
**Author**: Implementation Planner (Sonnet 4.6)
**Related Documents**:
- **V1 Plan**: `docs/project_plans/implementation_plans/features/deployment-sets-v1.md`
- **UI Spec**: `docs/project_plans/design-specs/ui-component-specs-page-refactor.md`
- **ArtifactDetailsModal**: `skillmeat/web/components/collection/artifact-details-modal.tsx`
- **ArtifactBrowseCard**: `skillmeat/web/components/collection/artifact-browse-card.tsx`

**Complexity**: Medium
**Total Estimated Effort**: 14 pts
**Target Timeline**: 1.5–2 weeks

---

## Executive Summary

Deployment Sets v2 is a frontend-only polish pass that replaces the dedicated detail page with an inline modal (matching the ArtifactDetailsModal pattern), makes set cards fully clickable, introduces a `DeploymentSetMemberCard` variant of ArtifactBrowseCard for the Members tab, and upgrades the AddMemberDialog with a MiniArtifactCard grid and type/search filters. No backend or API changes are required — all v1 endpoints are sufficient.

---

## Implementation Strategy

### Architecture Sequence

This is a pure UI layer change. The sequence follows shadcn/Radix component composition:

1. **Phase 1 — Modal Infrastructure**: Build `DeploymentSetDetailsModal`, wire Overview tab, make `DeploymentSetCard` fully clickable, deprecate detail page.
2. **Phase 2 — Members Tab + Card Variant**: Build `DeploymentSetMemberCard`, implement Members tab with per-artifact navigation to `ArtifactDetailsModal`.
3. **Phase 3 — AddMemberDialog Redesign**: Upgrade picker dialog with `MiniArtifactCard` grid, type filter, and search input.

### Parallel Work Opportunities

- Phase 2 (DeploymentSetMemberCard) and Phase 3 (AddMemberDialog) are independent after Phase 1 completes and can run in parallel.
- Within Phase 1, card clickability (`deployment-set-card.tsx`) and modal shell (`deployment-set-details-modal.tsx`) can be written concurrently by two agents.

### Critical Path

```
DSv2-001 (modal shell)
  → DSv2-003 (Overview tab)
  → DSv2-004 (Members tab shell)
    → DSv2-005 (member card)
    → DSv2-006 (member card ArtifactDetailsModal link)
DSv2-002 (card clickability) — can parallel DSv2-001
DSv2-007 (AddMemberDialog) — after Phase 1
```

---

## Phase Breakdown

### Phase 1: Modal Infrastructure

**Duration**: 3–4 days
**Dependencies**: None (v1 complete)
**Assigned Subagent(s)**: `ui-engineer-enhanced` (modal + tabs), `frontend-developer` (card wiring + page deprecation)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DSv2-001 | DeploymentSetDetailsModal shell | Create `deployment-set-details-modal.tsx` following `ArtifactDetailsModal` tabbed dialog pattern. Dialog accepts `setId: string` prop, fetches set via `useDeploymentSet(setId)` hook, renders shadcn `Dialog` with `Tabs` (Overview, Members). | Modal opens/closes correctly; tabs switch; set data loads; loading/error states handled. | 3 pts | ui-engineer-enhanced | None |
| DSv2-002 | Clickable DeploymentSetCard | Refactor `deployment-set-card.tsx` so the entire card surface is the click target (like `ArtifactBrowseCard`). Remove dedicated "Open" button. Card `onClick` prop triggers `onOpen(set.id)`. Keep existing action menu (Edit, Clone, Delete, Deploy). | Full card is clickable; action menu still works; keyboard navigation correct; no visual regression. | 1 pt | frontend-developer | None |
| DSv2-003 | Overview tab content | Implement the Overview tab inside `DeploymentSetDetailsModal`. Display: name, description, color swatch, icon, tags list, resolved member count, created/updated dates. Use shadcn `Badge`, `Separator`, and existing Tailwind layout tokens. | All metadata fields render; color/icon display correctly; dates formatted consistently with rest of app. | 2 pts | ui-engineer-enhanced | DSv2-001 |
| DSv2-004 | Wire modal into list page + deprecate detail page | In `deployment-sets-page-client.tsx`, add `DeploymentSetDetailsModal` state (`selectedSetId`). Pass `onOpen` to `DeploymentSetList` → `DeploymentSetCard`. Mark `app/deployment-sets/[id]/` route as deprecated (add redirect to list page or remove). | Clicking a card in the catalog opens the modal; direct navigation to `[id]` redirects to `/deployment-sets`; no broken links. | 1 pt | frontend-developer | DSv2-001, DSv2-002 |

**Phase 1 Quality Gates:**
- [ ] Modal opens with correct set data on card click
- [ ] Overview tab renders all metadata without errors
- [ ] Action menu (Edit, Clone, Delete, Deploy) still functions from card
- [ ] Dedicated `[id]` page gracefully redirects or is removed
- [ ] No TypeScript errors introduced

---

### Phase 2: Members Tab + Card Variant

**Duration**: 2–3 days
**Dependencies**: Phase 1 complete (DSv2-001)
**Assigned Subagent(s)**: `ui-engineer-enhanced`

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DSv2-005 | DeploymentSetMemberCard component | Create `deployment-set-member-card.tsx`. For `Artifact` members: adapt `ArtifactBrowseCard` — keep type border, name, description, tags; strip action dropdown (no quick-deploy, manage, etc.); add member position badge (e.g., "#1") and member type badge ("Artifact" / "Group" / "Set") in top-right. For Group/Set members: render a simpler summary card showing name, type icon, member count, and description. Props: `member: DeploymentSetMember & { resolvedArtifact?: Artifact }`, `onClick`, `className?`. | Artifact members match ArtifactBrowseCard visual style minus actions; position + type badges visible; Group/Set members show summary card; all cards are accessible (role=button, keyboard). | 3 pts | ui-engineer-enhanced | DSv2-001 |
| DSv2-006 | Members tab with navigation | Implement Members tab inside modal: render a responsive grid of `DeploymentSetMemberCard` using `useDeploymentSetMembers(setId)`. Artifact cards open `ArtifactDetailsModal` on click. Group cards show a simple info popover. Set cards trigger nested `DeploymentSetDetailsModal`. Show loading skeleton and empty state. | Members grid renders with correct data; clicking an Artifact card opens `ArtifactDetailsModal` for that artifact; empty state shown when no members; loading skeleton visible during fetch. | 2 pts | ui-engineer-enhanced | DSv2-005 |

**Phase 2 Quality Gates:**
- [ ] `DeploymentSetMemberCard` renders all three member types (Artifact, Group, Set) without errors
- [ ] Position badge and type badge display correctly on each card
- [ ] Clicking an Artifact member opens `ArtifactDetailsModal` for the correct artifact
- [ ] Empty state renders when set has no members
- [ ] TypeScript strict-mode passes on new component

---

### Phase 3: AddMemberDialog Redesign

**Duration**: 2–3 days
**Dependencies**: Phase 1 complete (modal infrastructure established); independent of Phase 2
**Assigned Subagent(s)**: `ui-engineer-enhanced`

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| DSv2-007 | AddMemberDialog with MiniArtifactCard grid + filters | Redesign `add-member-dialog.tsx`. Replace current list UI with a responsive multi-column grid using `MiniArtifactCard` (from `collection/mini-artifact-card.tsx`). Keep the 3 existing tabs (Artifact / Group / Set). Add: (1) Search `Input` component that filters displayed items by name; (2) Artifact type filter `ToggleGroup` (Skills, Commands, Agents, MCP Servers, Hooks) — only shown on Artifact tab; (3) Dialog width expands to accommodate grid (e.g., `max-w-3xl`). Selected items show a checkmark overlay. Confirm button adds selections. | Search filters results in real-time; type filter toggles are functional; grid shows 3–4 columns at default dialog width; selected cards show visual checkmark; existing add-member logic (position, type) unchanged; tests pass. | 3 pts | ui-engineer-enhanced | DSv2-001 |

**Phase 3 Quality Gates:**
- [ ] Search input filters all tabs in real-time
- [ ] Artifact type filter works on Artifact tab, hidden on Group/Set tabs
- [ ] Grid renders `MiniArtifactCard` for each item correctly
- [ ] Selection state (checkmark) is visually clear
- [ ] Existing add-member functionality (API calls, hook integration) unchanged
- [ ] No regressions to existing 3-tab structure

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ArtifactBrowseCard is 735 lines — stripping actions for member card may be complex | Medium | Medium | Create `DeploymentSetMemberCard` as a new component that borrows visual tokens (type border color, tag layout) rather than forking ArtifactBrowseCard directly |
| MiniArtifactCard drag-and-drop props may conflict with dialog selection mode | Low | Low | Pass `draggable={false}` or equivalent; review component props before implementation |
| Nested modal (Set member opens DeploymentSetDetailsModal) causes z-index or focus-trap issues | Medium | Low | Use Radix Dialog's built-in focus management; nest portals correctly; test keyboard navigation |
| Deprecating `[id]` page may break existing bookmarks or direct links | Low | Low | Add Next.js redirect from `[id]` to `/deployment-sets` before removing the page |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Phase 2 + Phase 3 parallelization requires coordinated context | Low | Low | Both are self-contained components; Phase 1 artifacts (modal, hooks wiring) are the only shared dependency |
| ArtifactDetailsModal integration in Phase 2 requires understanding its props | Low | Medium | Agent reads `artifact-details-modal.tsx` before implementing; all hooks already exist from v1 |

---

## Parallelization Strategy

```
Phase 1 (sequential within phase, two agents in parallel):
  Agent A (ui-engineer-enhanced): DSv2-001, DSv2-003
  Agent B (frontend-developer):   DSv2-002, DSv2-004

Phase 2 + Phase 3 (parallel after Phase 1):
  Agent A (ui-engineer-enhanced): DSv2-005, DSv2-006
  Agent B (ui-engineer-enhanced): DSv2-007
```

Total parallelized timeline: ~7–8 working days across three agent streams.

---

## Files to Create

| File | Purpose |
|------|---------|
| `skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx` | New modal component (replaces detail page) |
| `skillmeat/web/components/deployment-sets/deployment-set-member-card.tsx` | ArtifactBrowseCard variant for members |

## Files to Modify

| File | Change |
|------|--------|
| `skillmeat/web/components/deployment-sets/deployment-set-card.tsx` | Full-card click, remove dedicated open button |
| `skillmeat/web/components/deployment-sets/add-member-dialog.tsx` | MiniArtifactCard grid + search/type filters |
| `skillmeat/web/components/deployment-sets/deployment-set-list.tsx` | Thread `onOpen` prop through to card |
| `skillmeat/web/app/deployment-sets/deployment-sets-page-client.tsx` | Add modal state, wire `onOpen` |

## Files to Deprecate / Remove

| File | Action |
|------|--------|
| `skillmeat/web/app/deployment-sets/[id]/page.tsx` | Add redirect or delete |
| `skillmeat/web/app/deployment-sets/[id]/deployment-set-detail-client.tsx` | Delete after redirect confirmed |

---

## Success Metrics

- All set cards open the modal on full-card click
- Detail page route redirects cleanly (no 404)
- Members tab displays all member types with correct badges
- Artifact members link to `ArtifactDetailsModal`
- AddMemberDialog search + filter functional with no regression to existing add behavior
- Zero new TypeScript errors; all existing tests continue to pass

---

**Progress Tracking**: `.claude/progress/deployment-sets-v2/`

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-24
