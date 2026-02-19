---
feature: collection-card-ux-enhancements
status: completed
created: 2026-02-15
branch: feat/collection-org
estimated_effort: 1-2 hours
files_affected:
- skillmeat/web/components/collection/artifact-browse-card.tsx
- skillmeat/web/components/manage/artifact-operations-card.tsx
- skillmeat/web/components/collection/artifact-group-badges.tsx
- skillmeat/web/components/collection/filters.tsx
- skillmeat/web/app/manage/components/entity-filters.tsx
schema_version: 2
doc_type: quick_feature
feature_slug: collection-card-ux-enhancements
---

# Collection Card UX Enhancements

## Requirements

1. **Tooltips on '+' buttons** (collection page): Add hover tooltips "Add Tags" / "Add to Group" on the '+' buttons
2. **Click badge to filter**: Clicking a Tag or Group badge on a card applies that filter to the page
3. **Group filter on collection page**: Ensure Group filter is available in the Filters bar (currently conditional)
4. **Focus ring on badges**: Hovering on Tag/Group badges shows focus ring indicating clickability
5. **Manage page '+' tag button**: Add the same '+' tag button (TagSelectorPopover) to manage page cards
6. **Colored tags**: All tags on both pages use DB-configured colors (from /settings/tags), not just hash-based colors

## Tasks

- TASK-1: Add tooltips to '+' buttons on artifact-browse-card.tsx
- TASK-2: Make tag/group badges clickable with filter application + focus ring styling
- TASK-3: Ensure Group filter available in collection Filters component
- TASK-4: Add TagSelectorPopover '+' button to artifact-operations-card.tsx (manage page)
- TASK-5: Ensure tags use DB-configured colors (check if tag objects include color field from API)
