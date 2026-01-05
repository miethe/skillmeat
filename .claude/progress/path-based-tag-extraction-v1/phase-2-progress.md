---
prd_name: path-based-tag-extraction-v1
phase: 2
title: "Frontend Review UI"
status: completed
completion: 100%
started_at: "2025-01-05T00:00:00Z"
completed_at: "2025-01-05T11:50:00Z"

tasks:
  - id: "TASK-2.1"
    title: "API Client Functions"
    status: "completed"
    assigned_to: ["ui-engineer"]
    model: "sonnet"
    dependencies: []
    estimated_time: "3h"
    commit: "3eff240"
    files:
      - "skillmeat/web/lib/api/marketplace.ts"

  - id: "TASK-2.2"
    title: "Type Definitions"
    status: "completed"
    assigned_to: ["ui-engineer"]
    model: "haiku"
    dependencies: []
    estimated_time: "2h"
    commit: "3eff240"
    files:
      - "skillmeat/web/types/path-tags.ts"

  - id: "TASK-2.3"
    title: "React Query Hooks"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    model: "opus"
    dependencies: ["TASK-2.1", "TASK-2.2"]
    estimated_time: "6h"
    commit: "631b395"
    files:
      - "skillmeat/web/hooks/use-path-tags.ts"

  - id: "TASK-2.4"
    title: "PathTagReview Component"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    model: "opus"
    dependencies: ["TASK-2.3"]
    estimated_time: "10h"
    commit: "f61cea5"
    files:
      - "skillmeat/web/components/marketplace/path-tag-review.tsx"

  - id: "TASK-2.5"
    title: "CatalogEntryModal Integration"
    status: "completed"
    assigned_to: ["ui-engineer"]
    model: "opus"
    dependencies: ["TASK-2.4"]
    estimated_time: "5h"
    commit: "6b194be"
    files:
      - "skillmeat/web/components/CatalogEntryModal.tsx"

  - id: "TASK-2.6"
    title: "Accessibility Audit"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    model: "sonnet"
    dependencies: ["TASK-2.4", "TASK-2.5"]
    estimated_time: "5h"
    commit: "986512c"
    files:
      - "skillmeat/web/components/marketplace/path-tag-review.tsx"

  - id: "TASK-2.7"
    title: "E2E Tests"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    model: "sonnet"
    dependencies: ["TASK-2.4", "TASK-2.5"]
    estimated_time: "5h"
    commit: "986512c"
    files:
      - "skillmeat/web/tests/e2e/path-tag-review.spec.ts"

  - id: "TASK-2.8"
    title: "Component Testing"
    status: "completed"
    assigned_to: ["ui-engineer"]
    model: "sonnet"
    dependencies: ["TASK-2.4"]
    estimated_time: "4h"
    commit: "6b194be"
    files:
      - "skillmeat/web/__tests__/components/marketplace/path-tag-review.test.tsx"

parallelization:
  batch_1: ["TASK-2.1", "TASK-2.2"]
  batch_2: ["TASK-2.3"]
  batch_3: ["TASK-2.4"]
  batch_4: ["TASK-2.5", "TASK-2.8"]
  batch_5: ["TASK-2.6", "TASK-2.7"]
  critical_path: ["TASK-2.1", "TASK-2.3", "TASK-2.4", "TASK-2.5"]
  estimated_total_time: "40h"

blockers: []

execution_log:
  - batch: 1
    completed_at: "2025-01-05T11:30:00Z"
    tasks: ["TASK-2.1", "TASK-2.2"]
  - batch: 2
    completed_at: "2025-01-05T11:35:00Z"
    tasks: ["TASK-2.3"]
  - batch: 3
    completed_at: "2025-01-05T11:40:00Z"
    tasks: ["TASK-2.4"]
  - batch: 4
    completed_at: "2025-01-05T11:45:00Z"
    tasks: ["TASK-2.5", "TASK-2.8"]
  - batch: 5
    completed_at: "2025-01-05T11:50:00Z"
    tasks: ["TASK-2.6", "TASK-2.7"]
---

# Phase 2: Frontend Review UI - Progress Tracking

## Phase Overview

Build user-facing components for reviewing and approving path-based tags in the marketplace.

## Dependencies

- **Phase 1**: Complete (commit ab10c59)
  - Backend API endpoints (GET/PATCH path-tags)
  - PathSegmentExtractor service
  - Database migration with path_segments column

## Orchestration Quick Reference

### Batch 1 (No dependencies - Parallel)

```
Task("ui-engineer", "TASK-2.1: Create API client functions for path tags.

Files to create/modify:
- skillmeat/web/lib/api/marketplace.ts

Implement:
1. getPathTags(sourceId: string, entryId: string): Promise<PathSegmentsResponse>
   - GET /api/v1/marketplace-sources/{sourceId}/catalog/{entryId}/path-tags
2. updatePathTagStatus(sourceId, entryId, segment, status): Promise<PathSegmentsResponse>
   - PATCH with {segment, status} body

Error handling:
- 404: 'Catalog entry not found' or 'Segment not found'
- 409: 'Segment already approved/rejected'
- 500: Generic failure

Follow patterns in .claude/rules/web/api-client.md", model="sonnet")

Task("ui-engineer", "TASK-2.2: Create TypeScript type definitions for path tags.

Files to create:
- skillmeat/web/types/path-tags.ts

Types needed:
1. ExtractedSegment { segment, normalized, status, reason? }
   - status: 'pending' | 'approved' | 'rejected' | 'excluded'
2. PathSegmentsResponse { entry_id, raw_path, extracted: ExtractedSegment[], extracted_at }
3. UpdateSegmentStatusRequest { segment, status }

Export from types/index.ts if it exists.", model="haiku")
```

### Batch 2 (Depends on Batch 1)

```
Task("ui-engineer-enhanced", "TASK-2.3: Create React Query hooks for path tag operations.

Files to create:
- skillmeat/web/hooks/use-path-tags.ts

Implement:
1. Query key factory (pathTagKeys.all, pathTagKeys.detail(sourceId, entryId))
2. usePathTags(sourceId, entryId) - fetch hook with 5min staleTime
3. useUpdatePathTagStatus() - mutation with cache invalidation

Follow patterns in .claude/rules/web/hooks.md
Import API functions from @/lib/api/marketplace
Import types from @/types/path-tags")
```

### Batch 3 (Depends on Batch 2)

```
Task("ui-engineer-enhanced", "TASK-2.4: Build PathTagReview component.

Files to create:
- skillmeat/web/components/marketplace/path-tag-review.tsx

Component requirements:
1. Props: { sourceId: string, entryId: string }
2. States: loading, error, empty, data
3. Segment display: original value, normalized value, status badge, reason (if excluded)
4. Actions: Approve/Reject buttons for pending segments (disabled during mutation)
5. Summary footer: counts of approved/rejected/pending/excluded

UI requirements:
- Use shadcn/radix components (Button, Card, Badge)
- Dark mode support
- Responsive layout
- Accessibility: aria-labels on icon buttons, keyboard navigable

Sub-components:
- SegmentRow: single segment with actions
- StatusBadge: color-coded status indicator
- PathTagSummary: counts footer")
```

### Batch 4 (Depends on Batch 3 - Parallel)

```
Task("ui-engineer", "TASK-2.5: Integrate PathTagReview into CatalogEntryModal.

Files to modify:
- skillmeat/web/components/marketplace/catalog-entry-detail.tsx (or similar)

Integration:
1. Add 'Suggested Tags' tab/section (only visible if entry has path_segments)
2. Import and render PathTagReview component
3. Tab should show count badge if segments exist
4. Ensure no breaking changes to existing modal functionality

Reference existing modal patterns in the file.", model="opus")

Task("ui-engineer", "TASK-2.8: Create component unit tests for PathTagReview.

Files to create:
- skillmeat/web/__tests__/components/path-tag-review.test.tsx (or appropriate test location)

Test cases:
1. Renders loading state
2. Renders error state with retry
3. Renders empty state (no segments)
4. Renders segments list
5. Approve button calls mutation
6. Reject button calls mutation
7. Buttons disabled during mutation
8. Status updates after mutation
9. Summary counts are accurate

Use React Testing Library, mock hooks appropriately.
Target >80% coverage.", model="sonnet")
```

### Batch 5 (Depends on Batch 4 - Parallel)

```
Task("ui-engineer-enhanced", "TASK-2.6: Accessibility audit for PathTagReview.

Audit checklist:
1. Keyboard navigation (Tab, Space, Enter)
2. Screen reader support (aria-labels, status descriptions)
3. Color contrast (WCAG AA 4.5:1)
4. Focus management
5. Touch targets (44px minimum on mobile)

Fix any issues found in:
- skillmeat/web/components/marketplace/path-tag-review.tsx

Document findings.", model="sonnet")

Task("ui-engineer-enhanced", "TASK-2.7: Create E2E tests for path tag review workflow.

Test location: Determine from project structure (tests/e2e/ or similar)

Test scenarios:
1. User opens catalog entry modal
2. Navigates to Suggested Tags tab
3. Approves a segment (verify status changes)
4. Rejects a segment (verify status changes)
5. Summary counts update correctly
6. Changes persist after modal close/reopen

Use project's E2E framework (Playwright/Cypress).
Mock API responses if needed for test isolation.", model="sonnet")
```

## Work Log

_Updated automatically by artifact-tracker_
