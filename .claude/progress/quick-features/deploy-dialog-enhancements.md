---
feature: deploy-dialog-enhancements
status: completed
created: 2026-02-10
scope: frontend-only
files_affected:
  - skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx
  - skillmeat/web/app/projects/[id]/manage/page.tsx
---

# Deploy from Collection Dialog Enhancements

## Requirements

1. **Grey out deployed artifacts** - Artifacts already deployed to the project should be visually disabled and unselectable to prevent 409 errors
2. **Larger dialog** - Increase dialog size to show more content
3. **Hover open icon** - Each artifact row shows an icon on hover; clicking opens ArtifactDetailsModal
4. **Group filter** - Button next to search to filter by Groups (using GroupFilterSelect)
5. **Tag filter** - Button next to search to filter by Tags (using TagFilterPopover)

## Reusable Components

- `TagFilterPopover` from `components/ui/tag-filter-popover.tsx`
- `GroupFilterSelect` from `components/shared/group-filter-select.tsx`
- `ArtifactDetailsModal` from `components/collection/artifact-details-modal.tsx`

## Tasks

- TASK-1: Implement all dialog enhancements (single ui-engineer-enhanced agent)

## Status

- [x] Plan created
- [x] Implementation delegated (ui-engineer-enhanced)
- [x] Quality gates passed (type-check clean, all errors pre-existing)
- [x] Complete
