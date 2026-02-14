---
status: completed
created: 2026-02-13
completed: 2026-02-13
feature: Fix ArtifactLinkingDialog - focus borders, alignment, search, advanced filters
files:
  - skillmeat/web/components/entity/artifact-linking-dialog.tsx
  - skillmeat/web/components/ui/tag-filter-popover.tsx (reuse)
  - skillmeat/web/components/ui/tool-filter-popover.tsx (reuse)
commits:
  - 8f84d4ac fix(web): structural fix for ArtifactLinkingDialog overflow
---

# Fix ArtifactLinkingDialog

## Issues

1. **Focus border clipping**: Form field focus rings are cut off on sides. Add proper padding/overflow to dialog content.
2. **Relationship Type alignment**: Selected value shows center-aligned text instead of left-aligned.
3. **Search not filtering**: Typing in search doesn't filter the artifact list.
4. **Advanced filters**: Add collapsible section with Tag and Tool filters (reuse existing components from collection page).

## Tasks

- [x] TASK-1: Fix focus border clipping (structural fix with [&>*]:min-w-0 on DialogContent)
- [x] TASK-2: Fix Relationship Type select text alignment (simplified SelectItems with helper text)
- [x] TASK-3: Fix search filtering to actually filter artifact results (client-side useMemo filter)
- [x] TASK-4: Add collapsible Advanced Filters section with TagFilterPopover and ToolFilterPopover

## Root Cause

CSS Grid items have `min-width: auto` by default. Long artifact source URLs (e.g., GitHub paths) forced grid children to 887px inside a 512px dialog. The fix `[&>*]:min-w-0` allows grid items to shrink below content width.
