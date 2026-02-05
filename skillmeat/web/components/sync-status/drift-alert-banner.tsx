'use client';

import {
  CheckCircle2,
  Edit,
  Clock,
  AlertTriangle,
  Eye,
  GitMerge,
  ArrowUp,
  ArrowDown,
  X,
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type DriftStatus = 'none' | 'modified' | 'outdated' | 'conflict';
export type ComparisonScope =
  | 'collection-vs-project'
  | 'source-vs-collection'
  | 'source-vs-project';

export interface DriftAlertBannerProps {
  driftStatus: DriftStatus;
  comparisonScope: ComparisonScope;
  summary: {
    added: number;
    modified: number;
    deleted: number;
    unchanged: number;
  };
  onViewDiffs: () => void;
  onMerge: () => void;
  onTakeUpstream: () => void;
  onKeepLocal: () => void;
  /** Optional callback when the user dismisses this banner */
  onDismiss?: () => void;
}

/**
 * Get alert variant based on drift status
 */
function getAlertVariant(status: DriftStatus): 'default' | 'destructive' {
  return status === 'conflict' ? 'destructive' : 'default';
}

/**
 * Get background color class based on drift status
 */
function getBackgroundColor(status: DriftStatus): string {
  switch (status) {
    case 'none':
      return 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900';
    case 'modified':
      return 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900';
    case 'outdated':
      return 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900';
    case 'conflict':
      return 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900';
    default:
      return '';
  }
}

/**
 * Get status icon component
 */
function getStatusIcon(status: DriftStatus) {
  const iconClass = 'h-5 w-5 flex-shrink-0';

  switch (status) {
    case 'none':
      return <CheckCircle2 className={cn(iconClass, 'text-green-600 dark:text-green-500')} />;
    case 'modified':
      return <Edit className={cn(iconClass, 'text-amber-600 dark:text-amber-500')} />;
    case 'outdated':
      return <Clock className={cn(iconClass, 'text-orange-600 dark:text-orange-500')} />;
    case 'conflict':
      return <AlertTriangle className={cn(iconClass, 'text-red-600 dark:text-red-500')} />;
    default:
      return null;
  }
}

/**
 * Get status title text
 */
function getStatusTitle(status: DriftStatus): string {
  switch (status) {
    case 'none':
      return 'All Synced';
    case 'modified':
      return 'Drift Detected';
    case 'outdated':
      return 'Updates Available';
    case 'conflict':
      return 'Conflicts Detected';
    default:
      return 'Unknown Status';
  }
}

/**
 * Format summary stats into readable text
 */
function formatSummaryStats(summary: DriftAlertBannerProps['summary']): string {
  const parts: string[] = [];

  if (summary.added > 0) {
    parts.push(`${summary.added} added`);
  }
  if (summary.modified > 0) {
    parts.push(`${summary.modified} modified`);
  }
  if (summary.deleted > 0) {
    parts.push(`${summary.deleted} deleted`);
  }

  return parts.length > 0 ? parts.join(', ') : 'No changes';
}

/**
 * DriftAlertBanner - Alert banner showing drift status with contextual actions
 *
 * Displays drift status between different scopes (collection vs project, source vs collection, etc.)
 * with appropriate visual indicators and action buttons.
 *
 * Features:
 * - Color-coded status indicators (green/amber/orange/red)
 * - Status-specific icons
 * - Summary statistics of changes
 * - Contextual action buttons based on status
 * - Dark mode support
 *
 * @example
 * ```tsx
 * <DriftAlertBanner
 *   driftStatus="modified"
 *   comparisonScope="collection-vs-project"
 *   summary={{ added: 2, modified: 3, deleted: 1, unchanged: 10 }}
 *   onViewDiffs={() => console.log('View diffs')}
 *   onMerge={() => console.log('Merge')}
 *   onTakeUpstream={() => console.log('Take upstream')}
 *   onKeepLocal={() => console.log('Keep local')}
 * />
 * ```
 */
export function DriftAlertBanner({
  driftStatus,
  comparisonScope,
  summary,
  onViewDiffs,
  onMerge,
  onTakeUpstream,
  onKeepLocal,
  onDismiss,
}: DriftAlertBannerProps) {
  const totalChanges = summary.added + summary.modified + summary.deleted;
  const hasChanges = totalChanges > 0;

  // Determine which actions to show based on status
  const showActions = driftStatus !== 'none';
  const showMergeAction = driftStatus === 'conflict';
  const showTakeUpstreamAction =
    driftStatus === 'modified' || driftStatus === 'conflict' || driftStatus === 'outdated';
  const showKeepLocalAction = driftStatus === 'modified' || driftStatus === 'conflict';

  return (
    <Alert
      variant={getAlertVariant(driftStatus)}
      className={cn('relative', getBackgroundColor(driftStatus))}
    >
      <div className="flex items-start gap-3">
        {getStatusIcon(driftStatus)}

        <div className="flex min-w-0 flex-1 flex-col gap-3">

          <AlertDescription className="m-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-foreground">{getStatusTitle(driftStatus)}</span>
              {hasChanges && (
                <Badge variant="outline" className="text-xs">
                  {formatSummaryStats(summary)}
                </Badge>
              )}
            </div>
          </AlertDescription>

          {showActions && (
            <div className="flex flex-wrap items-center gap-2">
              {/* Always show View Diffs for non-synced states */}
              <Button
                variant="outline"
                size="sm"
                onClick={onViewDiffs}
                className="h-8 gap-1.5 text-xs"
              >
                <Eye className="h-3.5 w-3.5" />
                View Diffs
              </Button>

              {/* Merge action - for conflicts */}
              {showMergeAction && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={onMerge}
                  className="h-8 gap-1.5 text-xs"
                >
                  <GitMerge className="h-3.5 w-3.5" />
                  Merge...
                </Button>
              )}

              {/* Take Upstream - for modified/outdated/conflict */}
              {showTakeUpstreamAction && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onTakeUpstream}
                  className="h-8 gap-1.5 text-xs"
                >
                  <ArrowDown className="h-3.5 w-3.5" />
                  {driftStatus === 'outdated' ? 'Pull Updates' : 'Take Upstream'}
                </Button>
              )}

              {/* Keep Local - for modified/conflict */}
              {showKeepLocalAction && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onKeepLocal}
                  className="h-8 gap-1.5 text-xs"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                  Keep Local
                </Button>
              )}
            </div>
          )}
        </div>

        {onDismiss && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onDismiss}
            className="h-6 w-6 flex-shrink-0 rounded-full opacity-70 hover:opacity-100"
            aria-label="Dismiss drift alert"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </Alert>
  );
}
