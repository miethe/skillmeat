/**
 * Status Badge Component
 *
 * Displays artifact sync status with configurable icon and label.
 * Supports multiple status states with appropriate visual styling.
 *
 * @example Basic usage
 * ```tsx
 * <StatusBadge status="synced" />
 * ```
 *
 * @example Icon only
 * ```tsx
 * <StatusBadge status="modified" showLabel={false} size="sm" />
 * ```
 */

'use client';

import * as React from 'react';
import {
  CheckCircle2,
  Pencil,
  ArrowUp,
  GitMerge,
  AlertCircle,
  type LucideIcon,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { SyncStatus } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface StatusBadgeProps {
  /** Sync status to display */
  status: SyncStatus;
  /** Size variant affecting icon size and padding */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show the status icon */
  showIcon?: boolean;
  /** Whether to show the status label text */
  showLabel?: boolean;
  /** Additional CSS classes for the badge */
  className?: string;
}

// ============================================================================
// Configuration
// ============================================================================

interface StatusConfig {
  icon: LucideIcon;
  label: string;
  className: string;
}

const statusConfigs: Record<SyncStatus, StatusConfig> = {
  synced: {
    icon: CheckCircle2,
    label: 'Synced',
    className: 'bg-green-500/10 text-green-600 border-green-500/20 dark:text-green-400',
  },
  modified: {
    icon: Pencil,
    label: 'Modified',
    className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20 dark:text-yellow-400',
  },
  outdated: {
    icon: ArrowUp,
    label: 'Outdated',
    className: 'bg-orange-500/10 text-orange-600 border-orange-500/20 dark:text-orange-400',
  },
  conflict: {
    icon: GitMerge,
    label: 'Conflict',
    className: 'bg-destructive/10 text-destructive border-destructive/20',
  },
  error: {
    icon: AlertCircle,
    label: 'Error',
    className: 'bg-red-500/10 text-red-600 border-red-500/20 dark:text-red-400',
  },
};

const sizeClasses = {
  sm: {
    badge: 'px-1.5 py-0.5 text-xs',
    icon: 'h-3 w-3',
    gap: 'gap-1',
  },
  md: {
    badge: 'px-2 py-0.5 text-xs',
    icon: 'h-3.5 w-3.5',
    gap: 'gap-1.5',
  },
  lg: {
    badge: 'px-2.5 py-1 text-sm',
    icon: 'h-4 w-4',
    gap: 'gap-2',
  },
};

// ============================================================================
// Component
// ============================================================================

/**
 * StatusBadge - Display artifact sync status
 *
 * Renders a badge with an icon and/or label indicating the sync state
 * of an artifact. Color-coded for quick visual identification.
 *
 * @param status - The sync status value
 * @param size - Size variant (sm, md, lg)
 * @param showIcon - Whether to display the status icon
 * @param showLabel - Whether to display the status text
 * @param className - Additional CSS classes
 */
export function StatusBadge({
  status,
  size = 'md',
  showIcon = true,
  showLabel = true,
  className,
}: StatusBadgeProps) {
  const config = statusConfigs[status];
  const sizeConfig = sizeClasses[size];
  const Icon = config.icon;

  // Require at least icon or label
  if (!showIcon && !showLabel) {
    return null;
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        'inline-flex items-center font-medium',
        config.className,
        sizeConfig.badge,
        showIcon && showLabel && sizeConfig.gap,
        className
      )}
      aria-label={`Status: ${config.label}`}
    >
      {showIcon && (
        <Icon
          className={cn(sizeConfig.icon, showLabel && '-ml-0.5')}
          aria-hidden="true"
        />
      )}
      {showLabel && config.label}
    </Badge>
  );
}
