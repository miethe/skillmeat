/**
 * DeploymentCard Usage Examples
 *
 * This file demonstrates how to use the DeploymentCard component
 * in various scenarios. These examples are for reference only.
 */

'use client';

import { DeploymentCard, DeploymentCardSkeleton, type Deployment } from './deployment-card';

// Example 1: Basic deployment card (up to date)
const currentDeployment: Deployment = {
  id: 'deploy-1',
  artifact_name: 'pdf-extractor',
  artifact_type: 'skill',
  from_collection: 'my-collection',
  deployed_at: '2024-12-10T10:00:00Z',
  artifact_path: '.claude/skills/user/pdf-extractor.md',
  collection_sha: 'abc123def456',
  local_modifications: false,
  sync_status: 'synced',
  deployed_version: '1.2.0',
  latest_version: '1.2.0',
  status: 'current',
};

// Example 2: Outdated deployment (update available)
const outdatedDeployment: Deployment = {
  id: 'deploy-2',
  artifact_name: 'code-reviewer',
  artifact_type: 'agent',
  from_collection: 'my-collection',
  deployed_at: '2024-12-08T14:30:00Z',
  artifact_path: '.claude/agents/user/code-reviewer.yaml',
  collection_sha: 'def456ghi789',
  local_modifications: false,
  sync_status: 'outdated',
  deployed_version: '2.0.0',
  latest_version: '2.1.0',
  status: 'outdated',
};

// Example 3: Deployment with local modifications
const modifiedDeployment: Deployment = {
  id: 'deploy-3',
  artifact_name: 'task-manager',
  artifact_type: 'command',
  from_collection: 'work-tools',
  deployed_at: '2024-12-09T16:45:00Z',
  artifact_path: '.claude/commands/user/task-manager.yaml',
  collection_sha: 'ghi789jkl012',
  local_modifications: true,
  sync_status: 'modified',
  deployed_version: '3.1.0',
  latest_version: '3.1.0',
  status: 'current',
};

// Example 4: Error state deployment
const errorDeployment: Deployment = {
  id: 'deploy-4',
  artifact_name: 'broken-skill',
  artifact_type: 'skill',
  from_collection: 'testing',
  deployed_at: '2024-12-11T09:00:00Z',
  artifact_path: '.claude/skills/user/broken-skill.md',
  collection_sha: 'jkl012mno345',
  local_modifications: false,
  status: 'error',
};

/**
 * Example 1: Basic usage with all callbacks
 */
export function BasicDeploymentCardExample() {
  const handleUpdate = () => {
    console.log('Updating deployment:', currentDeployment.id);
    // API call to update deployment
  };

  const handleRemove = () => {
    console.log('Removing deployment:', currentDeployment.id);
    // API call to remove deployment
  };

  const handleViewSource = () => {
    console.log('Viewing source:', currentDeployment.artifact_name);
    // Navigate to artifact in collection view
  };

  const handleViewDiff = () => {
    console.log('Viewing diff for:', currentDeployment.id);
    // Open diff modal
  };

  return (
    <div className="max-w-md">
      <DeploymentCard
        deployment={currentDeployment}
        projectPath="/path/to/project"
        onUpdate={handleUpdate}
        onRemove={handleRemove}
        onViewSource={handleViewSource}
        onViewDiff={handleViewDiff}
      />
    </div>
  );
}

/**
 * Example 2: Grid of deployment cards
 */
export function DeploymentGridExample() {
  const deployments = [currentDeployment, outdatedDeployment, modifiedDeployment];

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {deployments.map((deployment) => (
        <DeploymentCard
          key={deployment.id}
          deployment={deployment}
          onUpdate={() => console.log('Update', deployment.id)}
          onRemove={() => console.log('Remove', deployment.id)}
          onViewSource={() => console.log('View source', deployment.artifact_name)}
        />
      ))}
    </div>
  );
}

/**
 * Example 3: Loading state
 */
export function DeploymentCardLoadingExample() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <DeploymentCardSkeleton />
      <DeploymentCardSkeleton />
      <DeploymentCardSkeleton />
    </div>
  );
}

/**
 * Example 4: Different deployment statuses
 */
export function DeploymentStatusesExample() {
  return (
    <div className="space-y-4 max-w-md">
      <div>
        <h3 className="text-sm font-medium mb-2">Up to Date</h3>
        <DeploymentCard
          deployment={currentDeployment}
          onRemove={() => console.log('Remove')}
        />
      </div>

      <div>
        <h3 className="text-sm font-medium mb-2">Update Available</h3>
        <DeploymentCard
          deployment={outdatedDeployment}
          onUpdate={() => console.log('Update')}
          onRemove={() => console.log('Remove')}
        />
      </div>

      <div>
        <h3 className="text-sm font-medium mb-2">Local Modifications</h3>
        <DeploymentCard
          deployment={modifiedDeployment}
          onViewDiff={() => console.log('View diff')}
          onRemove={() => console.log('Remove')}
        />
      </div>

      <div>
        <h3 className="text-sm font-medium mb-2">Error State</h3>
        <DeploymentCard
          deployment={errorDeployment}
          onRemove={() => console.log('Remove')}
        />
      </div>
    </div>
  );
}

/**
 * Example 5: Integration with React Query
 */
export function DeploymentWithQueryExample() {
  // Simulated loading state
  const isLoading = false;
  const deployment = currentDeployment;

  if (isLoading) {
    return <DeploymentCardSkeleton />;
  }

  if (!deployment) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No deployment found
      </div>
    );
  }

  return (
    <DeploymentCard
      deployment={deployment}
      onUpdate={() => {
        // Optimistic update with React Query
        // queryClient.setQueryData(['deployment', deployment.id], { ...deployment, status: 'updating' });
        // await updateDeploymentMutation.mutateAsync(deployment.id);
      }}
      onRemove={() => {
        // Optimistic removal with React Query
        // queryClient.setQueryData(['deployments'], (old) =>
        //   old?.filter(d => d.id !== deployment.id)
        // );
        // await removeDeploymentMutation.mutateAsync(deployment.id);
      }}
    />
  );
}

/**
 * Example 6: Filtered deployments by status
 */
export function FilteredDeploymentsExample() {
  const deployments = [
    currentDeployment,
    outdatedDeployment,
    modifiedDeployment,
    errorDeployment,
  ];

  // Filter to show only deployments that need attention
  const needsAttention = deployments.filter(
    (d) => d.status === 'outdated' || d.status === 'error' || d.local_modifications
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">
        Deployments Needing Attention ({needsAttention.length})
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {needsAttention.map((deployment) => (
          <DeploymentCard
            key={deployment.id}
            deployment={deployment}
            onUpdate={
              deployment.status === 'outdated'
                ? () => console.log('Update', deployment.id)
                : undefined
            }
            onViewDiff={
              deployment.local_modifications
                ? () => console.log('View diff', deployment.id)
                : undefined
            }
            onRemove={() => console.log('Remove', deployment.id)}
          />
        ))}
      </div>
    </div>
  );
}
