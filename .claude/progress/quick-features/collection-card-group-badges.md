---
feature: collection-card-group-badges
status: completed
created: 2026-02-13
scope: frontend-only
files_affected:
- skillmeat/web/components/collection/artifact-group-badges.tsx (NEW)
- skillmeat/web/components/collection/artifact-browse-card.tsx (EDIT)
tasks:
- id: TASK-1
  name: Create ArtifactGroupBadges component
  status: pending
  assigned_to: ui-engineer-enhanced
- id: TASK-2
  name: Integrate badges into artifact-browse-card
  status: pending
  assigned_to: ui-engineer-enhanced
schema_version: 2
doc_type: quick_feature
feature_slug: collection-card-group-badges
---

# Collection Card Group Badges

## Goal
Add group membership badges to artifact cards in grid view on /collection page.

## Design
- **Zone**: Bottom-left of card, between tags section and footer divider
- **Badge style**: Group color as background, auto-contrast text (existing Badge colorStyle), group icon + name
- **Compact mode**: When badges overflow zone (max ~3 visible), show icon-only with tooltip for name
- **Overflow**: `+N` indicator when too many groups, tooltip shows full list on hover
- **Empty state**: No badge zone rendered when artifact has no groups (clean, no placeholder)

## Implementation
1. New `ArtifactGroupBadges` component using `useArtifactGroups` hook
2. Uses `resolveColorHex` from group-constants for badge colors
3. Renders Lucide icons from GROUP_ICONS mapping
4. Integrate into artifact-browse-card between tags and footer
