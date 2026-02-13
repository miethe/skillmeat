---
status: in-progress
created: 2026-02-13
feature: Fix ArtifactLinkingDialog - focus borders, alignment, search, advanced filters
files:
  - skillmeat/web/components/entity/artifact-linking-dialog.tsx
  - skillmeat/web/components/ui/tag-filter-popover.tsx (reuse)
  - skillmeat/web/components/ui/tool-filter-popover.tsx (reuse)
---

# Fix ArtifactLinkingDialog

## Issues

1. **Focus border clipping**: Form field focus rings are cut off on sides. Add proper padding/overflow to dialog content.
2. **Relationship Type alignment**: Selected value shows center-aligned text instead of left-aligned.
3. **Search not filtering**: Typing in search doesn't filter the artifact list.
4. **Advanced filters**: Add collapsible section with Tag and Tool filters (reuse existing components from collection page).

## Tasks

- [ ] TASK-1: Fix focus border clipping (padding/overflow on dialog content)
- [ ] TASK-2: Fix Relationship Type select text alignment (left-align selected value)
- [ ] TASK-3: Fix search filtering to actually filter artifact results
- [ ] TASK-4: Add collapsible Advanced Filters section with TagFilterPopover and ToolFilterPopover
