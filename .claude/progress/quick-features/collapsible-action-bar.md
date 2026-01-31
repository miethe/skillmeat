# Quick Feature: Collapsible Action Bar for CLI Commands

**Status**: completed
**Created**: 2026-01-31
**Scope**: Move CLI Deploy Command from modal header to collapsible bottom action bar

## Summary

Move the `CliCommandSection` from the top of the artifact modal (above tabs) to a collapsible action bar at the bottom. The action bar should:
- Be positioned at the bottom of the modal
- Use Radix Collapsible component
- Be visible on all tabs EXCEPT "Contents" and "Sync Status"
- Remember collapsed/expanded state during the session

## Implementation Tasks

### TASK-1: Create CollapsibleActionBar Component
- **Files**: Create `skillmeat/web/components/entity/collapsible-action-bar.tsx`
- **Requirements**:
  - Wrap CliCommandSection in Collapsible from shadcn/ui
  - Closed state: Compact bar (~48-56px) with "CLI Deploy Command" label and ChevronUp icon
  - Open state: Reveals full CliCommandSection with select, code display, copy button
  - Styling per design spec: border-t, bg-background, hover:bg-accent
  - Animation for height transition
  - Keyboard accessible (Enter/Space toggles)

### TASK-2: Update unified-entity-modal.tsx
- **Files**: Modify `skillmeat/web/components/entity/unified-entity-modal.tsx`
- **Requirements**:
  - Remove CliCommandSection from current position (lines 1697-1703)
  - Add CollapsibleActionBar at bottom of modal
  - Conditionally render based on activeTab (hide for "contents" and "sync" tabs)
  - Position in modal footer slot

## Files Changed

| File | Type | Change |
|------|------|--------|
| `components/entity/collapsible-action-bar.tsx` | Create | New collapsible wrapper component |
| `components/entity/unified-entity-modal.tsx` | Modify | Move CLI section to bottom, add tab filtering |

## Design Reference

See: `docs/project_plans/design-specs/collapsible-action-bar.md`
