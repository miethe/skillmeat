# Entity Components

Components for artifact and entity lifecycle management in the SkillMeat web UI.

## ArtifactDeletionDialog

Multi-step confirmation dialog for deleting artifacts from collections and projects with flexible deletion options.

### Overview

The `ArtifactDeletionDialog` provides a comprehensive deletion workflow that allows users to:

- **Remove from Collection**: Delete the artifact from the personal collection
- **Undeploy from Projects**: Remove artifact deployments from one or more projects
- **Delete Deployments**: Permanently delete deployment metadata and files from the filesystem (with warning)

The dialog is context-aware and displays only relevant options based on where the deletion was initiated (collection or project context).

### Props Interface

```typescript
interface ArtifactDeletionDialogProps {
  /** Artifact to delete */
  artifact: Artifact;

  /** Whether dialog is open */
  open: boolean;

  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;

  /** Context where delete was initiated from ('collection' or 'project') */
  context?: 'collection' | 'project';

  /** Project path if initiated from project context */
  projectPath?: string;

  /** Collection ID if initiated from collection context */
  collectionId?: string;

  /** Success callback - invoked after successful deletion */
  onSuccess?: () => void;

  /** Error callback - invoked on deletion failure */
  onError?: (error: Error) => void;
}
```

### Features

#### Deletion Options

1. **Delete from Collection** (context-dependent)
   - Shown only when `context='collection'`
   - Removes artifact from the user's collection
   - Enabled by default in collection context

2. **Delete from Projects** (conditional)
   - Shows count of deployments found
   - Allows selective project deselection
   - Provides "Select All / Deselect All" toggle
   - Scrollable list when 5+ projects

3. **Delete Deployments** (destructive)
   - Visually distinguished with red styling and warning icon
   - Shows deployment file paths with deployment dates
   - Requires explicit confirmation via checkbox
   - Includes prominent filesystem warning

#### Deployment Management

- Auto-fetches all deployments for the artifact
- Displays unique project paths from deployments
- Supports granular selection of specific projects and deployments
- Shows loading states while fetching deployment data

#### Error Handling

- Graceful partial failure handling (some operations may fail while others succeed)
- Toast notifications with operation summary
- Warning toast when partial failures occur
- Error callback for application-level handling

### Usage Examples

#### Basic Usage from EntityActions

```tsx
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { useState } from 'react';

export function EntityActions({ artifact }) {
  const [showDeletionDialog, setShowDeletionDialog] = useState(false);

  return (
    <>
      <button onClick={() => setShowDeletionDialog(true)}>Delete</button>

      <ArtifactDeletionDialog
        artifact={artifact}
        open={showDeletionDialog}
        onOpenChange={setShowDeletionDialog}
        context="collection"
        onSuccess={() => {
          // Refresh data or navigate away
          router.refresh();
        }}
      />
    </>
  );
}
```

#### Usage from Collection Browser with Project Context

```tsx
<ArtifactDeletionDialog
  artifact={artifact}
  open={showDeleteDialog}
  onOpenChange={setShowDeleteDialog}
  context="project"
  projectPath="/path/to/project/.claude"
  onSuccess={() => {
    // Refresh project artifacts list
    queryClient.invalidateQueries({ queryKey: ['artifacts', projectPath] });
  }}
  onError={(error) => {
    console.error('Deletion failed:', error);
  }}
/>
```

#### Usage with Full Configuration

```tsx
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

<ArtifactDeletionDialog
  artifact={selectedArtifact}
  open={deleteDialogOpen}
  onOpenChange={setDeleteDialogOpen}
  context={isInProject ? 'project' : 'collection'}
  projectPath={projectPath}
  collectionId={collectionId}
  onSuccess={() => {
    // Refresh multiple caches
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    queryClient.invalidateQueries({ queryKey: ['deployments'] });

    // Show feedback
    toast.success('Artifact deleted successfully');

    // Close dialog
    setDeleteDialogOpen(false);
  }}
  onError={(error) => {
    // Log for debugging
    console.error('Artifact deletion error:', error);

    // Update error state
    setErrorMessage(error.message);
  }}
/>;
```

### Behavior Notes

#### Collection Deletion

- Removes artifact from `~/.skillmeat/collection/artifacts/`
- Updates collection manifest
- Non-destructive for deployments (they remain in projects)

#### Project Undeployment

- Removes artifact from `.claude/skills/` or equivalent directory
- Updates project artifact registry
- Cascades to related deployments
- Multiple projects supported in single operation

#### Deployment Deletion

- Permanently deletes deployment metadata and files
- Removes from filesystem (cannot be undone)
- Shows warning when toggled
- Requires explicit checkbox confirmation
- Visually highlighted with red styling

#### Error Handling Strategy

- If ALL operations fail: throws error and displays toast
- If SOME operations fail: completes successfully with warning toast
- Individual operation results tracked in `DeletionResult`
- Error array includes operation name and error message

### Related Hooks

#### useArtifactDeletion()

Custom mutation hook that orchestrates the deletion process:

```typescript
const deletion = useArtifactDeletion();

const result = await deletion.mutateAsync({
  artifact,
  deleteFromCollection: true,
  deleteFromProjects: true,
  deleteDeployments: false,
  selectedProjectPaths: ['/path/to/project'],
  selectedDeploymentPaths: [],
});

// Result structure:
// {
//   collectionDeleted: boolean;
//   projectsUndeployed: number;
//   deploymentsDeleted: number;
//   errors: Array<{ operation: string; error: string }>;
// }
```

Features:

- Parallel project undeployment using `Promise.allSettled`
- Comprehensive error tracking per operation
- Automatic cache invalidation on success
- Proper handling of partial failures

### Accessibility

- Semantic HTML with proper ARIA labels
- Keyboard navigation support (Tab, Enter, Space)
- Alert roles for warnings and status messages
- Live regions for dynamic counts and loading states
- Disabled state management during mutation
- Focus management within dialog

### Styling

- Red destructive styling for deployment deletion
- Alert icons for warnings and important operations
- Muted foreground text for helper descriptions
- Scrollable lists for many deployments/projects
- Dark mode support throughout

### Type Definitions

```typescript
// Artifact type (imported from @/types/artifact)
interface Artifact {
  id: string;
  name: string;
  type: string;
  // ... other fields
}

// Deletion result from useArtifactDeletion
interface DeletionResult {
  collectionDeleted: boolean;
  projectsUndeployed: number;
  deploymentsDeleted: number;
  errors: Array<{ operation: string; error: string }>;
}
```

### Integration Points

The component integrates with:

- **useArtifactDeletion()** hook: Orchestrates deletion operations
- **useDeploymentList()** hook: Fetches deployment data
- **Dialog primitive**: Radix UI dialog component
- **Checkbox primitive**: For selection controls
- **Sonner**: Toast notifications for feedback
- **Lucide icons**: AlertTriangle, Trash2, Loader2

### Testing

When testing this component:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('ArtifactDeletionDialog', () => {
  const mockArtifact = {
    id: '1',
    name: 'test-skill',
    type: 'skill',
  };

  it('renders deletion options', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      </QueryClientProvider>
    );

    expect(screen.getByText(/Delete test-skill/i)).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /Delete from Collection/i })).toBeInTheDocument();
  });

  it('calls onSuccess after deletion', async () => {
    const onSuccess = jest.fn();
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
          onSuccess={onSuccess}
        />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: /Delete Artifact/i }));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
```

### Best Practices

1. **Always provide `onSuccess`** to refresh data after deletion
2. **Handle `onError`** for proper error reporting to users
3. **Check `context`** matches your use case (collection vs project)
4. **Provide feedback** via toast notifications or UI state
5. **Test partial failures** - not all operations may succeed
6. **Cache invalidation** - ensure deployments list is refreshed after undeploy
7. **Confirm project paths** - verify projectPath before opening in project context

### Known Limitations

- Deployment files are identified by artifact path, not full file path
- Project paths derived from deployment metadata (single source per artifact)
- Partial failure doesn't allow recovery (partial state after mutation)
- No undo capability for filesystem deletion operations
