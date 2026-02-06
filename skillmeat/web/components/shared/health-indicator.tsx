/**
 * Health Indicator Component
 *
 * Displays artifact health status with tooltip explanation.
 * Health is derived from sync status and upstream update availability.
 *
 * @example Basic usage
 * ```tsx
 * <HealthIndicator artifact={artifact} />
 * ```
 *
 * @example Without tooltip
 * ```tsx
 * <HealthIndicator artifact={artifact} showTooltip={false} size="lg" />
 * ```
 */

'use client';

import * as React from 'react';
import { CheckCircle2, ArrowUp, GitBranch, AlertCircle, type LucideIcon } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export type HealthStatus = 'healthy' | 'needs-update' | 'has-drift' | 'error';

export interface HealthIndicatorProps {
  /** Artifact to derive health from */
  artifact: Artifact;
  /** Size variant affecting icon size */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show tooltip with status description */
  showTooltip?: boolean;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Configuration
// ============================================================================

interface HealthConfig {
  icon: LucideIcon;
  color: string;
  description: string;
}

const healthConfigs: Record<HealthStatus, HealthConfig> = {
  healthy: {
    icon: CheckCircle2,
    color: 'text-green-500 dark:text-green-400',
    description: 'Artifact is healthy and up to date',
  },
  'needs-update': {
    icon: ArrowUp,
    color: 'text-orange-500 dark:text-orange-400',
    description: 'A newer version is available upstream',
  },
  'has-drift': {
    icon: GitBranch,
    color: 'text-yellow-500 dark:text-yellow-400',
    description: 'Local modifications differ from source',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500 dark:text-red-400',
    description: 'Error occurred during sync or validation',
  },
};

const sizeClasses = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Derive health status from artifact properties.
 *
 * Logic:
 * 1. Error or conflict sync status = error health
 * 2. Upstream update available = needs-update
 * 3. Modified sync status = has-drift
 * 4. Otherwise = healthy
 *
 * @param artifact - The artifact to analyze
 * @returns Derived health status
 */
export function deriveHealthStatus(artifact: Artifact): HealthStatus {
  // Check for error states first
  if (artifact.syncStatus === 'error' || artifact.syncStatus === 'conflict') {
    return 'error';
  }

  // Check for upstream updates
  if (artifact.upstream?.updateAvailable) {
    return 'needs-update';
  }

  // Check for local modifications
  if (artifact.syncStatus === 'modified') {
    return 'has-drift';
  }

  // Default to healthy
  return 'healthy';
}

// ============================================================================
// Component
// ============================================================================

/**
 * HealthIndicator - Display artifact health with optional tooltip
 *
 * Shows a color-coded icon representing the artifact's health status.
 * Optionally wraps in a tooltip with a description of what the status means.
 *
 * @param artifact - The artifact to derive health from
 * @param size - Size variant (sm, md, lg)
 * @param showTooltip - Whether to show descriptive tooltip
 * @param className - Additional CSS classes
 */
export function HealthIndicator({
  artifact,
  size = 'md',
  showTooltip = true,
  className,
}: HealthIndicatorProps) {
  const health = deriveHealthStatus(artifact);
  const config = healthConfigs[health];
  const Icon = config.icon;

  const indicator = (
    <div
      className={cn('flex items-center', className)}
      role="status"
      aria-label={`Health: ${health.replace('-', ' ')}`}
    >
      <Icon className={cn(config.color, sizeClasses[size])} aria-hidden="true" />
    </div>
  );

  if (!showTooltip) {
    return indicator;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{indicator}</TooltipTrigger>
        <TooltipContent>
          <p className="text-sm">{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
