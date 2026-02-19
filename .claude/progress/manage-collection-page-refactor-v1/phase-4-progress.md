---
phase: 4
phase_name: Filter Components
prd: manage-collection-page-refactor-v1
status: completed
estimated_hours: 2-4
created_at: 2026-02-02
updated_at: 2026-02-02
parallelization:
  batch_1:
    tasks:
    - FILTER-4.1
    - FILTER-4.2
    rationale: ManagePageFilters and CollectionPageFilters tools enhancement can run
      in parallel
    can_parallelize: true
  batch_2:
    tasks:
    - FILTER-4.3
    rationale: URL state persistence depends on both filter components being complete
tasks:
- id: FILTER-4.1
  name: Create ManagePageFilters component
  description: Project dropdown (prominent), Status filter (All, Needs Update, Has
    Drift, Deployed, Error), Type filter, search input, optional tag filter (retained)
  estimated_hours: 1.5
  assigned_to:
  - ui-engineer-enhanced
  status: completed
  batch: 1
  depends_on: []
  acceptance_criteria:
  - All filters render correctly
  - Project dropdown populated from available projects
  - Status options functional (All, Needs Update, Has Drift, Deployed, Error)
  - Type filtering works
  - Search input functional
  - Tag filter optional and non-blocking
  - Active filters display with clear chips
  notes: Completed - created skillmeat/web/components/manage/manage-page-filters.tsx
- id: FILTER-4.2
  name: Enhance CollectionPageFilters with tools filter
  description: Add Tools multi-select popover to existing filters (Collection, Group,
    Type, Tags, Search). Tools API PRD must be complete.
  estimated_hours: 1
  assigned_to:
  - ui-engineer-enhanced
  status: completed
  batch: 1
  depends_on: []
  acceptance_criteria:
  - Tools filter popover opens correctly
  - Tools list populated from API or artifact metadata
  - Multi-select works properly
  - Selected tools show in active filters
  - Clear all works for tools filter
  - Responsive on mobile
  notes: Completed - integrated ToolFilterPopover into collection-toolbar.tsx and
    collection/page.tsx
- id: FILTER-4.3
  name: Add filter state to URL for bookmarkability
  description: Serialize filter state to query params, restore on page load, update
    on filter change (including collection/group selection)
  estimated_hours: 1.5
  assigned_to:
  - frontend-developer
  status: completed
  batch: 2
  depends_on:
  - FILTER-4.1
  - FILTER-4.2
  acceptance_criteria:
  - URL updates on filter change
  - Filters restore from URL on page load
  - Back button works correctly
  - Bookmarkable URLs work
  - No race conditions between filters and URL
  - Deep links work with artifacts and filters combined
  notes: ''
total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
progress: 0
updated: '2026-02-02'
schema_version: 2
doc_type: progress
feature_slug: manage-collection-page-refactor-v1
type: progress
---

# Phase 4: Filter Components

## Objective

Implement purpose-specific filters that guide users toward relevant features on each page. ManagePageFilters focuses on operations (project, status, health), while CollectionPageFilters focuses on discovery (tools, tags, type).

## Progress Summary

- **Status**: Pending
- **Estimated Hours**: 2-4 hours
- **Completed Tasks**: 0/3
- **In Progress Tasks**: 0/3
- **Blocked Tasks**: 0/3

## Tasks Overview

### Batch 1: Filter Components (Parallel)
- **FILTER-4.1**: Create ManagePageFilters component
- **FILTER-4.2**: Enhance CollectionPageFilters with tools filter

### Batch 2: URL State
- **FILTER-4.3**: Add filter state to URL for bookmarkability

## Quality Gate Checklist

- [ ] ManagePageFilters component renders with all filter types
- [ ] CollectionPageFilters has Tools filter working
- [ ] Filter state persists in URL
- [ ] Filters can be bookmarked and shared
- [ ] No console errors on filter changes
- [ ] Collection/group selection persists via URL without breaking local state
- [ ] Deep links with filters work correctly

## Output Artifacts

- New `skillmeat/web/components/manage/manage-page-filters.tsx`
- Updated `skillmeat/web/components/collection/collection-page-filters.tsx` (or existing filters.tsx)
- Updated `skillmeat/web/app/manage/page.tsx` (filter integration)
- Updated `skillmeat/web/app/collection/page.tsx` (filter URL state)

## Dependencies

- **Phase 0**: Complete (deployments data available)
- **Phase 1**: Complete (deep linking infrastructure available)
- **Phase 2**: Complete (card components available)
- **Phase 3**: Complete (modal separation done)
- **Tools API PRD**: Complete (prerequisite for tools filter)

## Notes

This phase focuses on filtering UX. The manage page needs operations-focused filters (project, status), while the collection page gets enhanced with tools filtering for better discovery.
