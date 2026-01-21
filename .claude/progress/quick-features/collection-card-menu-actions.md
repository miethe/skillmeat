# Quick Feature: Collection Card Menu Actions

**Status**: completed
**Created**: 2025-01-15
**Files**: `skillmeat/web/app/collection/page.tsx`

## Problem

When viewing artifacts from the /collection page, clicking the meatballs menu "Add to Collection" or "Manage Groups" buttons has no effect. The handlers are not connected.

## Analysis

**Current State**:
- `ArtifactGrid` and `ArtifactList` components accept `onMoveToCollection` and `onManageGroups` props
- Collection page only passes `onEdit` and `onDelete` handlers
- `MoveCopyDialog` exists and works in `UnifiedEntityModal`
- `ManageGroupsDialog` exists but needs wiring

**Root Cause**: Missing handler implementations and dialog state in collection page.

## Solution

### Task 1: Wire "Add to Collection" Action
1. Add state for MoveCopyDialog: `showMoveCopyDialog`, `artifactForCollection`
2. Create `handleMoveToCollection` handler
3. Pass handler to `ArtifactGrid` and `ArtifactList`
4. Add `MoveCopyDialog` component to page

### Task 2: Wire "Manage Groups" Action
1. Add state for ManageGroupsDialog: `showGroupsDialog`, `artifactForGroups`
2. Create `handleManageGroups` handler
3. Pass handler to `ArtifactGrid` and `ArtifactList`
4. Add `ManageGroupsDialog` component to page

## Scope

- **Files affected**: 1 (`collection/page.tsx`)
- **Complexity**: Low - existing components, just wiring
- **Design work**: None - dialogs already exist

## Progress

- [x] Exploration complete
- [x] Add to Collection handler - wired MoveCopyDialog
- [x] Add to Group - created AddToGroupDialog, wired to collection page
- [x] Quality gates - build passes
- [x] Documented refactor scope for All Collections support

## Implementation Details

**Changes made**:

1. **`components/collection/artifact-grid.tsx`** - Changed menu label from "Manage Groups" to "Add to Group"
2. **`components/collection/artifact-list.tsx`** - Changed menu label from "Manage Groups" to "Add to Group"
3. **Created `components/collection/add-to-group-dialog.tsx`** - New dialog for adding artifact to groups:
   - Multi-select checkbox list of groups
   - Fetches groups for the collection using `useGroups()`
   - Calls `useAddArtifactToGroup()` for each selected group
   - Empty state with "Create a group" action
4. **`app/collection/page.tsx`**:
   - Changed import from `ManageGroupsDialog` to `AddToGroupDialog`
   - Updated dialog component to pass `artifact` prop
   - Added `onSuccess` callback for cache invalidation

**Behavior notes**:
- "Add to Collection" opens MoveCopyDialog for any artifact in any view
- "Add to Group" only works when viewing a specific collection (disabled in "All Collections" view)

---

## Refactor Scope: Groups in "All Collections" View

### Current Limitation

"Add to Group" is disabled in "All Collections" view because groups are scoped to individual collections.

**Data Model Constraint**:
```typescript
interface Group {
  id: string;
  collection_id: string;  // Required - groups belong to ONE collection
  // ...
}
```

### Why This Is Non-Trivial

When viewing "All Collections", an artifact may belong to multiple collections, each with their own groups. The question becomes: **which collection's groups should we show?**

### Refactor Options

| Option | Complexity | User Experience | Changes Required |
|--------|------------|-----------------|------------------|
| **A. First collection** | Low | Arbitrary, confusing | Frontend only |
| **B. Two-step selection** | Medium | Clear but more clicks | Frontend only |
| **C. Unified group list** | Medium-High | Flexible but needs disambiguation | Frontend + API |
| **D. Global groups** | High | Most flexible | Database + API + Frontend |

#### Option A: Use Artifact's First Collection (Not Recommended)
- Show groups from the first collection the artifact belongs to
- **Pros**: Simple to implement
- **Cons**: Arbitrary, user doesn't know which collection's groups are shown

#### Option B: Two-Step Selection (Recommended for MVP)
- When clicking "Add to Group" in All Collections view:
  1. First show a collection picker (only collections this artifact belongs to)
  2. Then show that collection's groups
- **Pros**: Explicit, user knows context
- **Cons**: Extra click, slightly more complex UI
- **Effort**: ~1-2 hours frontend work

**Implementation sketch**:
```tsx
// In AddToGroupDialog, if no collectionId provided:
if (!collectionId && artifact.collections?.length) {
  // Show collection picker first
  return <CollectionPicker collections={artifact.collections} onSelect={setSelectedCollection} />;
}
// Then show groups for selected collection
```

#### Option C: Unified Group List with Collection Context (Future Enhancement)
- Show ALL groups from ALL collections the artifact belongs to
- Display as: "Group Name (Collection Name)"
- **Pros**: All options visible at once
- **Cons**: Potential name collision confusion, requires API changes to fetch multiple collections' groups in one call
- **Effort**: ~4-6 hours (API + frontend)

#### Option D: Global Groups (Major Refactor)
- Make groups collection-agnostic (remove `collection_id` requirement)
- Groups become a top-level concept alongside collections
- **Pros**: Maximum flexibility, cleaner mental model
- **Cons**: Major database migration, API redesign, UI redesign
- **Effort**: ~2-4 days

### Recommendation

1. **Short-term**: Keep current behavior (disabled in All Collections)
2. **MVP Enhancement**: Implement Option B (two-step selection) when demand exists
3. **Future**: Consider Option C or D based on user feedback

### Design Work Required

For Option B (two-step selection):
- New `CollectionPickerStep` component within `AddToGroupDialog`
- Conditional rendering based on whether `collectionId` is provided
- UI for showing which collection's groups are being displayed

For Option C or D: More significant design work needed for:
- How to disambiguate same-named groups across collections
- Whether to support cross-collection group membership
- How global groups would integrate with collection filtering
