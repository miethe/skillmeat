---
id: collections-groups-tab-redesign
title: "Redesign Collections Tab - Separate Collections & Groups Sections"
status: completed
created: 2026-02-13
scope: frontend-only
files_affected:
  - skillmeat/web/components/entity/modal-collections-tab.tsx
---

## Feature

Redesign the Collections tab in ArtifactOperationsModal/ArtifactDetailsModal to separate Collections and Groups into distinct visual sections.

## Changes

### modal-collections-tab.tsx

1. **Header**: Change "Collections & Groups" → "Collections"
2. **Remove** "Add to Group" button from the header area
3. **After collections list**: Add a visual separator (Separator component)
4. **New "Groups" section**:
   - "Groups" header with "Add to Group" button beside it
   - Import `GroupCard` from `app/groups/components/group-card.tsx`
   - Display artifact's groups in a responsive grid (2 columns when space allows)
   - Empty state when no groups: subtle message with the Add to Group button
5. **Layout**: Dynamic vertical placement - collections section takes natural height, groups section follows
6. **Empty states**: Clean design when 0 collections (only Default) or 0 groups

## Quality Gates

- [ ] pnpm type-check
- [ ] pnpm lint
- [ ] pnpm build
