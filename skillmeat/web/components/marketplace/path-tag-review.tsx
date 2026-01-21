/**
 * PathTagReview Component
 *
 * Displays extracted path segments for a marketplace entry and allows users
 * to approve or reject pending segments for tag generation.
 *
 * Features:
 * - Status-colored badges for each segment state
 * - Approve/reject actions for pending segments
 * - Loading, error, and empty states
 * - Summary footer with segment counts
 * - Dark mode support and responsive design
 */

'use client';

import * as React from 'react';
import { Check, X, AlertCircle, RefreshCw, Loader2, ArrowRight, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { usePathTags, useUpdatePathTagStatus } from '@/hooks';
import type { ExtractedSegment } from '@/types/path-tags';

// ============================================================================
// Types
// ============================================================================

export interface PathTagReviewProps {
  /** Marketplace source ID */
  sourceId: string;
  /** Catalog entry ID */
  entryId: string;
  /** Optional CSS class name */
  className?: string;
}

type SegmentStatus = ExtractedSegment['status'];

// ============================================================================
// Sub-components: StatusBadge
// ============================================================================

interface StatusBadgeProps {
  status: SegmentStatus;
  reason?: string;
}

const statusConfig: Record<SegmentStatus, { label: string; className: string }> = {
  pending: {
    label: 'Pending',
    className:
      'border-yellow-500 text-yellow-700 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950/50',
  },
  approved: {
    label: 'Approved',
    className:
      'border-green-500 text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-950/50',
  },
  rejected: {
    label: 'Rejected',
    className: 'border-red-500 text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-950/50',
  },
  excluded: {
    label: 'Excluded',
    className: 'border-gray-400 text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800/50',
  },
};

function StatusBadge({ status, reason }: StatusBadgeProps) {
  const config = statusConfig[status];

  if (reason) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className={cn('gap-1 text-xs', config.className)}>
              {config.label}
              <Info className="h-3 w-3" aria-hidden="true" />
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <p className="text-sm">{reason}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <Badge variant="outline" className={cn('text-xs', config.className)}>
      {config.label}
    </Badge>
  );
}

// ============================================================================
// Sub-components: SegmentRow
// ============================================================================

interface SegmentRowProps {
  segment: ExtractedSegment;
  isPending: boolean;
  onApprove: () => void;
  onReject: () => void;
}

function SegmentRow({ segment, isPending, onApprove, onReject }: SegmentRowProps) {
  const showActions = segment.status === 'pending';

  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 rounded-lg border p-3',
        'bg-card transition-colors',
        segment.status === 'pending' && 'border-yellow-200 dark:border-yellow-900/50',
        segment.status === 'approved' && 'border-green-200 dark:border-green-900/50',
        segment.status === 'rejected' && 'border-red-200 dark:border-red-900/50',
        segment.status === 'excluded' && 'border-gray-200 dark:border-gray-700'
      )}
    >
      {/* Segment values */}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <code className="rounded bg-muted px-2 py-0.5 font-mono text-sm">{segment.segment}</code>
          {segment.segment !== segment.normalized && (
            <>
              <ArrowRight
                className="h-3 w-3 flex-shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <span className="text-sm text-muted-foreground">{segment.normalized}</span>
            </>
          )}
        </div>
        {segment.status === 'excluded' && segment.reason && (
          <p className="text-xs italic text-muted-foreground">{segment.reason}</p>
        )}
      </div>

      {/* Status badge and actions */}
      <div className="flex flex-shrink-0 items-center gap-2">
        <StatusBadge status={segment.status} reason={segment.reason} />

        {showActions && (
          <div className="flex items-center gap-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-green-600 hover:bg-green-50 hover:text-green-700 dark:text-green-500 dark:hover:bg-green-950/50 dark:hover:text-green-400"
                    onClick={onApprove}
                    disabled={isPending}
                    aria-label="Approve segment"
                  >
                    {isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Check className="h-4 w-4" aria-hidden="true" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Approve segment</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-500 dark:hover:bg-red-950/50 dark:hover:text-red-400"
                    onClick={onReject}
                    disabled={isPending}
                    aria-label="Reject segment"
                  >
                    {isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <X className="h-4 w-4" aria-hidden="true" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reject segment</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Sub-components: PathTagSummary
// ============================================================================

interface PathTagSummaryProps {
  segments: ExtractedSegment[];
}

function PathTagSummary({ segments }: PathTagSummaryProps) {
  const counts = segments.reduce(
    (acc, seg) => {
      acc[seg.status] = (acc[seg.status] || 0) + 1;
      return acc;
    },
    {} as Record<SegmentStatus, number>
  );

  const items = [
    {
      status: 'approved' as const,
      count: counts.approved || 0,
      className: 'text-green-600 dark:text-green-400',
    },
    {
      status: 'rejected' as const,
      count: counts.rejected || 0,
      className: 'text-red-600 dark:text-red-400',
    },
    {
      status: 'pending' as const,
      count: counts.pending || 0,
      className: 'text-yellow-600 dark:text-yellow-400',
    },
    {
      status: 'excluded' as const,
      count: counts.excluded || 0,
      className: 'text-gray-500 dark:text-gray-400',
    },
  ];

  return (
    <div className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3 text-sm">
      {items.map(({ status, count, className }) => (
        <span key={status} className={cn('font-medium', className)}>
          {count} {status}
        </span>
      ))}
    </div>
  );
}

// ============================================================================
// Sub-components: Loading/Error/Empty States
// ============================================================================

function LoadingState() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading segments">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between gap-3 rounded-lg border p-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-16" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-8 w-8 rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
}

interface ErrorStateProps {
  error: Error;
  onRetry: () => void;
}

function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" aria-hidden="true" />
      <AlertTitle>Failed to load path segments</AlertTitle>
      <AlertDescription className="flex items-center justify-between gap-4">
        <span>{error.message || 'An unexpected error occurred'}</span>
        <Button variant="outline" size="sm" onClick={onRetry} className="flex-shrink-0">
          <RefreshCw className="mr-1 h-4 w-4" aria-hidden="true" />
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="mb-3 rounded-full bg-muted p-3">
        <Info className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-medium text-foreground">No segments extracted</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        This entry does not have any path segments to review.
      </p>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function PathTagReview({ sourceId, entryId, className }: PathTagReviewProps) {
  const { data, isLoading, error, refetch } = usePathTags(sourceId, entryId);
  const updateStatus = useUpdatePathTagStatus();

  const handleApprove = (segment: string) => {
    updateStatus.mutate({
      sourceId,
      entryId,
      segment,
      status: 'approved',
    });
  };

  const handleReject = (segment: string) => {
    updateStatus.mutate({
      sourceId,
      entryId,
      segment,
      status: 'rejected',
    });
  };

  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div className={className}>
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  if (!data?.extracted?.length) {
    return (
      <div className={className}>
        <EmptyState />
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {/* Raw path display */}
      {data.raw_path && (
        <div className="mb-3 text-xs text-muted-foreground">
          <span className="font-medium">Path:</span>{' '}
          <code className="rounded bg-muted px-1.5 py-0.5">{data.raw_path}</code>
        </div>
      )}

      {/* Segment list */}
      <ul className="list-none space-y-2">
        {data.extracted.map((segment) => (
          <li key={segment.segment}>
            <SegmentRow
              segment={segment}
              isPending={updateStatus.isPending}
              onApprove={() => handleApprove(segment.segment)}
              onReject={() => handleReject(segment.segment)}
            />
          </li>
        ))}
      </ul>

      {/* Summary footer */}
      <PathTagSummary segments={data.extracted} />
    </div>
  );
}

// ============================================================================
// Skeleton Export (for parent components)
// ============================================================================

export function PathTagReviewSkeleton() {
  return <LoadingState />;
}
