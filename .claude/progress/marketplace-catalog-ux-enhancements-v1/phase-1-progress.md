---
name: marketplace-catalog-ux-enhancements-v1
phase: 1
title: Pagination & Count Indicator
status: completed
completion: 0%
created: 2026-01-08
updated: '2026-01-08'
prd_reference: docs/project_plans/implementation_plans/enhancements/marketplace-catalog-ux-enhancements-v1.md
estimated_effort: 9 story points
timeline: 3 days
gate_owner: ui-engineer-enhanced
approval_required: Code review by Opus (UX consistency check)
parallelization:
  batch_1:
    description: Visual separation & count integration (no internal deps)
    tasks:
    - TASK-1.1
    - TASK-1.3
    - TASK-1.4
    runs_in_parallel: true
  batch_2:
    description: Traditional pagination UI (depends on TASK-1.1)
    tasks:
    - TASK-1.2
    runs_in_parallel: false
  batch_3:
    description: Testing (depends on TASK-1.2, TASK-1.3)
    tasks:
    - TASK-1.5
    runs_in_parallel: false
tasks:
- id: TASK-1.1
  description: Add pagination bar visual separation
  details: 'Pagination area needs shadow (elevation: 1-2), thin border (1px), or glassmorphic
    effect

    matching title bar. Must work on both light and dark mode.

    '
  acceptance_criteria:
  - Pagination bar has visual distinction (shadow/border/glassmorphism)
  - Styling applies correctly in light mode
  - Styling applies correctly in dark mode
  - Matches visual design of existing title bar
  assigned_to: ui-engineer
  estimate: 1d (3 pts)
  dependencies: []
  status: completed
  completed_date: null
  notes: null
- id: TASK-1.2
  description: Implement traditional pagination UI
  details: 'Replace infinite scroll "Load More" button with numbered pagination UI:

    numbered pages (1-5+), Next/Previous buttons, items per page selector (10/25/50/100).

    Persist page and limit in URL query params.

    '
  acceptance_criteria:
  - Numbered pages rendered (1-5+)
  - Next/Previous buttons functional
  - Items per page selector shows 10/25/50/100 options
  - Page state persists in URL query params
  - Current page indicator shows active page
  - Load More button removed
  assigned_to: ui-engineer-enhanced
  estimate: 1.5d (5 pts)
  dependencies:
  - TASK-1.1
  status: completed
  completed_date: null
  notes: null
- id: TASK-1.3
  description: Add artifact count indicator
  details: 'Add "Showing X of Y artifacts" text above artifact list.

    X = count of matching entries (post-filter), Y = total available in catalog.

    Updates dynamically when filters or search changes.

    '
  acceptance_criteria:
  - Count indicator displays above artifact list
  - Shows 'Showing X of Y artifacts' format
  - X reflects post-filter count
  - Y reflects total in source
  - Updates when filters change
  - Updates when search term changes
  assigned_to: ui-engineer
  estimate: 0.5d (2 pts)
  dependencies: []
  status: completed
  completed_date: null
  notes: null
- id: TASK-1.4
  description: Wire count totals from hook
  details: 'Extract total_count from useSourceCatalog hook''s first page response.

    Pass count values to count indicator component for display.

    '
  acceptance_criteria:
  - useSourceCatalog hook returns total_count in first page response
  - Count values extracted correctly
  - Count indicator receives and displays values
  - No race conditions with filter changes
  assigned_to: ui-engineer
  estimate: 0.5d (1 pt)
  dependencies:
  - TASK-1.3
  status: completed
  completed_date: null
  notes: null
- id: TASK-1.5
  description: Unit and E2E tests for pagination
  details: 'Comprehensive testing for pagination workflow and count indicator accuracy.

    Test page navigation, items per page selector, count accuracy with filters,

    and URL state persistence. Target >80% coverage.

    '
  acceptance_criteria:
  - Page navigation tests pass (next/previous/numbered pages)
  - Items per page selector tests pass (10/25/50/100)
  - Count accuracy tested with all filter combinations (type, status, confidence,
    search)
  - URL persistence tests pass (page and limit params)
  - E2E test validates full pagination workflow
  - Code coverage >80%
  - No console errors or warnings
  assigned_to: ui-engineer
  estimate: 0.5d (2 pts)
  dependencies:
  - TASK-1.2
  - TASK-1.3
  status: completed
  completed_date: null
  notes: null
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 1 Progress: Pagination & Count Indicator

**Status**: In Progress | **Completion**: 0%
**Effort**: 9 story points | **Timeline**: 3 days
**Gate Owner**: ui-engineer-enhanced

## Overview

Phase 1 improves pagination visibility and adds artifact count indicator to the marketplace source catalog page. The changes make pagination more discoverable and provide clearer feedback on artifact availability.

### Key Deliverables

- Visual separation for pagination bar (shadow/border/glassmorphism)
- Traditional pagination UI (numbered pages, Next/Previous, items per page selector)
- "Showing X of Y artifacts" indicator above artifact list
- Comprehensive unit and E2E tests for pagination workflow

### Success Metrics

- Pagination bar clearly distinguished from white background with maintained visual contrast
- Load More button replaced with numbered pagination
- Artifact count always visible and accurate with filters applied
- Pagination state persists in URL query params
- All new code covered >80% by tests

---

## Task Status

### Batch 1: Visual Separation & Count Integration (Parallel)

- [ ] **TASK-1.1** (ui-engineer, 1d/3pts): Add pagination bar visual separation
  - Status: Pending
  - Dependencies: None

- [ ] **TASK-1.3** (ui-engineer, 0.5d/2pts): Add artifact count indicator
  - Status: Pending
  - Dependencies: None

- [ ] **TASK-1.4** (ui-engineer, 0.5d/1pt): Wire count totals from hook
  - Status: Pending
  - Dependencies: TASK-1.3

### Batch 2: Traditional Pagination UI (Sequential)

- [ ] **TASK-1.2** (ui-engineer-enhanced, 1.5d/5pts): Implement traditional pagination UI
  - Status: Pending
  - Dependencies: TASK-1.1

### Batch 3: Testing (Sequential)

- [ ] **TASK-1.5** (ui-engineer, 0.5d/2pts): Unit and E2E tests for pagination
  - Status: Pending
  - Dependencies: TASK-1.2, TASK-1.3

---

## Completed Tasks

None yet.

---

## In Progress

None yet.

---

## Blocked Tasks

None.

---

## Next Actions

1. **Start Batch 1 (Parallel Execution)**:
   - Assign TASK-1.1 to ui-engineer → Add pagination bar styling
   - Assign TASK-1.3 to ui-engineer → Add count indicator component
   - Assign TASK-1.4 to ui-engineer → Wire count data from hook

2. **Prepare for Batch 2**:
   - Review TASK-1.1 results for styling foundation
   - Coordinate with ui-engineer-enhanced on pagination UI requirements

3. **Prepare for Batch 3**:
   - Define test scope after Batch 2 completes
   - Set up test environment and fixtures

---

## Context for AI Agents

### Phase 1 Scope

This phase focuses on **two independent features**:

1. **Pagination Styling & UI** (TASK-1.1, TASK-1.2)
   - File: `skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx`
   - Add visual separation to pagination bar (shadow/border/glassmorphism)
   - Replace infinite scroll "Load More" with traditional pagination UI
   - Numbered pages (1-5+), Next/Previous buttons, items per page selector (10/25/50/100)
   - Persist page/limit in URL query params using Next.js `useSearchParams`

2. **Count Indicator** (TASK-1.3, TASK-1.4)
   - File: `skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx`
   - Add "Showing X of Y artifacts" text above artifact list
   - X = post-filter count, Y = total available in catalog
   - Wire data from `useSourceCatalog` hook (get total_count from first page response)
   - Update when filters or search changes

### Key Files to Modify

- **Frontend**:
  - `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Page component
  - `skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx` - List component (main changes)
  - `skillmeat/web/hooks/useMarketplaceSources.ts` - Hook for catalog data

- **Backend** (if needed):
  - `skillmeat/api/routers/marketplace_sources.py` - API endpoint (verify total_count in response)

### Hook Contract

The `useSourceCatalog` hook should return:
```typescript
{
  artifacts: Artifact[];
  total_count: number;  // Total in source (for Y in "Showing X of Y")
  page: number;
  limit: number;
  // ... other fields
}
```

### Styling References

- Light/dark mode support required (check existing Radix UI patterns in sidebar/header)
- Shadow/border/glassmorphism options for pagination bar elevation
- Review existing title bar styling for consistency

### Testing Notes

- Test all filter combinations: type, status, confidence, search
- Verify URL state persistence across navigation
- Check responsive behavior (375px+ mobile screens)
- Mock API responses for unit tests
- E2E test full workflow: paginate → change items per page → apply filter → verify counts

---

## Risk Tracking

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Count indicator shows stale data | Medium | Medium | Invalidate useSourceCatalog on filter change; add refetch trigger |
| Pagination state not persisting | Medium | Low | Use Next.js useSearchParams consistently; tested in E2E |
| Layout breaks on small screens | Low | Medium | Test responsive on 375px+; use Radix responsive helpers |

---

## Quality Gate Requirements

Before marking Phase 1 complete, all of the following must be satisfied:

- [ ] Pagination bar renders with visual distinction in light mode
- [ ] Pagination bar renders with visual distinction in dark mode
- [ ] Visual distinction matches or complements existing title bar design
- [ ] Traditional pagination UI functional: page nav works
- [ ] Items per page selector works (10/25/50/100)
- [ ] URL state persists correctly (page and limit params)
- [ ] Count indicator displays correctly above list
- [ ] Count indicator updates with filter changes
- [ ] Count indicator updates with search changes
- [ ] Count accuracy tested with all filter combinations
- [ ] E2E test passes: user navigates pages, changes items per page, applies filters
- [ ] No console errors or warnings (TypeScript, ESLint clean)
- [ ] Code coverage >80%

**Gate Owner**: ui-engineer-enhanced
**Approval Required**: Code review by Opus (UX consistency check)

---

## Notes

- Phase 1 has no dependencies on Phase 2 or other PRDs
- Parallelization strategy allows Batch 1 tasks to run simultaneously (visual + count)
- Batch 2 depends on TASK-1.1 styling foundation (sequential)
- Batch 3 depends on Batch 2 completion (sequential)
- All tasks assignable to qualified agents immediately
