'use client';

import { useState } from 'react';
import { formatDistanceToNow, format } from 'date-fns';
import { Clock, Copy, RotateCcw, GitCompare, Eye, CheckCircle2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { useSnapshots } from '@/hooks';
import type { Snapshot } from '@/types/snapshot';
import { cn } from '@/lib/utils';

/**
 * Props for VersionTimeline component
 */
export interface VersionTimelineProps {
  /** Optional collection name filter */
  collectionName?: string;
  /** Callback when snapshot is selected for viewing */
  onSelectSnapshot?: (snapshotId: string) => void;
  /** Callback when two snapshots are selected for comparison */
  onCompare?: (snapshotId1: string, snapshotId2: string) => void;
  /** Callback when snapshot is selected for restoration */
  onRestore?: (snapshotId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * VersionTimeline - Display snapshot history in a vertical timeline
 *
 * Features:
 * - Vertical timeline with connected dots
 * - Formatted timestamps
 * - Snapshot details (message, artifact count, collection)
 * - Action buttons (view, compare, restore)
 * - Multi-select for comparison (max 2 snapshots)
 * - Loading and empty states
 *
 * @example
 * ```tsx
 * <VersionTimeline
 *   collectionName="default"
 *   onSelectSnapshot={(id) => console.log('View:', id)}
 *   onCompare={(id1, id2) => console.log('Compare:', id1, id2)}
 *   onRestore={(id) => console.log('Restore:', id)}
 * />
 * ```
 */
export function VersionTimeline({
  collectionName,
  onSelectSnapshot,
  onCompare,
  onRestore,
  className,
}: VersionTimelineProps) {
  const [selectedForCompare, setSelectedForCompare] = useState<Set<string>>(new Set());

  // Fetch snapshots with optional collection filter
  const { data, isLoading, error } = useSnapshots(collectionName ? { collectionName } : undefined);

  /**
   * Toggle snapshot selection for comparison
   */
  const toggleCompareSelection = (snapshotId: string) => {
    setSelectedForCompare((prev) => {
      const next = new Set(prev);
      if (next.has(snapshotId)) {
        next.delete(snapshotId);
      } else if (next.size < 2) {
        // Max 2 snapshots for comparison
        next.add(snapshotId);
      }
      return next;
    });
  };

  /**
   * Handle compare button click
   */
  const handleCompare = () => {
    if (selectedForCompare.size === 2 && onCompare) {
      const [id1, id2] = Array.from(selectedForCompare);
      onCompare(id1, id2);
      setSelectedForCompare(new Set()); // Clear selection after compare
    }
  };

  /**
   * Copy snapshot ID to clipboard
   */
  const copySnapshotId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id);
    } catch (err) {
      console.error('Failed to copy snapshot ID:', err);
    }
  };

  /**
   * Format timestamp for display
   */
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return {
      absolute: format(date, "MMM d, yyyy 'at' h:mm a"),
      relative: formatDistanceToNow(date, { addSuffix: true }),
    };
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex gap-4">
            <div className="flex flex-col items-center">
              <Skeleton className="h-3 w-3 rounded-full" />
              {i < 2 && <Skeleton className="my-2 h-16 w-0.5" />}
            </div>
            <Card className="flex-1">
              <CardContent className="p-4">
                <Skeleton className="mb-2 h-4 w-48" />
                <Skeleton className="mb-2 h-3 w-32" />
                <Skeleton className="h-3 w-24" />
              </CardContent>
            </Card>
          </div>
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('py-8 text-center', className)}>
        <p className="text-sm text-destructive">
          Failed to load snapshots: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  // Empty state
  if (!data || data.items.length === 0) {
    return (
      <div className={cn('py-8 text-center', className)}>
        <Clock className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No snapshots found</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {collectionName
            ? `Create your first snapshot for the "${collectionName}" collection`
            : 'Create your first snapshot'}
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Compare button (shown when 2 snapshots selected) */}
      {selectedForCompare.size === 2 && onCompare && (
        <div className="sticky top-0 z-10 border-b bg-background/95 pb-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <Button onClick={handleCompare} className="w-full" variant="default">
            <GitCompare className="mr-2 h-4 w-4" />
            Compare Selected Snapshots
          </Button>
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-0">
        {data.items.map((snapshot, index) => {
          const isSelected = selectedForCompare.has(snapshot.id);
          const timestamp = formatTimestamp(snapshot.timestamp);
          const isLast = index === data.items.length - 1;

          return (
            <div key={snapshot.id} className="flex gap-4">
              {/* Timeline connector */}
              <div className="flex flex-col items-center pt-2">
                {/* Dot */}
                <div
                  className={cn(
                    'h-3 w-3 rounded-full border-2 transition-colors',
                    isSelected
                      ? 'border-primary bg-primary'
                      : 'border-muted-foreground bg-background'
                  )}
                  aria-hidden="true"
                />
                {/* Vertical line */}
                {!isLast && (
                  <div className="my-2 h-full min-h-[4rem] w-0.5 bg-border" aria-hidden="true" />
                )}
              </div>

              {/* Snapshot card */}
              <Card
                className={cn(
                  'mb-6 flex-1 transition-shadow hover:shadow-md',
                  isSelected && 'ring-2 ring-primary'
                )}
              >
                <CardContent className="p-4">
                  {/* Header with timestamp and selection */}
                  <div className="mb-3 flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <Clock className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                        <time
                          dateTime={snapshot.timestamp}
                          className="text-sm font-medium"
                          title={timestamp.absolute}
                        >
                          {timestamp.relative}
                        </time>
                      </div>
                      <p className="text-xs text-muted-foreground">{timestamp.absolute}</p>
                    </div>

                    {onCompare && (
                      <div className="flex items-center gap-2">
                        <label
                          htmlFor={`compare-${snapshot.id}`}
                          className="cursor-pointer text-xs text-muted-foreground"
                        >
                          Compare
                        </label>
                        <Checkbox
                          id={`compare-${snapshot.id}`}
                          checked={isSelected}
                          onCheckedChange={() => toggleCompareSelection(snapshot.id)}
                          disabled={!isSelected && selectedForCompare.size >= 2}
                          aria-label={`Select snapshot for comparison: ${snapshot.message}`}
                        />
                      </div>
                    )}
                  </div>

                  {/* Message */}
                  <p className="mb-3 line-clamp-2 text-sm" title={snapshot.message}>
                    {snapshot.message || (
                      <span className="italic text-muted-foreground">No message</span>
                    )}
                  </p>

                  {/* Metadata badges */}
                  <div className="mb-4 flex flex-wrap gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {snapshot.artifactCount}{' '}
                      {snapshot.artifactCount === 1 ? 'artifact' : 'artifacts'}
                    </Badge>
                    {!collectionName && (
                      <Badge variant="outline" className="text-xs">
                        {snapshot.collectionName}
                      </Badge>
                    )}
                  </div>

                  {/* Snapshot ID */}
                  <div className="mb-4 flex items-center gap-2 rounded bg-muted p-2 font-mono text-xs">
                    <span className="text-muted-foreground">ID:</span>
                    <code className="flex-1 truncate" title={snapshot.id}>
                      {snapshot.id.substring(0, 8)}...
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copySnapshotId(snapshot.id)}
                      className="h-6 w-6 p-0"
                      aria-label="Copy full snapshot ID"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2">
                    {onSelectSnapshot && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onSelectSnapshot(snapshot.id)}
                        className="flex-1"
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View
                      </Button>
                    )}
                    {onRestore && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onRestore(snapshot.id)}
                        className="flex-1"
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Restore
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          );
        })}
      </div>

      {/* Pagination info */}
      {data.pageInfo.total > data.items.length && (
        <div className="border-t pt-4 text-center">
          <p className="text-xs text-muted-foreground">
            Showing {data.items.length} of {data.pageInfo.total} snapshots
          </p>
        </div>
      )}
    </div>
  );
}
