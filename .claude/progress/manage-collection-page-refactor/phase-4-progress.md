---
type: progress
prd: manage-collection-page-refactor
phase: 4
title: Filter Components
status: pending
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- frontend-developer
contributors:
- ui-engineer-enhanced
tasks:
- id: FILTER-4.1
  description: 'Create ManagePageFilters component: Project dropdown, Status filter
    (All, Needs Update, Has Drift, Deployed, Error), Type filter, search input.'
  status: pending
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1.5h
  priority: high
  model: opus
- id: FILTER-4.2
  description: Enhance CollectionPageFilters with tools multi-select popover. Add
    to existing filters (Collection, Group, Type, Tags, Search).
  status: pending
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1h
  priority: medium
  model: sonnet
- id: FILTER-4.3
  description: Add filter state to URL for bookmarkability. Serialize filter state
    to query params, restore on page load, update on filter change.
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - FILTER-4.1
  - FILTER-4.2
  estimated_effort: 1.5h
  priority: high
  model: opus
parallelization:
  batch_1:
  - FILTER-4.1
  - FILTER-4.2
  batch_2:
  - FILTER-4.3
  critical_path:
  - FILTER-4.1
  - FILTER-4.3
  estimated_total_time: 2-4h
blockers: []
success_criteria:
- id: SC-4.1
  description: ManagePageFilters component renders with all filter types
  status: pending
- id: SC-4.2
  description: CollectionPageFilters has Tools filter working
  status: pending
- id: SC-4.3
  description: Filter state persists in URL
  status: pending
- id: SC-4.4
  description: Filters can be bookmarked and shared
  status: pending
- id: SC-4.5
  description: No console errors on filter changes
  status: pending
files_modified:
- skillmeat/web/components/manage/manage-page-filters.tsx
- skillmeat/web/components/collection/collection-page-filters.tsx
- skillmeat/web/app/manage/page.tsx
- skillmeat/web/app/collection/page.tsx
schema_version: 2
doc_type: progress
feature_slug: manage-collection-page-refactor
---

# manage-collection-page-refactor - Phase 4: Filter Components

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/manage-collection-page-refactor/phase-4-progress.md -t FILTER-4.1 -s completed
```

---

## Objective

Implement purpose-specific filters that guide users toward relevant features on each page. Operations filters focus on status/health. Discovery filters focus on content/metadata.

---

## Orchestration Quick Reference

### Batch 1 (Launch in parallel - single message)

```
Task("frontend-developer", "FILTER-4.1: Create ManagePageFilters component. Include: Project dropdown (populated from projects), Status filter (All, Needs Update, Has Drift, Deployed, Error), Type filter (artifact types), search input. All filters functional, active filters display clearly. File: skillmeat/web/components/manage/manage-page-filters.tsx")

Task("frontend-developer", "FILTER-4.2: Enhance CollectionPageFilters with tools filter. Add Tools multi-select popover to existing filters (Collection, Group, Type, Tags, Search). Popover opens, tools list displays, multi-select works, selected tools show in active filters, clear all works, responsive on mobile. File: skillmeat/web/components/collection/collection-page-filters.tsx", model="sonnet")
```

### Batch 2 (After batch_1 completes)

```
Task("frontend-developer", "FILTER-4.3: Add filter state to URL for bookmarkability. Serialize filter state to query params on both pages. Restore filters from URL on page load. Update URL on filter change (use router.replace to avoid history pollution). Handle deep links with filters + artifact. No race conditions between filter state and URL sync. Files: skillmeat/web/app/manage/page.tsx, skillmeat/web/app/collection/page.tsx")
```

---

## Tasks Reference

| Task ID | Description | Assignee | Est. | Dependencies |
|---------|-------------|----------|------|--------------|
| FILTER-4.1 | Create ManagePageFilters | frontend-developer | 1.5h | - |
| FILTER-4.2 | Enhance CollectionPageFilters | frontend-developer | 1h | - |
| FILTER-4.3 | Add filter state to URL | frontend-developer | 1.5h | FILTER-4.1, FILTER-4.2 |

---

## Quality Gate

- [ ] ManagePageFilters component renders with all filter types
- [ ] CollectionPageFilters has Tools filter working
- [ ] Filter state persists in URL
- [ ] Filters can be bookmarked and shared
- [ ] No console errors on filter changes

---

## Implementation Notes

### Architectural Decisions

- Filters are page-specific to match content focus
- URL state is source of truth for filters (bookmarkable)
- Active filters displayed as dismissible chips

### Patterns and Best Practices

- Use `useSearchParams()` and `router.replace()` for URL sync
- Debounce search input (300ms) to avoid excessive updates
- Multi-select popovers use Radix Popover + Checkbox
- Filter state serialization: `?status=drift&type=skill&search=canvas`

### Known Gotchas

- Multiple filters can create long URLs - consider compression for complex states
- URL updates should not trigger unnecessary re-fetches
- Deep links with both filters and artifact ID must parse correctly
- Browser back button should restore previous filter state

### Filter Specifications

```
ManagePageFilters
  - Project: dropdown (all projects user has access to)
  - Status: single-select (All | Needs Update | Has Drift | Deployed | Error)
  - Type: single-select (All | Skill | Command | Agent | etc.)
  - Search: text input (searches name, description)

CollectionPageFilters (existing + new)
  - Collection: dropdown (user collections)
  - Group: dropdown (groups within collection)
  - Type: single-select
  - Tags: multi-select popover
  - Tools: multi-select popover (NEW)
  - Search: text input
```

---

## Completion Notes

(Fill in when phase is complete)
