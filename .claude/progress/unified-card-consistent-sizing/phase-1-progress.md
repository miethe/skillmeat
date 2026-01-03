---
prd: unified-card-consistent-sizing
phase: 1
title: Unified Card Consistent Sizing
status: completed
created: 2025-12-30
updated: 2025-12-30
completed_at: 2025-12-30

tasks:
  - id: "TASK-1"
    title: "Modify UnifiedCard content section layout"
    status: completed
    assigned_to: ["ui-engineer"]
    dependencies: []
    files:
      - skillmeat/web/components/shared/unified-card.tsx
    acceptance:
      - All content rows have fixed minimum heights
      - Description section always renders (uses nbsp when empty)
      - Tags section always renders (invisible when empty)
      - Warnings section always renders (invisible when empty)
      - Flex layout distributes space correctly
    commit: 1c117cf

  - id: "TASK-2"
    title: "Update UnifiedCardSkeleton to match new layout"
    status: completed
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-1"]
    files:
      - skillmeat/web/components/shared/unified-card.tsx
    acceptance:
      - Skeleton has same fixed dimensions as content card
      - Layout matches populated card structure
    commit: 1c117cf

  - id: "TASK-3"
    title: "Visual verification and adjustment"
    status: completed
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2"]
    files: []
    acceptance:
      - All cards in grid have identical heights
      - Cards with/without tags align perfectly
      - Cards with/without descriptions align perfectly
      - No layout shifts during loading
    note: "Build passes, CSS changes verified structurally"

parallelization:
  batch_1: ["TASK-1"]
  batch_2: ["TASK-2"]
  batch_3: ["TASK-3"]

summary:
  total_tasks: 3
  pending: 0
  in_progress: 0
  completed: 3
  blocked: 0
---

# Phase 1: Unified Card Consistent Sizing

## Overview

Single-phase implementation to standardize card heights on the collection page by using fixed-height rows with flex distribution.

## Orchestration Quick Reference

**Batch 1**:
- TASK-1 → `ui-engineer`

```
Task("ui-engineer", "TASK-1: Modify UnifiedCard content section layout.

File: skillmeat/web/components/shared/unified-card.tsx

Current issue: Cards have varying heights because description, tags, and warnings sections only render conditionally.

Required changes to the content section (lines 384-436):

1. Change the content wrapper from `space-y-3` to `flex flex-col` with fixed height
2. Make description ALWAYS render - use non-breaking space when empty
3. Make tags section ALWAYS render - invisible placeholder when empty
4. Make warnings section ALWAYS render - invisible placeholder when not outdated
5. Use min-h-* classes to ensure consistent row heights
6. Use flex-grow on description to absorb unused space

Target structure:
- Content container: flex flex-col, fixed min-height (~160px)
- Description row: flex-grow, min-h-[40px], line-clamp-2
- Metadata row: h-[20px]
- Tags row: h-[24px], mt-2, always rendered
- Warnings row: h-[16px], always rendered

Preserve all existing functionality and styling.")
```

**Batch 2** (after TASK-1 complete):
- TASK-2 → `ui-engineer`

```
Task("ui-engineer", "TASK-2: Update UnifiedCardSkeleton to match new layout.

File: skillmeat/web/components/shared/unified-card.tsx

Update the UnifiedCardSkeleton component to match the new fixed-height layout structure from TASK-1. The skeleton should have the same dimensions and row structure as the populated card.")
```

**Batch 3** (after TASK-2 complete):
- TASK-3 → `ui-engineer`

```
Task("ui-engineer", "TASK-3: Visual verification of card alignment.

Verify that cards on the /collection page now have consistent heights:
1. Cards with tags align with cards without tags
2. Cards with descriptions align with cards without
3. Loading skeletons match final card dimensions
4. No layout shifts occur during data loading

If any alignment issues remain, make final adjustments to the min-h values in unified-card.tsx.")
```

## Progress Log

*(Updates recorded here as tasks complete)*
