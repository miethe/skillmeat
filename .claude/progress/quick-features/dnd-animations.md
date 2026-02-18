---
feature: dnd-animations
status: completed
created: 2026-02-16
scope: frontend
files_affected:
  - skillmeat/web/components/collection/grouped-artifact-view.tsx
  - skillmeat/web/components/collection/mini-artifact-card.tsx
  - skillmeat/web/components/collection/group-sidebar.tsx
  - skillmeat/web/components/collection/remove-from-group-zone.tsx
  - skillmeat/web/tailwind.config.js
tasks:
  - id: DND-1
    title: "Shrink + fade drag overlay and add drop-into-group animation"
    status: pending
    assigned_to: ui-engineer-enhanced
  - id: DND-2
    title: "Group sidebar drop success animation (checkmark + count increment)"
    status: pending
    assigned_to: ui-engineer-enhanced
  - id: DND-3
    title: "Poof animation for remove-from-group drop"
    status: pending
    assigned_to: ui-engineer-enhanced
---

# Quick Feature: Drag-and-Drop Animations for Groups View

## Summary

Enhance the DnD experience in the two-pane Groups view with polished animations:

1. **Drag preview**: Card shrinks (~60% scale) and becomes semi-transparent (~70% opacity) so the user can see which group they're targeting while still reading the card name
2. **Drop into group**: Card animates shrinking/fading into the group item (disappears into it)
3. **Group success feedback**: Checkmark appears over the artifact count badge, then count visually increments by 1
4. **Remove poof**: When dragging out of a group (to remove zone), a "poof" particle/burst animation plays, then count decrements

## Files

- `grouped-artifact-view.tsx` — DragOverlay customization, drop animation state
- `mini-artifact-card.tsx` — Drag overlay styling
- `group-sidebar.tsx` — Drop success animation (checkmark + count)
- `remove-from-group-zone.tsx` — Poof animation
- `tailwind.config.js` — New keyframe animations
