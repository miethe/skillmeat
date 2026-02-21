---
feature: plugin-members-tab-fix
status: in-progress
created: 2026-02-20
---

# Plugin Members Tab Fix

## Problem
- ArtifactDetailsModal plugin tab uses `CompositePreview` + `useComposites()` → `.memberships` - doesn't populate
- ArtifactOperationsModal has no plugin/composite tab at all
- Source modal works because it uses `PluginMembersTab` + `useArtifactAssociations()`

## Fix
1. ArtifactDetailsModal: Replace `CompositePreview` with `PluginMembersTab` in the plugin tab content
2. ArtifactOperationsModal: Add composite-conditional plugin tab using `PluginMembersTab`

## Files
- `skillmeat/web/components/collection/artifact-details-modal.tsx`
- `skillmeat/web/components/manage/artifact-operations-modal.tsx`

## Tasks
- [ ] TASK-1: Fix ArtifactDetailsModal plugin tab (use PluginMembersTab)
- [ ] TASK-2: Add plugin tab to ArtifactOperationsModal
---
