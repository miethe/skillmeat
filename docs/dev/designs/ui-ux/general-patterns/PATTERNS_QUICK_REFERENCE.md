# SkillMeat Web Frontend - Patterns Quick Reference

## Artifact Card Component

**Location**: `/skillmeat/web/components/shared/unified-card.tsx`

```tsx
import { UnifiedCard } from '@/components/shared/unified-card';

<UnifiedCard
  item={artifact}
  selected={selected}
  selectable={true}
  onSelect={(checked) => setSelected(checked)}
  onClick={() => openDetail(artifact)}
  onEdit={() => editArtifact(artifact)}
  onDelete={() => deleteArtifact(artifact.id)}
  onDeploy={() => deployArtifact(artifact)}
/>
```

**Visual**: 4px left border with color by type + status badge + metadata + action menu

---

## Dropdown Menu Pattern

**Location**: `/skillmeat/web/components/ui/dropdown-menu.tsx` (base)

```tsx
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { MoreVertical } from 'lucide-react';

<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="icon" className="h-8 w-8">
      <MoreVertical className="h-4 w-4" />
      <span className="sr-only">Open menu</span>
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem onClick={handleEdit}>
      <Pencil className="mr-2 h-4 w-4" />
      Edit
    </DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem
      onClick={handleDelete}
      className="text-destructive focus:text-destructive"
    >
      <Trash2 className="mr-2 h-4 w-4" />
      Delete
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

## Deletion Confirmation Dialogs

### Pattern 1: Simple Dialog (Recommended for most cases)

```tsx
const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
const [isDeleting, setIsDeleting] = React.useState(false);

const handleDelete = async () => {
  setIsDeleting(true);
  try {
    await deleteItem();
    setShowDeleteDialog(false);
  } catch (error) {
    console.error('Failed to delete:', error);
  } finally {
    setIsDeleting(false);
  }
};

// In JSX:
<Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete {itemName}?</DialogTitle>
      <DialogDescription>
        This action cannot be undone. This will permanently delete the {itemType} "{itemName}".
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button
        variant="outline"
        onClick={() => setShowDeleteDialog(false)}
        disabled={isDeleting}
      >
        Cancel
      </Button>
      <Button
        variant="destructive"
        onClick={handleDelete}
        disabled={isDeleting}
      >
        {isDeleting ? 'Deleting...' : 'Delete'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Pattern 2: AlertDialog (For destructive actions with warnings)

```tsx
<AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle className="flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-destructive" />
        Delete {itemName}?
      </AlertDialogTitle>
      <AlertDialogDescription>
        <p>Are you sure you want to delete this item?</p>
        <p className="text-destructive mt-2">
          This will cascade delete {affectedCount} related items. This action cannot be undone.
        </p>
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel disabled={isDeleting}>
        Cancel
      </AlertDialogCancel>
      <AlertDialogAction
        onClick={handleDelete}
        disabled={isDeleting}
        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
      >
        {isDeleting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Deleting...
          </>
        ) : (
          'Delete'
        )}
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### Pattern 3: File Deletion Dialog (With file info display)

```tsx
<Dialog open={open} onOpenChange={setOpen}>
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
      <Button variant="outline" onClick={() => setOpen(false)} disabled={isDeleting}>
        Cancel
      </Button>
      <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
        {isDeleting ? 'Deleting...' : 'Delete File'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

## Collection/Deployment API Patterns

### Delete Collection
```typescript
import { deleteCollection } from '@/lib/api/collections';

const deleteCollectionMutation = useMutation({
  mutationFn: (collectionId: string) => deleteCollection(collectionId),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: collectionKeys.all });
  },
});

// Call:
await deleteCollectionMutation.mutateAsync(collectionId);
```

### Remove Artifact from Collection
```typescript
import { removeArtifactFromCollection } from '@/lib/api/collections';

export async function removeArtifactFromCollection(
  collectionId: string,
  artifactId: string
): Promise<void> {
  const response = await fetch(buildUrl(`/user-collections/${collectionId}/artifacts/${artifactId}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to remove artifact: ${response.statusText}`);
  }
}
```

### Undeploy Artifact from Project
```typescript
import { undeployArtifact } from '@/lib/api/deployments';

export async function undeployArtifact(
  data: ArtifactUndeployRequest
): Promise<ArtifactUndeployResponse> {
  const response = await fetch(buildUrl('/deploy/undeploy'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(`Failed to undeploy artifact: ${errorText}`);
  }

  return response.json();
}
```

---

## Hook Patterns for Deletion

### Collection Hook Pattern
```typescript
export function useDeleteCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (collectionId: string) => deleteCollection(collectionId),
    onSuccess: () => {
      // Invalidate both lists and individual items
      queryClient.invalidateQueries({ queryKey: collectionKeys.all });
    },
    onError: (error) => {
      console.error('[collections] Delete failed:', error);
    },
  });
}
```

### Deployment Hook Pattern
```typescript
export function useUndeployArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: undeployArtifact,
    onSuccess: (_, variables) => {
      // Invalidate all deployment queries for affected project
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.list(variables.project_path),
      });
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.summary(variables.project_path),
      });
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.lists(),
      });
    },
    onError: (error) => {
      console.error('[deployments] Undeploy failed:', error);
    },
  });
}
```

---

## Component Integration Example

### In EntityActions (Existing Pattern)
**File**: `/skillmeat/web/components/entity/entity-actions.tsx`

```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="icon" className="h-8 w-8">
      <MoreVertical className="h-4 w-4" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    {/* Other items */}
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
  </DropdownMenuContent>
</DropdownMenu>

{/* Dialog */}
<Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
  {/* ... dialog content ... */}
</Dialog>
```

---

## Common Icons

```typescript
import {
  MoreVertical,     // Menu trigger
  Trash2,           // Delete action
  Pencil,           // Edit action
  Rocket,           // Deploy action
  RefreshCw,        // Sync/update action
  FileText,         // View diff
  RotateCcw,        // Rollback action
  AlertTriangle,    // Warning indicator
  Loader2,          // Loading spinner
  Copy,             // Copy action
  Eye,              // View/visible
  EyeOff,           // Hidden/skip
  Info,             // Information
} from 'lucide-react';
```

---

## Key CSS Classes

```typescript
// Destructive styling
"text-destructive focus:text-destructive"
"bg-destructive text-destructive-foreground hover:bg-destructive/90"

// Button variants
variant="ghost"      // Minimal background
variant="outline"    // Border only
variant="destructive" // Red background

// Sizes
size="icon"          // Square button for icons
size="sm" | "lg"     // Size variants

// Colors
className="text-red-500"
className="bg-red-500/10"
className="border-red-500/20"
```

---

## Testing Checklist for Deletion Feature

- [ ] Menu item appears in dropdown
- [ ] Confirmation dialog shows on click
- [ ] Dialog title/description is clear
- [ ] Cancel button closes dialog
- [ ] Delete button triggers async operation
- [ ] Loading state shows during deletion
- [ ] Dialog closes on success
- [ ] Error message displays on failure
- [ ] Cache invalidates after successful deletion
- [ ] Toast notification appears (if implemented)
- [ ] Related items update/remove from UI

---

## Related Files by Feature

### Artifact Actions
- `skillmeat/web/components/entity/entity-actions.tsx` - Entity dropdown menu
- `skillmeat/web/components/discovery/ArtifactActions.tsx` - Discovery dropdown
- `skillmeat/web/components/deployments/deployment-actions.tsx` - Deployment dropdown

### Collections
- `skillmeat/web/lib/api/collections.ts` - API client
- `skillmeat/web/hooks/use-collections.ts` - React hooks
- `skillmeat/web/components/collection/collection-switcher.tsx` - UI

### Deployments
- `skillmeat/web/lib/api/deployments.ts` - API client
- `skillmeat/web/hooks/use-deployments.ts` - React hooks
- `skillmeat/web/components/deployments/deployment-card.tsx` - UI
