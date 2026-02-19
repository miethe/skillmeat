---
feature: Collection Group Ordering & Drag Artifacts Between Groups
status: in-progress
created: 2026-02-16
branch: feat/collection-org
tasks:
- id: SORT-1
  title: Sort groups alphabetically in all listing locations
  status: in-progress
  assigned_to: ui-engineer-enhanced
  files:
  - skillmeat/web/components/shared/group-filter-select.tsx
  - skillmeat/web/components/collection/add-to-group-dialog.tsx
  - skillmeat/web/components/collection/manage-groups-dialog.tsx
  - skillmeat/web/components/entity/groups-display.tsx
  - skillmeat/web/app/groups/components/groups-page-client.tsx
  - skillmeat/web/app/groups/components/groups-toolbar.tsx
  - skillmeat/web/hooks/use-groups.ts
- id: DND-1
  title: Rework grouped-artifact-view - remove group reorder, add artifact cross-group
    drag with list items
  status: in-progress
  assigned_to: ui-engineer-enhanced
  files:
  - skillmeat/web/components/collection/grouped-artifact-view.tsx
schema_version: 2
doc_type: quick_feature
feature_slug: collection-group-ordering
---

## Summary

Three changes:
1. Groups listed alphabetically (by name) everywhere
2. Remove broken group drag-to-reorder + visual indicators
3. Add artifact drag between groups with list-item display + drag handles
