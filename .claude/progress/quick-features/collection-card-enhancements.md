---
type: quick-feature
status: completed
feature: Collection Card Enhancements (Group Dialog + Tag/Group Add Buttons)
created: 2026-02-13
tasks:
- id: QF-1
  title: 'Enhance AddToGroupDialog: taller + group badges'
  status: in-progress
  assigned_to: ui-engineer-enhanced
- id: QF-2
  title: Add '+' buttons and tag selector popover to artifact cards
  status: in-progress
  assigned_to: ui-engineer-enhanced
schema_version: 2
doc_type: quick_feature
feature_slug: collection-card-enhancements
---

# Collection Card Enhancements

## Scope
3 related UI enhancements to artifact cards on the /collection page:

### QF-1: Enhance Add to Group Dialog
- Make dialog dynamically taller (prefer showing more groups)
- Show group badge (color + icon) next to each group name and count
- Use existing `ICON_MAP` and `COLOR_HEX_BY_TOKEN` from `lib/group-constants.ts`

### QF-2: Add '+' Buttons + Tag Selector Popover
- Add '+' buttons next to Tags and Groups badges on artifact cards
- Groups '+' opens existing AddToGroupDialog
- Tags '+' opens new inline tag selector popover with:
  - Colored tag badges (reuse TagBadge patterns)
  - Click to add/remove tags dynamically
  - Inline creation of new tags by typing
  - Clean animation, consistent with existing design system

## Files
- `skillmeat/web/components/collection/add-to-group-dialog.tsx` (modify)
- `skillmeat/web/components/collection/artifact-browse-card.tsx` (modify)
- `skillmeat/web/components/collection/artifact-group-badges.tsx` (modify - add '+' button)
- New: `skillmeat/web/components/collection/tag-selector-popover.tsx`
