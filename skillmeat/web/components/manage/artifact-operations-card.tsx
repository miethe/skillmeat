/**
 * Artifact Operations Card Component
 *
 * Operations-focused card for the /manage page, emphasizing health status,
 * sync state, and operational actions. Designed for quick decisions and
 * bulk operations on deployed artifacts.
 *
 * Key differences from browse/discovery cards:
 * - Shows health indicators and drift badges
 * - Displays deployment locations
 * - Action-oriented with Sync, Deploy, View Diff buttons
 * - Supports bulk selection via checkbox
 *
 * @example Basic usage
 * ```tsx
 * <ArtifactOperationsCard
 *   artifact={artifact}
 *   onClick={() => openModal(artifact)}
 *   onSync={() => syncArtifact(artifact.id)}
 *   onDeploy={() => deployArtifact(artifact.id)}
 * />
 * ```
 *
 * @example With selection
 * ```tsx
 * <ArtifactOperationsCard
 *   artifact={artifact}
 *   onClick={() => openModal(artifact)}
 *   selectable={true}
 *   selected={selectedIds.includes(artifact.id)}
 *   onSelect={(selected) => toggleSelection(artifact.id, selected)}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import {
  RefreshCcw,
  Download,
  GitCompare,
  MoreHorizontal,
  AlertTriangle,
  ArrowRight,
  Clock,
  Trash2,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { StatusBadge } from '@/components/shared/status-badge';
import {
  HealthIndicator,
  deriveHealthStatus,
  type HealthStatus,
} from '@/components/shared/health-indicator';
import { DeploymentBadgeStack } from '@/components/shared/deployment-badge-stack';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface ArtifactOperationsCardProps {
  /** The artifact to display */
  artifact: Artifact;

  /** Click handler for opening operations modal */
  onClick: () => void;

  /** Handler for sync action */
  onSync?: () => void;

  /** Handler for deploy action */
  onDeploy?: () => void;

  /** Handler for viewing diff */
  onViewDiff?: () => void;

  /** Handler for manage action (opens management menu) */
  onManage?: () => void;

  /** Handler for delete action */
  onDelete?: (artifact: Artifact) => void;

  /** Whether card is selected (for bulk operations) */
  selected?: boolean;

  /** Selection change handler */
  onSelect?: (selected: boolean) => void;

  /** Whether selection is enabled */
  selectable?: boolean;

  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Configuration
// ============================================================================

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

// Health-based border accent overrides (when attention needed)
const healthBorderAccents: Partial<Record<HealthStatus, string>> = {
  'needs-update': 'border-orange-500/50',
  'has-drift': 'border-yellow-500/50',
  error: 'border-red-500/50',
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format a date string as relative time (e.g., "2h ago", "3d ago")
 */
function formatRelativeTime(dateString?: string): string {
  if (!dateString) return 'Never';

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
}

/**
 * Get version display string showing current and available versions
 */
function getVersionDisplay(artifact: Artifact): {
  current: string;
  available?: string;
  hasUpdate: boolean;
} {
  const current = artifact.version || 'unknown';
  const available = artifact.upstream?.version;
  const hasUpdate = artifact.upstream?.updateAvailable === true;

  return {
    current,
    available: hasUpdate ? available : undefined,
    hasUpdate,
  };
}

// ============================================================================
// Component
// ============================================================================

/**
 * ArtifactOperationsCard - Operations-focused card for manage page
 *
 * Displays artifact with emphasis on health status, sync state, and
 * operational actions. Supports bulk selection and quick actions.
 *
 * @param artifact - The artifact to display
 * @param onClick - Handler for card click (opens modal)
 * @param onSync - Handler for sync action
 * @param onDeploy - Handler for deploy action
 * @param onViewDiff - Handler for view diff action
 * @param onManage - Handler for manage dropdown action
 * @param selected - Whether card is selected
 * @param onSelect - Selection change handler
 * @param selectable - Whether selection is enabled
 * @param className - Additional CSS classes
 */
export function ArtifactOperationsCard({
  artifact,
  onClick,
  onSync,
  onDeploy,
  onViewDiff,
  onManage,
  onDelete,
  selected = false,
  onSelect,
  selectable = false,
  className,
}: ArtifactOperationsCardProps) {
  const config = getArtifactTypeConfig(artifact.type);
  const health = deriveHealthStatus(artifact);
  const versionInfo = getVersionDisplay(artifact);
  const lastSynced = artifact.upstream?.lastChecked;

  // Type-safe icon lookup with fallback
  const iconName = config?.icon ?? 'FileText';
  const IconComponent = (LucideIcons as any)[iconName] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const Icon = IconComponent || LucideIcons.FileText;

  // Determine if card needs attention styling
  const needsAttention = health === 'needs-update' || health === 'has-drift';
  const hasError = health === 'error';

  // Handle card click (excluding interactive elements)
  const handleCardClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;

    // Ignore clicks on checkbox
    if (target.closest('[role="checkbox"]')) return;

    // Ignore clicks on buttons
    if (target.closest('button')) return;

    onClick();
  };

  // Handle checkbox change
  const handleCheckboxChange = (checked: boolean) => {
    onSelect?.(checked);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <Card
      className={cn(
        'cursor-pointer border-l-4 transition-all hover:border-primary/50 hover:shadow-md',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        artifactTypeBorderAccents[artifact.type],
        artifactTypeCardTints[artifact.type],
        selected && 'ring-2 ring-primary',
        needsAttention && healthBorderAccents[health],
        hasError && healthBorderAccents.error,
        className
      )}
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      aria-label={`Manage ${artifact.name}, ${artifact.type} artifact. Status: ${artifact.syncStatus}`}
    >
      {/* Header Row: Checkbox, Icon, Name, Status, Health */}
      <div className="flex items-start gap-3 p-4 pb-2">
        {/* Checkbox (when selectable) */}
        {selectable && (
          <Checkbox
            checked={selected}
            onCheckedChange={handleCheckboxChange}
            className="mt-1 flex-shrink-0"
            aria-label={`Select ${artifact.name} for bulk operations`}
          />
        )}

        {/* Type Icon */}
        <div
          className={cn(
            'flex-shrink-0 rounded-md border p-2',
            config?.color ?? 'text-muted-foreground'
          )}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>

        {/* Name and Version */}
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold" title={artifact.name}>
            {artifact.name}
          </h3>
          {/* Version with update arrow */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>{versionInfo.current}</span>
            {versionInfo.hasUpdate && versionInfo.available && (
              <>
                <ArrowRight className="h-3 w-3" aria-hidden="true" />
                <span className="text-orange-600 dark:text-orange-400">
                  {versionInfo.available}
                </span>
                <span className="sr-only">available</span>
              </>
            )}
          </div>
        </div>

        {/* Status Badge and Health Indicator */}
        <div className="flex flex-shrink-0 items-center gap-2">
          <StatusBadge status={artifact.syncStatus} size="sm" />
          <HealthIndicator artifact={artifact} size="md" />
        </div>
      </div>

      {/* Deployments Row */}
      {artifact.deployments && artifact.deployments.length > 0 && (
        <div className="border-t px-4 py-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Deployed to:</span>
            <DeploymentBadgeStack deployments={artifact.deployments} maxBadges={2} />
          </div>
        </div>
      )}

      {/* Status Row: Drift, Update Available, Last Synced */}
      <div className="flex flex-wrap items-center gap-2 border-t px-4 py-2">
        {/* Drift Badge */}
        {artifact.syncStatus === 'modified' && (
          <Badge
            variant="outline"
            className="border-yellow-500/20 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
          >
            <AlertTriangle className="mr-1 h-3 w-3" aria-hidden="true" />
            Has Drift
          </Badge>
        )}

        {/* Update Available Badge */}
        {versionInfo.hasUpdate && (
          <Badge
            variant="outline"
            className="border-orange-500/20 bg-orange-500/10 text-orange-600 dark:text-orange-400"
          >
            Update Available
          </Badge>
        )}

        {/* Last Synced */}
        <div className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" aria-hidden="true" />
          <span>Last synced: {formatRelativeTime(lastSynced)}</span>
        </div>
      </div>

      {/* Actions Row */}
      <div className="flex items-center gap-2 border-t px-4 py-3">
        {/* Sync Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onSync?.();
          }}
          disabled={!onSync}
          aria-label={`Sync ${artifact.name}`}
        >
          <RefreshCcw className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          Sync
        </Button>

        {/* Deploy Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onDeploy?.();
          }}
          disabled={!onDeploy}
          aria-label={`Deploy ${artifact.name}`}
        >
          <Download className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          Deploy
        </Button>

        {/* View Diff Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onViewDiff?.();
          }}
          disabled={!onViewDiff || artifact.syncStatus === 'synced'}
          aria-label={`View diff for ${artifact.name}`}
        >
          <GitCompare className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          View Diff
        </Button>

        {/* Manage Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              aria-label={`More actions for ${artifact.name}`}
            >
              <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onManage?.()} disabled={!onManage}>
              <LucideIcons.Settings className="mr-2 h-4 w-4" aria-hidden="true" />
              Manage Settings
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onClick()}>
              <LucideIcons.Info className="mr-2 h-4 w-4" aria-hidden="true" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {
                navigator.clipboard.writeText(`skillmeat deploy ${artifact.name}`);
              }}
            >
              <LucideIcons.Copy className="mr-2 h-4 w-4" aria-hidden="true" />
              Copy Deploy Command
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                navigator.clipboard.writeText(`skillmeat sync ${artifact.name}`);
              }}
            >
              <LucideIcons.Copy className="mr-2 h-4 w-4" aria-hidden="true" />
              Copy Sync Command
            </DropdownMenuItem>
            {onDelete && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(artifact);
                  }}
                >
                  <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                  Delete Artifact
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </Card>
  );
}

// ============================================================================
// Skeleton
// ============================================================================

/**
 * ArtifactOperationsCardSkeleton - Loading skeleton for operations card
 *
 * Displays a placeholder while artifact data is being fetched.
 * Matches the layout of ArtifactOperationsCard for seamless loading states.
 *
 * @param selectable - Whether to show checkbox skeleton
 */
export function ArtifactOperationsCardSkeleton({ selectable = false }: { selectable?: boolean }) {
  return (
    <Card className="border-l-4" aria-busy="true" aria-label="Loading artifact card">
      {/* Header Row */}
      <div className="flex items-start gap-3 p-4 pb-2">
        {selectable && (
          <Skeleton className="mt-1 h-4 w-4 flex-shrink-0 rounded" aria-hidden="true" />
        )}
        <Skeleton className="h-8 w-8 flex-shrink-0 rounded-md" aria-hidden="true" />
        <div className="min-w-0 flex-1 space-y-1">
          <Skeleton className="h-4 w-32" aria-hidden="true" />
          <Skeleton className="h-3 w-20" aria-hidden="true" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-16 rounded-full" aria-hidden="true" />
          <Skeleton className="h-4 w-4 rounded-full" aria-hidden="true" />
        </div>
      </div>

      {/* Deployments Row */}
      <div className="border-t px-4 py-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-3 w-20" aria-hidden="true" />
          <Skeleton className="h-5 w-24 rounded-full" aria-hidden="true" />
          <Skeleton className="h-5 w-24 rounded-full" aria-hidden="true" />
        </div>
      </div>

      {/* Status Row */}
      <div className="flex items-center gap-2 border-t px-4 py-2">
        <Skeleton className="h-5 w-20 rounded-full" aria-hidden="true" />
        <Skeleton className="ml-auto h-3 w-32" aria-hidden="true" />
      </div>

      {/* Actions Row */}
      <div className="flex items-center gap-2 border-t px-4 py-3">
        <Skeleton className="h-8 w-16 rounded-md" aria-hidden="true" />
        <Skeleton className="h-8 w-20 rounded-md" aria-hidden="true" />
        <Skeleton className="h-8 w-24 rounded-md" aria-hidden="true" />
        <Skeleton className="ml-auto h-8 w-8 rounded-md" aria-hidden="true" />
      </div>
    </Card>
  );
}
