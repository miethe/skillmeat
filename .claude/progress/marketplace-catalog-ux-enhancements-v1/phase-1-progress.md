---
prd: marketplace-catalog-ux-enhancements-v1
phase: 1
title: "Pagination & Count Indicator"
status: not_started
start_date: null
end_date: null
completion_percentage: 0

tasks:
  - id: TASK-1.1
    title: "Add pagination bar visual separation"
    description: "Add visual separation to pagination bar (shadow/border/glassmorphism effect)"
    status: pending
    assigned_to: ui-engineer
    story_points: 3
    dependencies: []
    files_modified: []
    notes: ""

  - id: TASK-1.2
    title: "Implement traditional pagination UI"
    description: "Build traditional pagination with numbered pages (1-5+), Next/Previous, items per page selector (10/25/50/100)"
    status: pending
    assigned_to: ui-engineer-enhanced
    story_points: 5
    dependencies: ["TASK-1.1"]
    files_modified: []
    notes: ""

  - id: TASK-1.3
    title: "Add artifact count indicator"
    description: "Add 'Showing X of Y artifacts' indicator above list"
    status: pending
    assigned_to: ui-engineer
    story_points: 2
    dependencies: []
    files_modified: []
    notes: ""

  - id: TASK-1.4
    title: "Wire count totals from hook"
    description: "Connect artifact count indicator to useMarketplaceArtifacts hook for live totals"
    status: pending
    assigned_to: ui-engineer
    story_points: 1
    dependencies: ["TASK-1.3"]
    files_modified: []
    notes: ""

  - id: TASK-1.5
    title: "Unit and E2E tests for pagination"
    description: "Add unit tests for pagination component and E2E tests for pagination flows. Target >80% coverage."
    status: pending
    assigned_to: ui-engineer
    story_points: 2
    dependencies: ["TASK-1.2", "TASK-1.3"]
    files_modified: []
    notes: ""

parallelization:
  batch_1:
    - "TASK-1.1"
    - "TASK-1.3"
  batch_2:
    - "TASK-1.2"
    - "TASK-1.4"
  batch_3:
    - "TASK-1.5"

blockers: []

success_criteria:
  - "Pagination bar has visual separation (shadow/border/glassmorphism)"
  - "Traditional pagination UI implemented: numbered pages (1-5+), Next/Previous, items per page (10/25/50/100)"
  - "'Showing X of Y artifacts' visible above list and updates with filters"
  - "E2E tests pass with >80% coverage"

estimated_total_story_points: 13
actual_total_story_points: null
---

# Phase 1: Pagination & Count Indicator

## Overview

Implement visual enhancements to marketplace catalog pagination including traditional pagination UI, count indicators, and visual separation.

## Progress Summary

- **Status**: Not Started
- **Completion**: 0%
- **Story Points**: 0/13 completed

## Task Details

### Batch 1 (Parallel) - Visual Foundation

#### TASK-1.1: Add pagination bar visual separation
- **Status**: Pending
- **Assigned to**: ui-engineer
- **Story Points**: 3
- **Dependencies**: None
- **Description**: Add visual separation to pagination bar using shadow, border, or glassmorphism effect to distinguish it from artifact list.

#### TASK-1.3: Add artifact count indicator
- **Status**: Pending
- **Assigned to**: ui-engineer
- **Story Points**: 2
- **Dependencies**: None
- **Description**: Add "Showing X of Y artifacts" text indicator above the artifact list.

### Batch 2 (After Batch 1) - Functional Implementation

#### TASK-1.2: Implement traditional pagination UI
- **Status**: Pending
- **Assigned to**: ui-engineer-enhanced
- **Story Points**: 5
- **Dependencies**: TASK-1.1
- **Description**: Build traditional pagination component with:
  - Numbered pages (show 1-5+ with ellipsis)
  - Next/Previous buttons
  - Items per page selector (10/25/50/100 options)
  - Integrate with existing cursor-based pagination backend

#### TASK-1.4: Wire count totals from hook
- **Status**: Pending
- **Assigned to**: ui-engineer
- **Story Points**: 1
- **Dependencies**: TASK-1.3
- **Description**: Connect artifact count indicator to `useMarketplaceArtifacts` hook to display live totals that update with filters.

### Batch 3 (After Batch 2) - Testing

#### TASK-1.5: Unit and E2E tests for pagination
- **Status**: Pending
- **Assigned to**: ui-engineer
- **Story Points**: 2
- **Dependencies**: TASK-1.2, TASK-1.3
- **Description**: Add comprehensive tests for pagination component and count indicator:
  - Unit tests for pagination logic
  - E2E tests for pagination flows
  - Target >80% coverage

## Context for AI Agents

### Key Files
- `skillmeat/web/app/marketplace/page.tsx` - Main marketplace catalog page
- `skillmeat/web/hooks/use-marketplace-artifacts.ts` - Data fetching hook with pagination
- `skillmeat/web/components/ui/` - Radix UI components for pagination primitives

### Technical Decisions
- Backend uses cursor-based pagination; frontend will map to page numbers for UX
- Count indicator should reflect filtered results, not just total artifacts
- Visual separation should match existing design system (Radix UI + shadcn)

### Integration Points
- Pagination state managed by `useMarketplaceArtifacts` hook
- Count totals available from backend API response
- Need to coordinate with filter state for accurate counts

## Notes

Initial phase focuses on visual improvements and traditional pagination patterns. Backend already supports cursor-based pagination, so main work is UI mapping and state management.
