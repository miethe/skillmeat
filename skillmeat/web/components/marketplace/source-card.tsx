/**
 * Source Card Component
 *
 * Displays a GitHub repository source with artifact counts, status badges,
 * and quick actions (rescan, view details).
 *
 * Visual design follows the unified card style with colored left border accents.
 */

'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  Github,
  RefreshCw,
  ExternalLink,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Shield,
  ShieldCheck,
  Star,
  Loader2,
  Pencil,
  Trash2,
  Search,
  SearchCheck,
  SearchX,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { GitHubSource, TrustLevel, ScanStatus } from '@/types/marketplace';
import { TagBadge } from './tag-badge';
import { CountBadge } from './count-badge';

// ============================================================================
// Sub-components
// ============================================================================

interface TrustBadgeProps {
  level: TrustLevel;
}

function TrustBadge({ level }: TrustBadgeProps) {
  const config = {
    untrusted: {
      icon: Shield,
      label: 'Untrusted',
      description: 'This source has not been verified',
      className: 'border-gray-300 text-gray-600 bg-gray-50 dark:bg-gray-900',
    },
    basic: {
      icon: Shield,
      label: 'Basic',
      description: 'This source has basic trust verification',
      className: 'border-gray-400 text-gray-700 bg-gray-100 dark:bg-gray-800',
    },
    verified: {
      icon: ShieldCheck,
      label: 'Verified',
      description: 'This source has been verified as trustworthy',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
    },
    official: {
      icon: Star,
      label: 'Official',
      description: 'This is an official Anthropic source',
      className: 'border-purple-500 text-purple-700 bg-purple-50 dark:bg-purple-950',
    },
  }[level];

  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex h-6 w-6 items-center justify-center rounded-md border',
              config.className
            )}
            aria-label={`Trust level: ${config.label}. ${config.description}`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="font-medium">Trust: {config.label}</p>
          <p className="text-xs text-muted-foreground">{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface StatusBadgeProps {
  status: ScanStatus;
  errorMessage?: string;
  lastSyncAt?: string;
}

/**
 * Formats a timestamp into a friendly display format.
 * Returns "Jan 25, 2026 at 2:30 PM" style or relative time for recent dates.
 */
function formatTimestamp(timestamp: string | undefined): string {
  if (!timestamp) return 'Never';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  // Use relative time for recent timestamps (within 24 hours)
  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    if (diffMinutes < 1) return 'Just now';
    return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
  }
  if (diffHours < 24) {
    const hours = Math.floor(diffHours);
    return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  }

  // Use absolute format for older timestamps
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function StatusBadge({ status, errorMessage, lastSyncAt }: StatusBadgeProps) {
  const config = {
    pending: {
      icon: Clock,
      label: 'Pending',
      description: 'Scan is pending',
      className: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
    },
    scanning: {
      icon: Loader2,
      label: 'Scanning',
      description: 'Currently scanning for artifacts',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950 animate-pulse',
      iconClassName: 'animate-spin',
    },
    success: {
      icon: CheckCircle2,
      label: 'Synced',
      description: 'Successfully synced with repository',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    error: {
      icon: AlertTriangle,
      label: 'Error',
      description: 'An error occurred during scan',
      className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950',
    },
  }[status];

  const Icon = config.icon;
  const ariaLabel =
    status === 'error' && errorMessage
      ? `Scan status: ${config.label}. ${errorMessage}`
      : `Scan status: ${config.label}. ${config.description}`;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex h-6 w-6 items-center justify-center rounded-md border',
              config.className
            )}
            aria-label={ariaLabel}
          >
            <Icon
              className={cn('h-3.5 w-3.5', 'iconClassName' in config && config.iconClassName)}
              aria-hidden="true"
            />
          </div>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-medium">Sync: {config.label}</p>
          <p className="text-xs text-muted-foreground">
            {status === 'error' && errorMessage ? errorMessage : config.description}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Last synced: {formatTimestamp(lastSyncAt)}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface IndexingBadgeProps {
  indexingEnabled: boolean | null;
  lastIndexedTreeSha?: string | null;
  lastIndexedAt?: string | null;
}

function IndexingBadge({ indexingEnabled, lastIndexedTreeSha, lastIndexedAt }: IndexingBadgeProps) {
  // Determine indexing state
  let state: 'disabled' | 'pending' | 'indexed' | 'default';
  if (indexingEnabled === false) {
    state = 'disabled';
  } else if (indexingEnabled === true && !lastIndexedTreeSha) {
    state = 'pending';
  } else if (indexingEnabled === true && lastIndexedTreeSha) {
    state = 'indexed';
  } else {
    state = 'default';
  }

  const config = {
    disabled: {
      icon: SearchX,
      label: 'Disabled',
      description: 'Search indexing is disabled for this source',
      className: 'border-gray-300 text-gray-500 bg-gray-50 dark:bg-gray-900',
    },
    pending: {
      icon: Search,
      label: 'Pending',
      description: 'Source has not been indexed yet',
      className: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
    },
    indexed: {
      icon: SearchCheck,
      label: 'Active',
      description: 'Search index is active',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    default: {
      icon: Search,
      label: 'Default',
      description: 'Using default indexing settings',
      className: 'border-gray-200 text-gray-400 bg-gray-50/50 dark:bg-gray-900/50',
    },
  }[state];

  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex h-6 w-6 items-center justify-center rounded-md border',
              config.className
            )}
            aria-label={`Search Index: ${config.label}. ${config.description}`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </div>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-medium">Search Index: {config.label}</p>
          <p className="text-xs text-muted-foreground">{config.description}</p>
          {state === 'indexed' && lastIndexedAt && (
            <p className="mt-1 text-xs text-muted-foreground">
              Last indexed: {formatTimestamp(lastIndexedAt)}
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export interface SourceCardProps {
  /** GitHub source data */
  source: GitHubSource;
  /** Callback when rescan button is clicked */
  onRescan?: (sourceId: string) => void;
  /** Whether rescan is in progress */
  isRescanning?: boolean;
  /** Custom click handler (default: navigate to detail page) */
  onClick?: () => void;
  /** Callback when edit button is clicked */
  onEdit?: (source: GitHubSource) => void;
  /** Callback when delete button is clicked */
  onDelete?: (source: GitHubSource) => void;
  /** Callback when a tag is clicked (for filtering) */
  onTagClick?: (tag: string) => void;
}

export function SourceCard({
  source,
  onRescan,
  isRescanning = false,
  onClick,
  onEdit,
  onDelete,
  onTagClick,
}: SourceCardProps) {
  const router = useRouter();

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      router.push(`/marketplace/sources/${source.id}`);
    }
  };

  const handleRescan = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRescan?.(source.id);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(source);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(source);
  };

  const handleSourceClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const githubUrl = `https://github.com/${source.owner}/${source.repo_name}`;
    window.open(githubUrl, '_blank', 'noopener,noreferrer');
  };

  // Use counts_by_type if available, otherwise fallback to legacy artifact_count
  const countsByType = source.counts_by_type ?? { skill: source.artifact_count };

  // Description with fallback to repo_description
  const displayDescription = source.description || source.repo_description;

  // Format last sync time
  const lastSyncFormatted = source.last_sync_at
    ? new Date(source.last_sync_at).toLocaleString()
    : 'Never synced';

  return (
    <Card
      className={cn(
        'group relative cursor-pointer border-l-4 border-l-blue-500',
        'transition-shadow duration-200 hover:shadow-md',
        'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]'
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`View source: ${source.owner}/${source.repo_name}`}
    >
      <div className="space-y-3 p-4">
        {/* Header: Repo name + badges */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Github className="h-5 w-5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="min-w-0">
              <h3 className="truncate font-semibold">
                {source.owner}/{source.repo_name}
              </h3>
              <p className="text-xs text-muted-foreground">
                {source.ref}
                {source.root_hint && ` • ${source.root_hint}`}
              </p>
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center gap-1">
            <StatusBadge
              status={source.scan_status}
              errorMessage={source.last_error}
              lastSyncAt={source.last_sync_at}
            />
            <TrustBadge level={source.trust_level} />
            <IndexingBadge
              indexingEnabled={source.indexing_enabled ?? null}
              lastIndexedTreeSha={source.last_indexed_tree_sha}
              lastIndexedAt={source.last_indexed_at}
            />
          </div>
        </div>

        {/* Content - Fixed-height rows for consistent card heights */}
        <div className="flex min-h-[80px] flex-col">
          {/* Description - flex-grow to fill available space */}
          <div className="min-h-[40px] flex-grow">
            <p className="line-clamp-2 text-sm text-muted-foreground">
              {displayDescription || '\u00A0'}
            </p>
          </div>

          {/* Tags and artifact counts - fixed height */}
          <div className="flex h-6 items-center justify-between gap-2">
            <TagBadge tags={source.tags ?? []} maxDisplay={3} onTagClick={onTagClick} />
            <CountBadge countsByType={countsByType} />
          </div>
        </div>

        {/* Footer: Last sync + actions */}
        <div className="flex items-center justify-between border-t pt-2">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" aria-hidden="true" />
            <span aria-label={`Last synced: ${lastSyncFormatted}`}>{lastSyncFormatted}</span>
          </span>
          <div className="flex items-center gap-1">
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={handleEdit} aria-label="Edit source">
                <Pencil className="h-4 w-4" />
                <span className="sr-only">Edit</span>
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={handleDelete}
                aria-label="Delete source"
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRescan}
              disabled={isRescanning || source.scan_status === 'scanning'}
              aria-label="Rescan repository"
            >
              <RefreshCw
                className={cn(
                  'h-4 w-4',
                  (isRescanning || source.scan_status === 'scanning') && 'animate-spin'
                )}
              />
              <span className="sr-only">Rescan</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSourceClick}
              aria-label="Open GitHub repository"
            >
              <span className="text-xs">Source</span>
              <ExternalLink className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ============================================================================
// Skeleton
// ============================================================================

export function SourceCardSkeleton() {
  return (
    <Card className="border-l-4 border-l-muted">
      <div className="space-y-3 p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <div className="space-y-1">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
          <div className="flex gap-1">
            <Skeleton className="h-6 w-6 rounded-md" />
            <Skeleton className="h-6 w-6 rounded-md" />
            <Skeleton className="h-6 w-6 rounded-md" />
          </div>
        </div>

        {/* Content - Fixed-height to match card */}
        <div className="flex min-h-[80px] flex-col">
          {/* Description skeleton */}
          <div className="min-h-[40px] flex-grow space-y-1">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>

          {/* Tags and counts skeleton - fixed height */}
          <div className="flex h-6 items-center justify-between gap-2">
            <div className="flex gap-1">
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-5 w-14 rounded-full" />
              <Skeleton className="w-18 h-5 rounded-full" />
            </div>
            <Skeleton className="h-5 w-8 rounded-full" />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t pt-2">
          <Skeleton className="h-4 w-32" />
          <div className="flex gap-1">
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-8 w-16 rounded-md" />
          </div>
        </div>
      </div>
    </Card>
  );
}
