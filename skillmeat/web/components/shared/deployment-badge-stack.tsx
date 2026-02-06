/**
 * Deployment Badge Stack Component
 *
 * Displays deployment locations as badges with overflow handling.
 * Shows first N badges with a clickable "+N" overflow indicator.
 *
 * @example Basic usage
 * ```tsx
 * <DeploymentBadgeStack
 *   deployments={artifact.deployments}
 *   onBadgeClick={(d) => console.log('Clicked:', d)}
 * />
 * ```
 *
 * @example With modal integration
 * ```tsx
 * <DeploymentBadgeStack
 *   deployments={deployments}
 *   maxBadges={3}
 *   onOverflowClick={() => openModal('deployments')}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { FolderKanban } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { DeploymentSummary } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface DeploymentBadgeStackProps {
  /** Array of deployment information */
  deployments: DeploymentSummary[];
  /** Maximum number of badges to display before showing overflow (default: 2) */
  maxBadges?: number;
  /** Callback when a deployment badge is clicked */
  onBadgeClick?: (deployment: DeploymentSummary) => void;
  /** Callback when overflow badge is clicked (typically opens modal on deployments tab) */
  onOverflowClick?: () => void;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Extract a displayable project name from the full path.
 *
 * Takes the last path segment as the project name for brevity.
 * Handles both Unix and Windows path separators.
 *
 * @param projectPath - Full path to the project
 * @returns Short project name for display
 */
function extractProjectName(projectPath: string): string {
  if (!projectPath) return 'Unknown';

  // Handle both Unix and Windows paths
  const separator = projectPath.includes('\\') ? '\\' : '/';
  const segments = projectPath.split(separator).filter(Boolean);

  // Return last segment, or full path if no segments
  return segments[segments.length - 1] || projectPath;
}

// ============================================================================
// Sub-components
// ============================================================================

interface DeploymentBadgeProps {
  deployment: DeploymentSummary;
  onClick?: () => void;
}

/**
 * Single deployment badge with project icon and name.
 */
function DeploymentBadge({ deployment, onClick }: DeploymentBadgeProps) {
  const projectName = extractProjectName(deployment.project_path);
  const isClickable = Boolean(onClick);

  return (
    <Badge
      variant="outline"
      className={cn(
        'inline-flex items-center gap-1 text-xs',
        isClickable && 'cursor-pointer hover:bg-muted'
      )}
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      aria-label={`Deployed to ${deployment.project_name || projectName}`}
    >
      <FolderKanban className="h-3 w-3" aria-hidden="true" />
      <span className="max-w-[100px] truncate">{deployment.project_name || projectName}</span>
    </Badge>
  );
}

interface OverflowBadgeProps {
  /** Count of hidden deployments */
  count: number;
  /** Hidden deployment details for tooltip */
  hiddenDeployments: DeploymentSummary[];
  /** Click handler for overflow badge */
  onClick?: () => void;
}

/**
 * Overflow badge showing count with tooltip listing all hidden projects.
 */
function OverflowBadge({ count, hiddenDeployments, onClick }: OverflowBadgeProps) {
  const isClickable = Boolean(onClick);

  const badge = (
    <Badge
      variant="outline"
      className={cn('text-xs', isClickable && 'cursor-pointer hover:bg-muted')}
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      aria-label={`${count} more deployments`}
    >
      +{count}
    </Badge>
  );

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Also deployed to:</p>
            {hiddenDeployments.map((deployment) => (
              <div key={deployment.project_path} className="flex items-center gap-1 text-xs">
                <FolderKanban className="h-3 w-3" aria-hidden="true" />
                <span>
                  {deployment.project_name || extractProjectName(deployment.project_path)}
                </span>
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * DeploymentBadgeStack - Display deployment locations with overflow
 *
 * Shows badges for each deployment location (project) where an artifact
 * is deployed. When there are more deployments than maxBadges, shows
 * an overflow indicator with a tooltip listing all hidden deployments.
 *
 * @param deployments - Array of deployment summary objects
 * @param maxBadges - Maximum visible badges before overflow (default: 2)
 * @param onBadgeClick - Handler for individual badge clicks
 * @param onOverflowClick - Handler for overflow badge click (opens modal)
 * @param className - Additional CSS classes
 */
export function DeploymentBadgeStack({
  deployments,
  maxBadges = 2,
  onBadgeClick,
  onOverflowClick,
  className,
}: DeploymentBadgeStackProps) {
  // Handle empty or invalid deployments
  if (!deployments || !Array.isArray(deployments) || deployments.length === 0) {
    return null;
  }

  const visibleDeployments = deployments.slice(0, maxBadges);
  const hiddenDeployments = deployments.slice(maxBadges);
  const overflowCount = hiddenDeployments.length;
  const hasOverflow = overflowCount > 0;

  return (
    <div
      className={cn('flex flex-wrap items-center gap-1', className)}
      role="list"
      aria-label="Deployment locations"
    >
      {visibleDeployments.map((deployment) => (
        <div key={deployment.project_path} role="listitem">
          <DeploymentBadge
            deployment={deployment}
            onClick={onBadgeClick ? () => onBadgeClick(deployment) : undefined}
          />
        </div>
      ))}
      {hasOverflow && (
        <div role="listitem">
          <OverflowBadge
            count={overflowCount}
            hiddenDeployments={hiddenDeployments}
            onClick={onOverflowClick}
          />
        </div>
      )}
    </div>
  );
}
