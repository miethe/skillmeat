# Deployment Components

This directory contains components for displaying and managing artifact deployments in projects.

## Components

### DeploymentCard

A card component that displays comprehensive deployment information with status indicators and action menus.

**Features:**
- Type-colored left border (follows UnifiedCard pattern)
- Status badges (up to date, outdated, error)
- Version comparison (deployed vs. latest)
- Local modifications warning
- Sync status indicators
- Deployment metadata (collection source, timestamp, commit SHA)
- Action menu with context-aware options

**Props:**
```typescript
interface DeploymentCardProps {
  deployment: Deployment;
  projectPath?: string;
  onUpdate?: () => void;
  onRemove?: () => void;
  onViewSource?: () => void;
  onViewDiff?: () => void;
}
```

**Usage:**
```tsx
import { DeploymentCard } from '@/components/deployments';

<DeploymentCard
  deployment={deployment}
  projectPath="/path/to/project"
  onUpdate={() => updateDeployment(deployment.id)}
  onRemove={() => removeDeployment(deployment.id)}
  onViewSource={() => navigateToArtifact(deployment.artifact_name)}
  onViewDiff={() => showDiff(deployment)}
/>
```

### DeploymentActions

Dropdown menu component with deployment lifecycle actions.

**Features:**
- Update to latest version (shown only for outdated deployments)
- View diff (shown only when local modifications exist)
- View source artifact in collection
- Copy deployment path to clipboard
- Remove deployment (with confirmation dialog)

**Props:**
```typescript
interface DeploymentActionsProps {
  deployment: Deployment;
  onUpdate?: () => void;
  onRemove?: () => void;
  onViewSource?: () => void;
  onViewDiff?: () => void;
  onCopyPath?: () => void;
}
```

**Usage:**
```tsx
import { DeploymentActions } from '@/components/deployments';

<DeploymentActions
  deployment={deployment}
  onUpdate={() => updateDeployment(deployment.id)}
  onRemove={() => removeDeployment(deployment.id)}
  onViewSource={() => navigateToCollection(deployment.artifact_name)}
/>
```

### DeploymentCardSkeleton

Loading skeleton for the deployment card.

**Usage:**
```tsx
import { DeploymentCardSkeleton } from '@/components/deployments';

{isLoading ? (
  <DeploymentCardSkeleton />
) : (
  <DeploymentCard deployment={deployment} />
)}
```

## Type Definitions

### Deployment

Extended deployment interface with UI-specific fields:

```typescript
interface Deployment extends ArtifactDeploymentInfo {
  id: string;
  latest_version?: string;
  deployed_version?: string;
  status: 'current' | 'outdated' | 'error';
}
```

Base type `ArtifactDeploymentInfo` from `/types/deployments.ts`:

```typescript
interface ArtifactDeploymentInfo {
  artifact_name: string;
  artifact_type: string;
  from_collection: string;
  deployed_at: string;
  artifact_path: string;
  collection_sha: string;
  local_modifications: boolean;
  sync_status?: ArtifactSyncStatus;
}
```

## Status System

### Deployment Status

- **current**: Deployment is up to date with collection
- **outdated**: Newer version available in collection
- **error**: Deployment has errors

### Sync Status

- **synced**: No local modifications
- **modified**: Local modifications detected
- **outdated**: Collection version is newer

## Visual Design

### Type Colors

Deployments use type-colored borders matching the artifact type:

| Type | Border Color | Background Tint |
|------|--------------|-----------------|
| skill | Blue | Blue/2% |
| command | Purple | Purple/2% |
| agent | Green | Green/2% |
| mcp | Orange | Orange/2% |
| hook | Pink | Pink/2% |

### Status Colors

| Status | Color | Icon |
|--------|-------|------|
| current | Green | CheckCircle2 |
| outdated | Yellow | AlertCircle |
| error | Red | XCircle |

### Sync Status Colors

| Status | Color |
|--------|-------|
| synced | Green |
| modified | Yellow |
| outdated | Orange |

## Examples

### Grid Layout

```tsx
import { DeploymentCard } from '@/components/deployments';

function DeploymentGrid({ deployments }: { deployments: Deployment[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {deployments.map((deployment) => (
        <DeploymentCard
          key={deployment.id}
          deployment={deployment}
          onUpdate={() => handleUpdate(deployment)}
          onRemove={() => handleRemove(deployment)}
        />
      ))}
    </div>
  );
}
```

### With React Query

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DeploymentCard, DeploymentCardSkeleton } from '@/components/deployments';

function ProjectDeployments({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['deployments', projectId],
    queryFn: () => fetchDeployments(projectId),
  });

  const updateMutation = useMutation({
    mutationFn: updateDeployment,
    onSuccess: () => {
      queryClient.invalidateQueries(['deployments', projectId]);
    },
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <DeploymentCardSkeleton />
        <DeploymentCardSkeleton />
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data?.deployments.map((deployment) => (
        <DeploymentCard
          key={deployment.id}
          deployment={deployment}
          onUpdate={() => updateMutation.mutate(deployment.id)}
        />
      ))}
    </div>
  );
}
```

### Filtered View

```tsx
import { DeploymentCard } from '@/components/deployments';

function OutdatedDeployments({ deployments }: { deployments: Deployment[] }) {
  const outdated = deployments.filter(d => d.status === 'outdated');

  if (outdated.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        All deployments are up to date
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">
        Updates Available ({outdated.length})
      </h2>
      <div className="grid gap-4 md:grid-cols-2">
        {outdated.map((deployment) => (
          <DeploymentCard
            key={deployment.id}
            deployment={deployment}
            onUpdate={() => updateDeployment(deployment.id)}
          />
        ))}
      </div>
    </div>
  );
}
```

## Testing

Unit tests are located in `__tests__/components/deployments/`:

- `deployment-card.test.tsx` - DeploymentCard component tests
- `deployment-actions.test.tsx` - DeploymentActions component tests

Run tests:
```bash
pnpm test deployments
```

## Accessibility

- Menu trigger buttons have proper ARIA labels
- Screen reader text for icon-only actions
- Keyboard navigation support
- Focus management in dialogs
- Tooltips for truncated content
- High contrast status indicators

## Integration Points

### API Endpoints

- `GET /api/projects/:id/deployments` - List deployments
- `PUT /api/deployments/:id` - Update deployment
- `DELETE /api/deployments/:id` - Remove deployment
- `GET /api/deployments/:id/diff` - Get deployment diff

### Related Components

- `UnifiedCard` - Base card pattern
- `EntityActions` - Similar action menu pattern
- `ArtifactGrid` - Collection view pattern

### Type Definitions

- `/types/deployments.ts` - Deployment types
- `/types/artifact.ts` - Artifact types
- `/types/entity.ts` - Entity configuration

## Future Enhancements

- Bulk deployment updates
- Deployment history timeline
- Rollback to previous versions
- Deployment health checks
- Auto-update configuration
- Deployment groups/bundles
