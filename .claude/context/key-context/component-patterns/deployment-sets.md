# Deployment Sets Components

Feature-specific components for deployment set management in `components/deployment-sets/`. Follow established patterns used in artifact and group features.

## DeploymentSetCard

Clickable card displaying deployment set metadata and member summary.

**Source**: `skillmeat/web/components/deployment-sets/deployment-set-card.tsx`

**Props:**
- `deploymentSet: DeploymentSet` - Set object with name, description, members, tags, color, icon
- `onSelect?: (id: string) => void` - Optional click handler to open details modal
- `className?: string` - Optional styling override

**Behavior:**
- Full-card click triggers selection (opens `DeploymentSetDetailsModal`)
- Displays set color indicator (square or circle badge)
- Shows set icon if available
- Renders tags using unified tag system (matches artifact/group tagging)
- Shows member count summary
- Supports hover state and focus indicators for keyboard navigation

**Related Pattern:**
- Follows `ArtifactCard` structure from collections feature
- Uses same tag rendering as `GroupCard`

**Usage:**
```typescript
import { DeploymentSetCard } from '@/components/deployment-sets/deployment-set-card';

<DeploymentSetCard
  deploymentSet={set}
  onSelect={handleSelect}
/>
```

## DeploymentSetDetailsModal

Tabbed modal for viewing and editing deployment set details, matching `ArtifactDetailsModal` pattern.

**Source**: `skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx`

**Tabs:**
1. **Overview** - Set name, description, color/icon metadata
2. **Members** - Listed members (artifacts, groups, sets)
3. **Groups** - Groups containing this set

**Features:**
- **Inline editing:** Name and description editable with blur save
- **Header actions:** Batch deploy button, edit dropdown, delete confirmation
- **Colored tag display** unified with artifact tag system
- **Mutation triggers:** Save/delete operations invalidate relevant queries via `useQueryClient()`

**Implementation Pattern:**
- Similar to `ArtifactDetailsModal` but for deployment sets
- Tab-based organization with consistent styling
- Maintains edit state separately from display state

**Usage:**
```typescript
import { DeploymentSetDetailsModal } from '@/components/deployment-sets/deployment-set-details-modal';

<DeploymentSetDetailsModal
  open={open}
  onOpenChange={setOpen}
  deploymentSet={selectedSet}
/>
```

## MiniArtifactCard

Compact artifact card used in member selection dialogs (e.g., `AddMemberDialog`).

**Source**: `skillmeat/web/components/deployment-sets/mini-artifact-card.tsx`

**Props:**
- `artifact: Artifact` - Artifact to display
- `selected?: boolean` - Visual selection indicator
- `onSelect: (id: string) => void` - Selection callback
- `className?: string` - Optional styling override

**Behavior:**
- Minimal visual footprint (single row or compact grid item)
- Shows artifact name, type badge
- Visual indicator when already selected (checkmark or highlight)
- Supports click and Enter/Space keyboard selection
- No description or metadata (for density)

**Used in:**
- `AddMemberDialog` artifacts tab
- Multi-select scenarios where space is constrained

**Usage:**
```typescript
import { MiniArtifactCard } from '@/components/deployment-sets/mini-artifact-card';

<div className="grid grid-cols-2 gap-2">
  {artifacts.map((artifact) => (
    <MiniArtifactCard
      key={artifact.id}
      artifact={artifact}
      selected={selectedIds.includes(artifact.id)}
      onSelect={handleSelect}
    />
  ))}
</div>
```

## AddMemberDialog

Three-tab dialog for selecting members to add to a deployment set.

**Source**: `skillmeat/web/components/deployment-sets/add-member-dialog.tsx`

**Tabs:**
1. **Artifacts** - Search/filter artifacts (skills, commands, agents, etc.)
2. **Groups** - Search/filter groups
3. **Sets** - Search/filter other deployment sets

**Features:**
- Per-tab search and type filtering
- Visual selection state (checkmarks, highlighting)
- MiniArtifactCard grid for artifact selection
- Circular reference validation before submission
  - Prevents adding a set to itself
  - Prevents adding a set that already contains this set
- Batch addition with single submit (add multiple members at once)

**Validation Logic:**
```typescript
// Before allowing member addition
const canAddMember = (memberId: string, targetSetId: string) => {
  // Check if targetSetId is already in the dependency chain
  return !isMemberInSet(memberId, targetSetId);
};
```

**Implementation Pattern:**
- Similar structure to search modals used in artifact linking
- Tab-based organization for different member types
- Maintains selection state within modal session
- Submit triggers mutation to add members batch

**Usage:**
```typescript
import { AddMemberDialog } from '@/components/deployment-sets/add-member-dialog';

<AddMemberDialog
  open={open}
  onOpenChange={setOpen}
  deploymentSetId={setId}
  onMembersAdded={handleMembersAdded}
/>
```
