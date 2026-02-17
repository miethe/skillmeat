# Two-Pane Groups View Redesign

**Status**: completed
**Branch**: feat/two-pane-groups-view
**Scope**: Frontend only (web)
**Estimated effort**: 1-2 sessions

## Context

The current "grouped" view mode (`GroupedArtifactView`) uses collapsible sections to show artifacts organized by group. Two issues:

1. **Bug**: Dragging artifacts from "Ungrouped" into a group silently fails — the `handleDragEnd` condition at line ~539 blocks mutations when `sourceGroupId === 'ungrouped'`
2. **Gap**: Artifacts can belong to multiple groups (data model supports it via `GroupArtifact` junction table), but the view only shows each artifact in its first group

The fix is a full redesign to a two-pane layout that properly supports multi-group membership and intuitive drag-and-drop.

## Design

### Two-Pane Layout

```
+---------------------+----------------------------------------+
| GROUP SIDEBAR       | ARTIFACT PANE                          |
| (280px, fixed)      | (flex-1)                               |
|                     |                                        |
| [*] All Artifacts   | [PaneHeader: "Development Tools (12)"] |
| [ ] Ungrouped       |                                        |
| ─────────────       | [RemoveFromGroupZone] (if viewing group)|
| [●] Dev Tools    5  |                                        |
| [●] Testing     3   | [MiniArtifactCard] ≡ name | desc | badges |
| [●] Deploy      2   | [MiniArtifactCard] ≡ name | desc | badges |
|                     | [MiniArtifactCard] ≡ name | desc | badges |
| [+ Create Group]    |                                        |
+---------------------+----------------------------------------+
```

**Left Pane (GroupSidebar)**:
- "All Artifacts" and "Ungrouped" special selections
- Each group row: color dot, icon, name, artifact count
- Groups are **droppable targets** -- drag an artifact here to ADD it to that group
- Selected item highlighted
- "Create Group" button at bottom

**Right Pane (ArtifactPane)**:
- Header showing current selection name + count
- **MiniArtifactCard** list -- compact cards that are draggable and clickable
- When viewing a specific group: **RemoveFromGroupDropZone** appears at top
- Card shows: drag handle, type icon, name, 1-line description, group badges, tag badges

### Key Semantic: ADD, Not MOVE

Since artifacts can be in multiple groups, dragging to a group in the sidebar **adds** the artifact (via `useAddArtifactToGroup`). Removal is explicit via the "Remove from Group" drop zone. This replaces the current `useMoveArtifactToGroup` semantic.

### Data Sources by Selection

| Selection | Source | Sortable? |
|-----------|--------|-----------|
| All Artifacts | `props.artifacts` from parent | No |
| Ungrouped | `props.artifacts` filtered by no group membership | No |
| Specific Group | `useGroupArtifacts(groupId)` cross-ref'd with `props.artifacts` | Yes (within-group reorder) |

### Responsive Behavior

On screens below `md` breakpoint: sidebar collapses to a `Select` dropdown at the top of the view, with the artifact list below it. Full-width artifact cards.

## Component Architecture

```
GroupedArtifactView (container, DndContext)
  |
  +-- GroupSidebar (left pane, ~280px)
  |     +-- SidebarItem "All Artifacts" (clickable)
  |     +-- SidebarItem "Ungrouped" (clickable)
  |     +-- Separator
  |     +-- DroppableGroupItem[] (each group: icon, name, count, color dot)
  |     +-- "Create Group" button
  |
  +-- ArtifactPane (right pane, flex-1)
  |     +-- PaneHeader (shows selected group name + count)
  |     +-- RemoveFromGroupDropZone (conditional, only for specific group)
  |     +-- MiniArtifactCard[] (scrollable list, draggable)
  |     +-- EmptyState (when no artifacts in selection)
  |
  +-- DragOverlay (portal, shows MiniArtifactCard preview)
```

## DnD Architecture

**DndContext setup** (in `grouped-artifact-view.tsx`):
- Sensors: PointerSensor (distance: 8), KeyboardSensor
- Collision: closestCenter

**Droppable IDs and data**:
- Left pane group items: `id="group-drop-{groupId}"`, `data={ type: 'group-sidebar', groupId }`
- Remove zone: `id="remove-from-group"`, `data={ type: 'remove-zone' }`
- Right pane artifacts (sortable): `id=artifact.id`, `data={ type: 'artifact', artifactId, groupId }`

**DragEnd logic**:
```
if (dropped on group-sidebar item):
  if artifact not already in that group:
    useAddArtifactToGroup({ groupId: target, artifactId: dragged })
    toast.success("Added to [group name]")
  else:
    toast.info("Already in [group name]")

if (dropped on remove-zone):
  useRemoveArtifactFromGroup({ groupId: currentGroup, artifactId: dragged })
  toast.success("Removed from [group name]")

if (dropped on another artifact in same group -- reorder):
  useReorderArtifactsInGroup({ groupId, artifactIds: newOrder })
```

## File Changes

### New Files (3)

1. **`skillmeat/web/components/collection/group-sidebar.tsx`**
   - Left pane with "All", "Ungrouped", and group list
   - Each group item uses `useDroppable` from @dnd-kit
   - Shows `isOver` highlight when artifact dragged over
   - Reuses `ICON_MAP` and `resolveColorHex` from `lib/group-constants.ts`

2. **`skillmeat/web/components/collection/mini-artifact-card.tsx`**
   - Compact card: drag handle, type icon, name, description (1-line), group badges, type badge
   - `DraggableMiniArtifactCard` wrapper uses `useSortable` from @dnd-kit
   - Click handler opens `ArtifactDetailsModal`
   - Reuses `ArtifactGroupBadges` from `artifact-group-badges.tsx`

3. **`skillmeat/web/components/collection/remove-from-group-zone.tsx`**
   - `useDroppable` target with destructive styling
   - Shows "Remove from [Group Name]" with trash icon
   - Red/destructive highlight on `isOver`
   - Only rendered when a specific group is selected

### Rewritten File (1)

4. **`skillmeat/web/components/collection/grouped-artifact-view.tsx`**
   - Full rewrite -- assembles GroupSidebar + ArtifactPane within single `DndContext`
   - State: `selectedPane: 'all' | 'ungrouped' | string` (groupId)
   - DnD sensors: PointerSensor (8px distance) + KeyboardSensor
   - `onDragEnd` logic (see DnD Architecture above)
   - Same `GroupedArtifactViewProps` interface so parent needs no changes

### No Changes Needed

5. **`skillmeat/web/app/collection/page.tsx`** -- same props interface preserved
6. **`skillmeat/web/hooks/use-groups.ts`** -- all hooks exist: `useGroups`, `useGroupArtifacts`, `useAddArtifactToGroup`, `useRemoveArtifactFromGroup`, `useReorderArtifactsInGroup`
7. **`skillmeat/web/hooks/use-artifact-groups.ts`** -- used by `ArtifactGroupBadges`
8. **`skillmeat/web/components/collection/artifact-group-badges.tsx`** -- reused inside MiniArtifactCard
9. **`skillmeat/web/lib/group-constants.ts`** -- `resolveColorHex`, `ICON_MAP`

## Implementation Sequence

**Batch 1 (parallel -- 3 agents)**:
- Agent A: Create `mini-artifact-card.tsx` with `DraggableMiniArtifactCard`
- Agent B: Create `group-sidebar.tsx` with droppable group items
- Agent C: Create `remove-from-group-zone.tsx`

**Batch 2 (sequential -- depends on Batch 1)**:
- Rewrite `grouped-artifact-view.tsx` assembling all pieces with DndContext, DnD handlers, state management

**Batch 3 (parallel)**:
- Polish: responsive collapse, empty states, loading skeletons
- Tests: update `grouped-artifact-view.test.tsx`

## Key Patterns to Follow

- **DnD pattern**: Follow existing `@dnd-kit` usage in current `grouped-artifact-view.tsx`
- **Card pattern**: Follow `ArtifactBrowseCard` structure from `artifact-browse-card.tsx`
- **Group constants**: Use `resolveColorHex` and `ICON_MAP` from `lib/group-constants.ts`
- **Badge pattern**: Reuse `ArtifactGroupBadges` component from `artifact-group-badges.tsx`
- **Toast pattern**: Use `sonner` toast for success/info messages (existing pattern)

## Verification

1. `pnpm type-check` -- no new type errors
2. `pnpm build` -- successful build
3. Manual testing:
   - Select groups in sidebar, verify correct artifacts appear
   - Drag artifact to sidebar group -> added (verify via group badges updating)
   - Drag artifact to "Remove from Group" zone -> removed
   - Drag within group list -> reorder persists
   - Click card -> ArtifactDetailsModal opens
   - Check "All Artifacts" and "Ungrouped" views show correct sets
   - Verify artifact appearing in multiple groups shows in each when selected
   - Mobile responsive: sidebar collapses to dropdown
