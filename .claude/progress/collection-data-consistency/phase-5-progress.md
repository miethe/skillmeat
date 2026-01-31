---
type: progress
prd: collection-data-consistency
phase: 5
title: Frontend Data Preloading
status: completed
started: null
completed: null
progress: 100
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ui-engineer
contributors: []
tasks:
- id: TASK-5.1
  title: Create DataPrefetcher Component
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  model: opus
  effort: 0.5h
  priority: medium
  files:
  - skillmeat/web/app/providers.tsx
- id: TASK-5.2
  title: Integrate with QueryClient
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-5.1
  model: sonnet
  effort: 0.5h
  priority: medium
  files:
  - skillmeat/web/app/providers.tsx
- id: TASK-5.3
  title: Add Loading State Indicator
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-5.1
  model: haiku
  effort: 0.25h
  priority: low
  files:
  - skillmeat/web/app/providers.tsx
- id: TASK-5.4
  title: Document Prefetch Strategy
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-5.1
  model: haiku
  effort: 0.25h
  priority: low
  files:
  - skillmeat/web/app/providers.tsx
parallelization:
  batch_1:
  - TASK-5.1
  batch_2:
  - TASK-5.2
  - TASK-5.3
  - TASK-5.4
blockers: []
success_criteria:
- id: SC-5.1
  description: DataPrefetcher component created and mounted in providers
  status: pending
- id: SC-5.2
  description: Sources and collections prefetched on app load
  status: pending
- id: SC-5.3
  description: No duplicate network requests on navigation
  status: pending
- id: SC-5.4
  description: Prefetch does not block initial render
  status: pending
- id: SC-5.5
  description: StaleTime configured appropriately (5 minutes)
  status: pending
updated: '2026-01-31'
---

# Phase 5: Frontend Data Preloading

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-data-consistency/phase-5-progress.md \
  -t TASK-5.1 -s completed

# Batch update after parallel execution
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-data-consistency/phase-5-progress.md \
  --updates "TASK-5.2:completed,TASK-5.3:completed,TASK-5.4:completed"
```

## Overview

Phase 5 adds frontend data prefetching to improve UX by loading commonly-needed data (sources, collections) at app initialization. This eliminates navigation-dependent cache population and ensures data is available immediately when users navigate to pages that need it.

**Estimated Duration**: 1-2 hours
**Risk**: Low (additive UX improvement)
**Dependencies**: Phase 2 complete (entity mapper available)

## Tasks

### TASK-5.1: Create DataPrefetcher Component

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.5h
**Priority**: medium
**Model**: opus

**Description**: Create prefetcher component that loads sources and collections at app initialization

**Requirements**:
- Component mounts in providers.tsx
- Prefetches on app load
- Returns null (no UI - background operation)
- Uses useEffect with useQueryClient

**Files**:
- `skillmeat/web/app/providers.tsx`: Add DataPrefetcher component

**Key Implementation Notes**:
- Use queryClient.prefetchQuery() not useQuery()
- Prefetch sources and user-collections endpoints
- staleTime: 5 minutes to match backend cache TTL

---

### TASK-5.2: Integrate with QueryClient

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.5h
**Priority**: medium
**Model**: sonnet
**Dependencies**: TASK-5.1

**Description**: Configure prefetch queries with staleTime to avoid redundant fetches

**Requirements**:
- Prefetched data available immediately on navigation
- No duplicate requests on navigation
- staleTime configured to 5 minutes
- gcTime (formerly cacheTime) appropriate

**Files**:
- `skillmeat/web/app/providers.tsx`: Configure query options

---

### TASK-5.3: Add Loading State Indicator

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.25h
**Priority**: low
**Model**: haiku
**Dependencies**: TASK-5.1

**Description**: Optional: Add subtle loading indicator during initial prefetch

**Requirements**:
- Users see prefetch status (can be silent)
- Non-blocking - does not prevent app usage
- Optional implementation (can skip if UX is smooth without)

**Files**:
- `skillmeat/web/app/providers.tsx`: Optional loading indicator

---

### TASK-5.4: Document Prefetch Strategy

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.25h
**Priority**: low
**Model**: haiku
**Dependencies**: TASK-5.1

**Description**: Add comments explaining prefetch rationale and configuration

**Requirements**:
- Future developers understand prefetch behavior
- Document why these specific endpoints are prefetched
- Document staleTime rationale
- JSDoc on DataPrefetcher component

**Files**:
- `skillmeat/web/app/providers.tsx`: Add documentation comments

---

## Quality Gates

- [ ] DataPrefetcher component created and mounted in providers
- [ ] Sources and collections prefetched on app load
- [ ] No duplicate network requests on navigation
- [ ] Prefetch does not block initial render
- [ ] StaleTime configured appropriately (5 minutes)

## Key Files Modified

- `skillmeat/web/app/providers.tsx`
