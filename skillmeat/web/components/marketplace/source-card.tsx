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
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { GitHubSource, TrustLevel, ScanStatus } from '@/types/marketplace';

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
      className: 'border-gray-300 text-gray-600 bg-gray-50 dark:bg-gray-900',
    },
    basic: {
      icon: Shield,
      label: 'Basic',
      className: 'border-gray-400 text-gray-700 bg-gray-100 dark:bg-gray-800',
    },
    verified: {
      icon: ShieldCheck,
      label: 'Verified',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
    },
    official: {
      icon: Star,
      label: 'Official',
      className: 'border-purple-500 text-purple-700 bg-purple-50 dark:bg-purple-950',
    },
  }[level];

  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn('gap-1 text-xs', config.className)}
          >
            <Icon className="h-3 w-3" />
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>Trust level: {config.label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface StatusBadgeProps {
  status: ScanStatus;
  errorMessage?: string;
}

function StatusBadge({ status, errorMessage }: StatusBadgeProps) {
  const config = {
    pending: {
      icon: Clock,
      label: 'Pending',
      className: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
    },
    scanning: {
      icon: Loader2,
      label: 'Scanning',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950 animate-pulse',
      iconClassName: 'animate-spin',
    },
    success: {
      icon: CheckCircle2,
      label: 'Synced',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    error: {
      icon: AlertTriangle,
      label: 'Error',
      className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950',
    },
  }[status];

  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn('gap-1 text-xs', config.className)}
          >
            <Icon className={cn('h-3 w-3', 'iconClassName' in config && config.iconClassName)} />
            {config.label}
          </Badge>
        </TooltipTrigger>
        {status === 'error' && errorMessage && (
          <TooltipContent className="max-w-xs">
            <p className="text-sm">{errorMessage}</p>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}

interface ArtifactCountsProps {
  counts: {
    skills?: number;
    commands?: number;
    agents?: number;
    mcp_servers?: number;
    hooks?: number;
  };
}

function ArtifactCounts({ counts }: ArtifactCountsProps) {
  const items = [
    { key: 'skills', label: 'Skills', count: counts.skills || 0 },
    { key: 'commands', label: 'Commands', count: counts.commands || 0 },
    { key: 'agents', label: 'Agents', count: counts.agents || 0 },
    { key: 'mcp_servers', label: 'MCP', count: counts.mcp_servers || 0 },
    { key: 'hooks', label: 'Hooks', count: counts.hooks || 0 },
  ].filter((item) => item.count > 0);

  if (items.length === 0) {
    return (
      <span className="text-sm text-muted-foreground">No artifacts detected</span>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item.key}
          className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs font-medium"
        >
          {item.label}: {item.count}
        </span>
      ))}
    </div>
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
}

export function SourceCard({
  source,
  onRescan,
  isRescanning = false,
  onClick,
  onEdit,
  onDelete,
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

  // Parse artifact counts from the single artifact_count field
  // TODO: Backend should return counts_by_type instead
  const artifactCounts = {
    skills: source.artifact_count,
    commands: 0,
    agents: 0,
    mcp_servers: 0,
    hooks: 0,
  };

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
      <div className="p-4 space-y-3">
        {/* Header: Repo name + badges */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Github className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <h3 className="font-semibold truncate">
                {source.owner}/{source.repo_name}
              </h3>
              <p className="text-xs text-muted-foreground">
                {source.ref}
                {source.root_hint && ` • ${source.root_hint}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <StatusBadge status={source.scan_status} errorMessage={source.last_error} />
            <TrustBadge level={source.trust_level} />
          </div>
        </div>

        {/* Description (truncated) */}
        {source.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {source.description}
          </p>
        )}

        {/* Artifact counts */}
        <ArtifactCounts counts={artifactCounts} />

        {/* Footer: Last sync + actions */}
        <div className="flex items-center justify-between pt-2 border-t">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {lastSyncFormatted}
          </span>
          <div className="flex items-center gap-1">
            {onEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleEdit}
                aria-label="Edit source"
              >
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
      <div className="p-4 space-y-3">
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
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>

        {/* Counts */}
        <div className="flex gap-2">
          <Skeleton className="h-6 w-20 rounded-md" />
          <Skeleton className="h-6 w-24 rounded-md" />
          <Skeleton className="h-6 w-16 rounded-md" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t">
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
