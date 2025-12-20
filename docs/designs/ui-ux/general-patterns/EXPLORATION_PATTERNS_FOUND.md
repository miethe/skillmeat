# SkillMeat Web Frontend - Pattern Exploration Results

**Date**: December 20, 2025
**Focus**: Artifact card components, deletion patterns, API relationships, dropdown menus

---

## 1. Artifact Card Components

### Primary Implementation: UnifiedCard
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/shared/unified-card.tsx`

The main artifact/entity card component that displays in grids and lists.

**Key Features**:
- **Type Detection**: Uses type guards to detect Entity vs Artifact types at runtime
- **Color-Coded Borders**: Left border (4px) with type-specific colors:
  - `skill` → blue-500
  - `command` → purple-500
  - `agent` → green-500
  - `mcp` → orange-500
  - `hook` → pink-500
- **Status Indicators**: Shows sync status (synced, modified, outdated, conflict)
- **Metadata Display**: Version, last updated (relative time), usage count
- **Tags**: Displays up to 3 tags with "+N more" indicator
- **Selection Checkbox**: Conditionally renders based on `selectable` prop
- **Action Menu**: Shows EntityActions dropdown for Entity types

**Props Interface**:
```typescript
interface UnifiedCardProps {
  item: Entity | Artifact;
  selected?: boolean;
  selectable?: boolean;
  onSelect?: (selected: boolean) => void;
  onClick?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onDeploy?: () => void;
  onSync?: () => void;
  onViewDiff?: () => void;
  onRollback?: () => void;
  mode?: 'selection' | 'browse'; // deprecated
}
```

**Usage Pattern**:
```tsx
import { UnifiedCard } from '@/components/shared/unified-card';

<UnifiedCard
  item={artifact}
  selected={true}
  selectable={true}
  onSelect={(checked) => updateSelection(checked)}
  onClick={() => openDetail(artifact)}
  onEdit={() => startEdit(artifact)}
  onDelete={() => deleteArtifact(artifact.id)}
/>
```

### Wrapper Components

**EntityCard** (file: `skillmeat/web/components/entity/entity-card.tsx`)
- Simple wrapper around UnifiedCard for Entity types
- Re-exports from UnifiedCard for consistency

---

## 2. Dropdown Menu Implementation

### Base Radix UI Component
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ui/dropdown-menu.tsx`

Radix UI dropdown with shadcn styling.

**Exported Components**:
- `DropdownMenu` - Root container
- `DropdownMenuTrigger` - Button that opens menu
- `DropdownMenuContent` - Menu content container
- `DropdownMenuItem` - Individual menu item
- `DropdownMenuSeparator` - Visual divider
- `DropdownMenuCheckboxItem` - Checkbox menu item
- `DropdownMenuRadioItem` - Radio button menu item
- Plus sub-menus, groups, labels, shortcuts

**Styling**:
- Animation: fade-in/out with zoom
- Width: min-w-[8rem]
- Border: 1px solid border color
- Portal: Renders outside DOM hierarchy
- Keyboard accessible: Tab navigation, Enter to activate

---

## 3. Deletion/Confirmation Dialog Patterns

### Pattern 1: Simple Deletion Dialog (EntityActions)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/entity-actions.tsx`

**Implementation**:
- Uses `Dialog` component from shadcn
- State: `showDeleteDialog` (boolean)
- Loading state: `isDeleting` (boolean)
- Dropdown trigger in actions menu with Trash2 icon
- Destructive styling: `className="text-destructive focus:text-destructive"`

**Code Pattern**:
```typescript
const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
const [isDeleting, setIsDeleting] = React.useState(false);

const handleDelete = async () => {
  if (!onDelete) return;
  setIsDeleting(true);
  try {
    await onDelete();
    setShowDeleteDialog(false);
  } catch (error) {
    console.error('Failed to delete entity:', error);
  } finally {
    setIsDeleting(false);
  }
};

// In JSX:
<Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete {entity.name}?</DialogTitle>
      <DialogDescription>
        This action cannot be undone. This will permanently delete the {entity.type} "{entity.name}".
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={isDeleting}>
        Cancel
      </Button>
      <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
        {isDeleting ? 'Deleting...' : 'Delete'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Pattern 2: AlertDialog for Destructive Actions (DeploymentActions)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/deployments/deployment-actions.tsx`

**Implementation**:
- Uses `AlertDialog` component (Radix AlertDialog for destructive actions)
- Darker overlay: `bg-black/80`
- Clear warning title and description
- Shows affected resource details (path, artifact count, etc.)
- Loading indicator during action

**Code Pattern**:
```typescript
<AlertDialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Remove Deployment?</AlertDialogTitle>
      <AlertDialogDescription>
        This will remove "{deployment.artifact_name}" from the project at
        <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">
          {deployment.artifact_path}
        </code>
        . This action cannot be undone.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel disabled={isRemoving}>Cancel</AlertDialogCancel>
      <AlertDialogAction
        onClick={handleRemove}
        disabled={isRemoving}
        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
      >
        {isRemoving ? 'Removing...' : 'Remove'}
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### Pattern 3: AlertDialog with Cascade Warning (DeleteSourceDialog)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/delete-source-dialog.tsx`

**Implementation**:
- Shows resource name (with owner/repo format)
- **Cascade warning**: Highlights secondary effects in destructive color
- Artifact count affected
- Uses mutation hook for async deletion
- Optional `onSuccess` callback

**Code Pattern**:
```typescript
<AlertDialogDescription className="space-y-2">
  <p>
    Are you sure you want to delete{' '}
    <strong className="text-foreground">
      {source.owner}/{source.repo_name}
    </strong>
    ?
  </p>
  <p className="text-destructive">
    This will also remove {source.artifact_count} artifact
    {source.artifact_count !== 1 ? 's' : ''} from the catalog. This
    action cannot be undone.
  </p>
</AlertDialogDescription>
```

### Pattern 4: File Deletion with Warning Alert (FileDeletionDialog)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/file-deletion-dialog.tsx`

**Implementation**:
- Uses `Dialog` (not AlertDialog)
- Includes warning Alert component with destructive styling
- Shows file name in code block for clarity
- Error state with error message display
- Icon: AlertTriangle (h-5 w-5 text-red-500)

**Code Pattern**:
```typescript
<Dialog open={open} onOpenChange={handleOpenChange}>
  <DialogContent className="sm:max-w-md">
    <DialogHeader>
      <DialogTitle className="flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-red-500" />
        Delete File
      </DialogTitle>
    </DialogHeader>

    <div className="space-y-4 py-4">
      <Alert variant="destructive" className="border-red-500/20 bg-red-500/10">
        <AlertDescription className="text-sm">
          <span className="font-medium">File to delete:</span>
          <br />
          <code className="mt-1 inline-block rounded bg-red-500/20 px-2 py-1 text-xs">
            {fileName}
          </code>
        </AlertDescription>
      </Alert>

      {error && (
        <Alert variant="destructive">
          <AlertDescription className="text-sm">{error}</AlertDescription>
        </Alert>
      )}
    </div>

    <DialogFooter>
      <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isDeleting}>
        Cancel
      </Button>
      <Button variant="destructive" onClick={handleConfirm} disabled={isDeleting}>
        {isDeleting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Deleting...
          </>
        ) : (
          'Delete File'
        )}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## 4. Action Dropdown Patterns

### EntityActions Dropdown
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/entity-actions.tsx`

**Menu Items**:
- Edit (Pencil icon) - Always shown if `onEdit` provided
- Deploy to Project (Rocket icon) - If `onDeploy` provided
- Sync to Collection (RefreshCw icon) - If `onSync` provided
- View Diff (FileText icon) - Only if status === 'modified' and `onViewDiff` provided
- Rollback to Collection (RotateCcw icon) - If status is 'modified'/'conflict' and `onRollback` provided
- ─── Separator ───
- Delete (Trash2 icon, destructive styling) - Shows confirmation dialog

**Trigger Button**:
```tsx
<Button variant="ghost" size="icon" className="h-8 w-8">
  <MoreVertical className="h-4 w-4" />
  <span className="sr-only">Open menu</span>
</Button>
```

### DeploymentActions Dropdown
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/deployments/deployment-actions.tsx`

**Menu Items**:
- Update to Latest (RefreshCw) - Only if status === 'outdated'
- View Diff (FileText) - Only if `local_modifications` exist
- View in Collection (Eye)
- Copy Path (Copy) - Shows "Copied!" feedback for 2 seconds
- ─── Separator ───
- Remove (Trash2, destructive)

### ArtifactActions Dropdown
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/discovery/ArtifactActions.tsx`

**Menu Items**:
- Import to Collection (Download) - Disabled if already imported
- Skip/Un-skip (Eye or EyeOff toggle)
- ─── Separator ───
- View Details (Info)
- Copy Source URL (Copy)

**Special Features**:
- Managed open state: `const [open, setOpen] = useState(false);`
- Closes menu after actions: `setOpen(false)`
- Toast notifications via `useToastNotification()`
- Clipboard API with fallback: `navigator.clipboard.writeText()` + textarea fallback

---

## 5. Collection/Project/Artifact Relationships

### API Endpoints

**Collections** (`lib/api/collections.ts`):
- `GET /api/v1/user-collections` - List collections
- `GET /api/v1/user-collections/{id}` - Get collection by ID
- `POST /api/v1/user-collections` - Create collection
- `PUT /api/v1/user-collections/{id}` - Update collection
- `DELETE /api/v1/user-collections/{id}` - Delete collection
- `POST /api/v1/user-collections/{id}/artifacts` - Add artifacts to collection (accepts `artifact_ids` array)
- `DELETE /api/v1/user-collections/{id}/artifacts/{artifact_id}` - Remove artifact from collection

**Deployments** (`lib/api/deployments.ts`):
- `POST /api/v1/deploy` - Deploy artifact to project
  - Payload: `ArtifactDeployRequest` (artifact_id, artifact_name, artifact_type, project_path, overwrite)
- `POST /api/v1/deploy/undeploy` - Remove artifact from project
  - Payload: `ArtifactUndeployRequest` (artifact_name, artifact_type, project_path)
- `GET /api/v1/deploy` - List deployments (optional: `project_path` query param)

### Type Relationships

**Entity** (deployed in a project):
```typescript
interface Entity {
  id: string;
  name: string;
  type: EntityType;
  description?: string;
  tags?: string[];
  status: 'synced' | 'modified' | 'outdated' | 'conflict';
  version: string;
  source: string;
  modifiedAt: string;
  projectPath: string;
  collection?: string;
}
```

**Artifact** (in collection):
```typescript
interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  version: string;
  source: string;
  status: string;
  updatedAt: string;
  metadata: {
    title: string;
    description: string;
    tags: string[];
  };
  usageStats: {
    usageCount: number;
  };
  upstreamStatus: {
    isOutdated: boolean;
  };
}
```

**Deployment**:
```typescript
interface ArtifactDeploymentInfo {
  artifact_name: string;
  artifact_type: string;
  artifact_path: string;
  project_path: string;
  sync_status: 'synced' | 'modified' | 'outdated' | 'unknown';
  deployed_at: string;
  status: 'active' | 'outdated' | 'unknown';
  local_modifications: boolean;
}
```

---

## 6. Hooks and State Management

### Collection Hooks (`hooks/use-collections.ts`)
```typescript
export function useCollections(): UseQueryResult<Collection[], Error>
export function useCreateCollection(): UseMutationResult<Collection, Error, CreateCollectionRequest>
export function useUpdateCollection(): UseMutationResult<Collection, Error, UpdateCollectionRequest>
export function useDeleteCollection(): UseMutationResult<void, Error, string>
export function useAddArtifactToCollection(): UseMutationResult<AddArtifactResponse, Error, AddArtifactRequest>
export function useRemoveArtifactFromCollection(): UseMutationResult<void, Error, RemoveArtifactRequest>
```

### Deployment Hooks (`hooks/use-deployments.ts`)
```typescript
export function useDeploymentList(projectPath?: string): UseQueryResult<ArtifactDeploymentListResponse, Error>
export function useDeployments(params?: DeploymentQueryParams): UseQueryResult<ArtifactDeploymentInfo[], Error>
export function useDeploymentSummary(projectPath?: string): UseQueryResult<DeploymentSummary, Error>
export function useDeployArtifact(): UseMutationResult<ArtifactDeploymentResponse, Error, ArtifactDeployRequest>
export function useUndeployArtifact(): UseMutationResult<ArtifactUndeployResponse, Error, ArtifactUndeployRequest>
export function useRefreshDeployments(): (projectPath?: string) => void
```

**Query Key Structure**:
```typescript
const deploymentKeys = {
  all: ['deployments'],
  lists: () => [...deploymentKeys.all, 'list'],
  list: (projectPath?: string) => [...deploymentKeys.lists(), { projectPath }],
  summaries: () => [...deploymentKeys.all, 'summary'],
  summary: (projectPath?: string) => [...deploymentKeys.summaries(), { projectPath }],
  filtered: (params?: DeploymentQueryParams) => [...deploymentKeys.lists(), 'filtered', params],
};
```

---

## 7. Dialog Hierarchy & Component Structure

### Dialog Components Available

**Dialog** (`components/ui/dialog.tsx`) - General purpose modal:
- `Dialog` - Root
- `DialogContent` - Modal box with close button (X in top-right)
- `DialogHeader` - Header section with flex layout
- `DialogTitle` - Heading
- `DialogDescription` - Subtitle/details
- `DialogFooter` - Button container (flex-row on desktop, flex-col on mobile)

**AlertDialog** (`components/ui/alert-dialog.tsx`) - Destructive action confirmation:
- `AlertDialog` - Root
- `AlertDialogContent` - Darker overlay styling
- `AlertDialogHeader` - Header section
- `AlertDialogTitle` - Heading
- `AlertDialogDescription` - Description
- `AlertDialogFooter` - Button container
- `AlertDialogAction` - Destructive button (uses button styling)
- `AlertDialogCancel` - Cancel button (outline styling)

### Styling Patterns

**Destructive Button**:
```tsx
className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
```

**Disabled States**:
```tsx
disabled={isDeleting} // Prevents interactions during async operations
```

**Loading Indicators**:
```tsx
{isDeleting ? (
  <>
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    Deleting...
  </>
) : (
  'Delete'
)}
```

---

## 8. Card Grid/List Components

### Artifact Grid
**File**: `skillmeat/web/components/collection/artifact-grid.tsx`
- Displays UnifiedCard components in grid layout
- Shows artifacts with selection checkboxes
- Action menus in card corners

### Artifact List
**File**: `skillmeat/web/components/collection/artifact-list.tsx`
- Alternative to grid layout
- Uses same UnifiedCard component
- Row-based layout with alternating backgrounds

### Grouped Artifact View
**File**: `skillmeat/web/components/collection/grouped-artifact-view.tsx`
- Groups artifacts by category/type
- Collapsible sections
- Uses UnifiedCard for each artifact

---

## 9. Toast Notifications

**Hook**: `hooks/use-toast-notification.ts`

**Usage Pattern**:
```typescript
const { showSuccess, showError } = useToastNotification();

// Success notification
showSuccess('Source URL copied to clipboard');

// Error notification
showError('Failed to copy to clipboard');
```

Commonly used for:
- Copy-to-clipboard feedback
- Action completion messages
- Error messages from hooks/API calls

---

## 10. Key Component Locations Summary

| Component | Path | Purpose |
|-----------|------|---------|
| UnifiedCard | `components/shared/unified-card.tsx` | Primary card for artifacts/entities |
| EntityCard | `components/entity/entity-card.tsx` | Entity-specific card wrapper |
| EntityActions | `components/entity/entity-actions.tsx` | Dropdown menu for entity operations |
| DeploymentActions | `components/deployments/deployment-actions.tsx` | Dropdown for deployment operations |
| ArtifactActions | `components/discovery/ArtifactActions.tsx` | Dropdown for discovered artifacts |
| FileDeletionDialog | `components/entity/file-deletion-dialog.tsx` | File deletion confirmation |
| DeleteSourceDialog | `components/marketplace/delete-source-dialog.tsx` | Source deletion with cascade warning |
| DropdownMenu | `components/ui/dropdown-menu.tsx` | Radix-based dropdown primitive |
| Dialog | `components/ui/dialog.tsx` | General modal dialog |
| AlertDialog | `components/ui/alert-dialog.tsx` | Destructive action confirmation |

---

## 11. Recommended Patterns for New Features

### For Artifact Deletion Feature

**1. Add to EntityActions dropdown** (most common pattern):
```tsx
{onDelete && (
  <>
    <DropdownMenuSeparator />
    <DropdownMenuItem
      onClick={() => setShowDeleteDialog(true)}
      className="text-destructive focus:text-destructive"
    >
      <Trash2 className="mr-2 h-4 w-4" />
      Delete
    </DropdownMenuItem>
  </>
)}
```

**2. Confirmation Dialog (choose one)**:
- Use `Dialog` for simpler cases (EntityActions pattern)
- Use `AlertDialog` for destructive actions with warnings (DeploymentActions pattern)

**3. Loading State**:
```typescript
const [isDeleting, setIsDeleting] = React.useState(false);

const handleDelete = async () => {
  setIsDeleting(true);
  try {
    await onDelete();
    setShowDeleteDialog(false);
  } catch (error) {
    console.error('Failed to delete:', error);
  } finally {
    setIsDeleting(false);
  }
};
```

**4. Cache Invalidation** (in hooks):
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: artifactKeys.all });
  queryClient.invalidateQueries({ queryKey: artifactKeys.lists() });
}
```

---

## Files Analyzed

Total files analyzed: **20+**

### Core Components
- `skillmeat/web/components/shared/unified-card.tsx`
- `skillmeat/web/components/entity/entity-actions.tsx`
- `skillmeat/web/components/entity/entity-card.tsx`
- `skillmeat/web/components/discovery/ArtifactActions.tsx`
- `skillmeat/web/components/deployments/deployment-actions.tsx`
- `skillmeat/web/components/marketplace/delete-source-dialog.tsx`
- `skillmeat/web/components/entity/file-deletion-dialog.tsx`

### UI Primitives
- `skillmeat/web/components/ui/dropdown-menu.tsx`
- `skillmeat/web/components/ui/dialog.tsx`
- `skillmeat/web/components/ui/alert-dialog.tsx`

### API Clients
- `skillmeat/web/lib/api/collections.ts`
- `skillmeat/web/lib/api/deployments.ts`

### Hooks
- `skillmeat/web/hooks/use-deployments.ts`
- `skillmeat/web/hooks/use-collections.ts`

---

## Conclusion

The SkillMeat web frontend has well-established patterns for:
1. **Card display** - Unified component with type-specific colors
2. **Actions** - Dropdown menus with conditional items
3. **Deletion** - Multiple dialog patterns depending on complexity
4. **API integration** - TanStack Query with hierarchical cache keys
5. **Async operations** - Loading states and error handling

These patterns should be followed when implementing new artifact deletion features.
