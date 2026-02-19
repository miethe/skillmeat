---
title: 'Implementation Plan: /manage + /collection Tabs and Filter Bar Unification'
description: Standardize artifact browsing structure across /manage and /collection
  using shared tab and filter-bar components, with an All tab default and consistent
  placement.
status: inferred_complete
complexity: Medium
total_effort: 3-5 days
phases: 5
category: harden-polish
created: 2026-02-10
updated: 2026-02-10
related_specs:
- /docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md
- /docs/project_plans/implementation_plans/harden-polish/collections-groups-ux-enhancement-v1.md
related_request_logs:
- REQ-20260210-skillmeat
---
# Implementation Plan: /manage + /collection Tabs and Filter Bar Unification

## Executive Summary

This plan standardizes the artifact browsing structure on `/manage` and `/collection` by introducing shared UI primitives for:
1. Artifact type tabs (with new `All` first tab, default selected)
2. Search/filter bar layout and behavior
3. Active-filter rendering and placement

Target layout on both pages:
- Search/filter bar
- Active filters line
- Artifact type tabs
- Result count line
- Artifact list/grid content

`/manage` will keep its project-specific filter and status semantics, but render through the same shared bar system used by `/collection`.

## Scope

### In Scope

- Move `/manage` tabs below search/filter bar and active filters line, above result count
- Add `All` tab as first tab, default selected, on `/manage`
- Add same artifact type tabs to `/collection` in the same location (below filter bar, above result count)
- Keep existing `/collection` view modes (grid/list/grouped), and apply tabs consistently across them
- Migrate `/manage` to the same filter-bar component system as `/collection`, with project filter included
- Reduce duplicated page-specific UI logic by extracting shared components
- Fix high-confidence miswirings discovered during planning (tracked in request log)

### Out of Scope

- Full redesign of artifact cards/modals
- Backend API contract changes (except optional query param normalization if needed)
- Large changes to `/projects/[id]/manage` UX (compatibility only)

## Current-State Findings (Captured)

Tracked in request log `REQ-20260210-skillmeat`:
- `REQ-20260210-skillmeat-01`: grouped mode in `/collection` currently falls back to grid
- `REQ-20260210-skillmeat-02`: duplicated `collection-view-mode` localStorage persistence
- `REQ-20260210-skillmeat-03`: `/manage` project filtering can over-match via substring path matching
- `REQ-20260210-skillmeat-04`: `/manage` has duplicated type controls (tabs + filter dropdown)
- `REQ-20260210-skillmeat-05`: GroupedArtifactView exists/tests exist but route integration is bypassed
- `REQ-20260210-skillmeat-06`: `.claude/scripts/batch-file-bugs.sh` create call is incompatible with current meatycapture CLI

## Proposed Technical Design

### 1. Shared Artifact Type Tabs Component

Create a shared component for both pages:
- `skillmeat/web/components/shared/artifact-type-tabs.tsx`

Proposed API:
- `value: 'all' | ArtifactType`
- `onChange: (value: 'all' | ArtifactType) => void`
- `counts?: Partial<Record<'all' | ArtifactType, number>>`
- `className?: string`

Behavior:
- `All` tab shown first and selected by default
- Uses existing artifact type metadata/icons for specific types
- URL contract: missing `type` param means `all`

### 2. Shared Filter Bar System

Extract a shared filter-bar component family from current collection/manage implementations:
- `skillmeat/web/components/shared/artifact-filter-bar.tsx`
- `skillmeat/web/components/shared/active-filter-row.tsx`

The shared bar supports configurable controls:
- Search input
- Filter controls (status/type/scope/platform/project/tags/tools)
- Sort controls (enabled where relevant)
- Clear-all behavior

Page-specific config:
- `/manage`: search, project, status, tags (+ optional type removal from dropdown to avoid duplicate tab control)
- `/collection`: search, status, scope, platform, tags, tools, sort

### 3. URL State Contract Normalization

Standardize type-tab URL behavior:
- `type` absent => `all`
- `type=<artifactType>` => specific type tab

Adjust page state derivation:
- `/manage` currently defaults to `skill`; change to `all`
- `/collection` already supports `all` semantics in filters; align with tabs as primary type selector

### 4. Placement Standardization

On both pages, render in this sequence:
1. Search/filter bar
2. Active filters row
3. Artifact type tabs
4. Result count line
5. Content area

### 5. Compatibility with Project Manage Route

`/projects/[id]/manage` currently consumes `EntityTabs` and `EntityFilters`.
Plan preserves compatibility by either:
- keeping legacy components untouched for project route, or
- migrating project route in a follow-up PR with explicit acceptance tests

This implementation does not change project route UX by default.

## Phase Breakdown

### Phase 1: Shared Component Extraction

Estimated: 0.5-1 day

Tasks:
- Create `artifact-type-tabs.tsx` with `All` support
- Create `artifact-filter-bar.tsx` and `active-filter-row.tsx`
- Define shared filter state interfaces/types (`all`-aware type filter)
- Add stories/tests for shared components

Acceptance criteria:
- Shared tabs render `All` + five artifact types
- Shared filter bar can be configured for manage and collection variants
- Active filters row supports removable chips and clear-all event

### Phase 2: `/manage` Migration

Estimated: 1 day

Tasks:
- Replace `EntityTabs` placement to below filter bar + active filters line
- Default type state to `all` (not `skill`)
- Ensure `All` is first tab and selected by default
- Remove duplicated type control from manage filter dropdown (or make it hidden when tabs enabled)
- Keep project filter in shared filter bar config

Acceptance criteria:
- `/manage` layout order matches target sequence
- New `All` tab present and default active
- Filtering behavior remains correct for status/project/tags/search
- No regressions in add dialog type handling (`AddEntityDialog` remains valid with `all`)

### Phase 3: `/collection` Tabs Integration

Estimated: 1 day

Tasks:
- Add shared artifact type tabs below filter bar and above result count
- Wire tab changes to existing URL type filter
- Ensure tabs apply to grid/list/grouped modes consistently
- Keep existing view mode controls (grid/list/grouped)

Acceptance criteria:
- Tabs appear in target location on `/collection`
- Selecting tabs filters artifacts consistently regardless of view mode
- URL deep linking works with `type` query param
- Result count reflects tab-filtered output

### Phase 4: Miswiring Cleanup (From Findings)

Estimated: 0.5-1 day

Tasks:
- Resolve grouped-mode placeholder mismatch
  - Either wire `GroupedArtifactView` in page or hide grouped option until ready
- Remove duplicate localStorage writes for `collection-view-mode`
- Normalize `/manage` project matching to exact normalized key match (avoid substring over-match)

Acceptance criteria:
- No selectable view mode routes to placeholder behavior
- Single source of truth for collection view-mode persistence
- Project filter results are deterministic and exact-match safe

### Phase 5: Tests, QA, and Rollout

Estimated: 1-2 days

Tasks:
- Update/manage component tests for new tab default and layout
- Add `/collection` tests for tabs + view mode combinations
- Add regression tests for URL state transitions and back/forward navigation
- Manual QA pass across desktop/mobile

Acceptance criteria:
- Updated unit/integration tests pass
- Key manual flows pass
- No visual regressions in `/manage` and `/collection`

## File-Level Change Plan

Core files expected to change:
- `skillmeat/web/app/manage/page.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/web/components/collection/collection-toolbar.tsx`
- `skillmeat/web/components/manage/manage-page-filters.tsx`
- `skillmeat/web/app/manage/components/entity-tabs.tsx` (or replaced usage)

New shared components:
- `skillmeat/web/components/shared/artifact-type-tabs.tsx`
- `skillmeat/web/components/shared/artifact-filter-bar.tsx`
- `skillmeat/web/components/shared/active-filter-row.tsx`

Potential test updates:
- `skillmeat/web/__tests__/components/manage/manage-page-filters.test.tsx`
- `skillmeat/web/__tests__/integration/entity-lifecycle-flows.test.tsx`
- New tests for `/collection` tab + layout behavior (component or integration)

## Risks and Mitigations

- Risk: type-filter logic divergence between tabs and dropdown
  - Mitigation: single source of truth (`type` URL param), hide duplicate type dropdown where tabs exist
- Risk: project manage route regressions via shared component refactor
  - Mitigation: preserve legacy wrapper compatibility in this scope
- Risk: filtered counts become inconsistent with pagination totals
  - Mitigation: define and test count semantics explicitly per page

## QA Matrix

Critical checks:
- `/manage` loads with `All` tab selected on first visit
- `/manage` tabs appear below active filters row, above count
- `/collection` tabs appear below filter bar, above “Showing x of y...” line
- `/collection` tab filtering works in grid/list/grouped modes
- URL navigation/back-forward preserves type/filter state
- Project filter on `/manage` does exact expected matching

## Delivery Notes

- Plan intentionally prioritizes shared-component extraction before page migration to minimize duplicated business logic.
- Miswiring cleanup from `REQ-20260210-skillmeat` is included as part of the same delivery to avoid carrying known debt into the standardized UI.
