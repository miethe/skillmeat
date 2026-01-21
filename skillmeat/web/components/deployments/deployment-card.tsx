/**
 * DeploymentCard Component
 *
 * Displays deployment status, version information, and available actions.
 * Uses the UnifiedCard visual style with type-colored borders and status indicators.
 */

'use client';

import * as React from 'react';
import { useMemo } from 'react';
import * as LucideIcons from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ArtifactDeploymentInfo, ArtifactSyncStatus } from '@/types/deployments';
import type { ArtifactType } from '@/types/artifact';
import type { ProjectSummary } from '@/types/project';
import { getEntityTypeConfig } from '@/types/entity';
import { DeploymentActions } from './deployment-actions';

/**
 * Extended deployment interface with UI-specific fields
 */
export interface Deployment extends ArtifactDeploymentInfo {
  /** Unique identifier for the deployment */
  id: string;
  /** Latest version available in collection */
  latest_version?: string;
  /** Current deployed version */
  deployed_version?: string;
  /** Computed deployment status */
  status: 'current' | 'outdated' | 'error';
}

/**
 * Props for DeploymentCard component
 */
export interface DeploymentCardProps {
  /** Deployment information to display */
  deployment: Deployment;
  /** List of projects for matching deployment path to project name */
  projects?: ProjectSummary[];
  /** Project path for context */
  projectPath?: string;
  /** Callback when deployment should be updated */
  onUpdate?: () => void;
  /** Callback when deployment should be removed */
  onRemove?: () => void;
  /** Callback to view source artifact in collection */
  onViewSource?: () => void;
  /** Callback to view deployment diff */
  onViewDiff?: () => void;
}

// Type-colored left borders (matching UnifiedCard pattern)
const artifactTypeBorderAccents: Record<ArtifactType, string> = {
  skill: 'border-l-blue-500',
  command: 'border-l-purple-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  hook: 'border-l-pink-500',
};

const artifactTypeCardTints: Record<ArtifactType, string> = {
  skill: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
  command: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
  agent: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
  mcp: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  hook: 'bg-pink-500/[0.02] dark:bg-pink-500/[0.03]',
};

// Status badge colors and labels
const statusColors: Record<string, string> = {
  current: 'bg-green-500/10 text-green-600 border-green-500/20',
  outdated: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
  error: 'bg-red-500/10 text-red-600 border-red-500/20',
};

const statusIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  current: LucideIcons.CheckCircle2,
  outdated: LucideIcons.AlertCircle,
  error: LucideIcons.XCircle,
};

const statusLabels: Record<string, string> = {
  current: 'Up to date',
  outdated: 'Update available',
  error: 'Error',
};

// Sync status colors (for local modifications indicator)
const syncStatusColors: Record<ArtifactSyncStatus, string> = {
  synced: 'text-green-500',
  modified: 'text-yellow-500',
  outdated: 'text-orange-500',
};

const syncStatusLabels: Record<ArtifactSyncStatus, string> = {
  synced: 'Synced',
  modified: 'Modified',
  outdated: 'Outdated',
};

/**
 * DeploymentCard - Card component for displaying deployment information
 *
 * Shows deployment status, version information, and provides actions through
 * a dropdown menu. Follows the UnifiedCard visual pattern with type-colored
 * borders and status indicators.
 *
 * @example
 * ```tsx
 * <DeploymentCard
 *   deployment={deployment}
 *   projectPath="/path/to/project"
 *   onUpdate={() => updateDeployment(deployment.id)}
 *   onRemove={() => removeDeployment(deployment.id)}
 *   onViewSource={() => navigateToArtifact(deployment.artifact_name)}
 * />
 * ```
 */
export function DeploymentCard({
  deployment,
  projects,
  projectPath: _projectPath,
  onUpdate,
  onRemove,
  onViewSource,
  onViewDiff,
}: DeploymentCardProps) {
  void _projectPath; // Reserved for future use
  const config = getEntityTypeConfig(deployment.artifact_type as ArtifactType);

  // Find which project this deployment belongs to
  const projectMatch = useMemo(() => {
    if (!Array.isArray(projects)) return null;
    // Match project by its path matching the deployment's project_path
    return projects.find((p) => p.path === deployment.project_path);
  }, [projects, deployment.project_path]);

  const projectDisplayName = projectMatch?.name || 'Custom Path';

  // Type-safe icon lookup with fallback
  const IconComponent = (LucideIcons as any)[config.icon] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const Icon = IconComponent || LucideIcons.FileText;

  // Status icon
  const StatusIcon = statusIcons[deployment.status] || LucideIcons.Circle;

  // Format relative time
  const formatRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Copy path to clipboard
  const handleCopyPath = async () => {
    if (deployment.artifact_path) {
      await navigator.clipboard.writeText(deployment.artifact_path);
    }
  };

  return (
    <Card
      className={cn(
        'border-l-4 transition-all hover:shadow-md',
        artifactTypeBorderAccents[deployment.artifact_type as ArtifactType],
        artifactTypeCardTints[deployment.artifact_type as ArtifactType]
      )}
    >
      {/* Header with icon and status */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            {/* Icon with type color */}
            <div className="flex-shrink-0 rounded-md border p-2">
              <Icon className={cn('h-4 w-4', config.color)} />
            </div>

            {/* Name and type */}
            <div className="min-w-0 flex-1">
              <h3 className="truncate font-semibold" title={deployment.artifact_name}>
                {deployment.artifact_name}
              </h3>
              <p className="truncate text-xs capitalize text-muted-foreground">
                {deployment.artifact_type}
              </p>
            </div>
          </div>

          {/* Status badge and actions */}
          <div className="flex flex-shrink-0 items-center gap-2">
            <Badge
              className={cn('flex items-center gap-1', statusColors[deployment.status])}
              variant="outline"
            >
              <StatusIcon className="h-3 w-3" />
              {statusLabels[deployment.status]}
            </Badge>
            <DeploymentActions
              deployment={deployment}
              onUpdate={onUpdate}
              onRemove={onRemove}
              onViewSource={onViewSource}
              onViewDiff={onViewDiff}
              onCopyPath={handleCopyPath}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-3 px-4 pb-4">
        {/* Project / Deployment path */}
        <div className="flex items-start gap-2 text-sm">
          <LucideIcons.FolderTree className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <p className="text-xs text-muted-foreground">Project</p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <p className="cursor-help truncate font-medium">{projectDisplayName}</p>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[400px]">
                  <p className="break-all font-mono text-xs">{deployment.artifact_path}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

        {/* Version information */}
        <div className="grid grid-cols-2 gap-4">
          {/* Deployed version */}
          {deployment.deployed_version && (
            <div className="flex items-center gap-1 text-xs">
              <LucideIcons.Package className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Deployed:</span>
              <span className="font-mono">{deployment.deployed_version}</span>
            </div>
          )}

          {/* Latest version (if different) */}
          {deployment.latest_version &&
            deployment.latest_version !== deployment.deployed_version && (
              <div className="flex items-center gap-1 text-xs">
                <LucideIcons.ArrowUpCircle className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Available:</span>
                <span className="font-mono">{deployment.latest_version}</span>
              </div>
            )}
        </div>

        {/* Metadata row */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {/* Collection source */}
          <div className="flex items-center gap-1" title="Source collection">
            <LucideIcons.Database className="h-3 w-3" />
            <span>{deployment.from_collection}</span>
          </div>

          {/* Deployment time */}
          <div
            className="flex items-center gap-1"
            title={new Date(deployment.deployed_at).toLocaleString()}
          >
            <LucideIcons.Clock className="h-3 w-3" />
            <span>{formatRelativeTime(deployment.deployed_at)}</span>
          </div>

          {/* Commit SHA (truncated) */}
          {deployment.collection_sha && (
            <div className="flex items-center gap-1" title={`Commit: ${deployment.collection_sha}`}>
              <LucideIcons.GitCommit className="h-3 w-3" />
              <span className="font-mono">{deployment.collection_sha.substring(0, 7)}</span>
            </div>
          )}
        </div>

        {/* Warnings and status indicators */}
        <div className="flex flex-col gap-1">
          {/* Local modifications warning */}
          {deployment.local_modifications && (
            <div className="flex items-center gap-1 text-xs text-yellow-600">
              <LucideIcons.AlertTriangle className="h-3 w-3" />
              <span>Local modifications detected</span>
            </div>
          )}

          {/* Sync status indicator */}
          {deployment.sync_status && deployment.sync_status !== 'synced' && (
            <div
              className={cn(
                'flex items-center gap-1 text-xs',
                syncStatusColors[deployment.sync_status]
              )}
            >
              <LucideIcons.RefreshCw className="h-3 w-3" />
              <span>{syncStatusLabels[deployment.sync_status]}</span>
            </div>
          )}

          {/* Outdated version warning */}
          {deployment.status === 'outdated' && (
            <div className="flex items-center gap-1 text-xs text-orange-600">
              <LucideIcons.AlertCircle className="h-3 w-3" />
              <span>Update available in collection</span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

/**
 * DeploymentCardSkeleton - Loading placeholder for deployment card
 *
 * Displays a skeleton while deployment data is being fetched.
 */
export function DeploymentCardSkeleton() {
  return (
    <Card className="border-l-4">
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-1 items-center gap-2">
            {/* Icon skeleton */}
            <div className="h-8 w-8 flex-shrink-0 animate-pulse rounded-md bg-muted" />

            {/* Name skeleton */}
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-muted" />
              <div className="h-3 w-24 animate-pulse rounded bg-muted" />
            </div>
          </div>

          {/* Status badge and actions skeleton */}
          <div className="flex flex-shrink-0 items-center gap-2">
            <div className="h-5 w-24 animate-pulse rounded-full bg-muted" />
            <div className="h-8 w-8 animate-pulse rounded bg-muted" />
          </div>
        </div>
      </div>
      <div className="space-y-3 px-4 pb-4">
        {/* Path skeleton */}
        <div className="flex items-start gap-2">
          <div className="h-4 w-4 animate-pulse rounded bg-muted" />
          <div className="flex-1 space-y-1">
            <div className="h-3 w-20 animate-pulse rounded bg-muted" />
            <div className="h-3 w-48 animate-pulse rounded bg-muted" />
          </div>
        </div>

        {/* Version skeleton */}
        <div className="grid grid-cols-2 gap-4">
          <div className="h-3 w-24 animate-pulse rounded bg-muted" />
          <div className="h-3 w-24 animate-pulse rounded bg-muted" />
        </div>

        {/* Metadata skeleton */}
        <div className="flex gap-4">
          <div className="h-3 w-20 animate-pulse rounded bg-muted" />
          <div className="h-3 w-16 animate-pulse rounded bg-muted" />
          <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        </div>
      </div>
    </Card>
  );
}
