'use client';

import { useEffect } from 'react';
import { format } from 'date-fns';
import {
  Plus,
  Minus,
  FileEdit,
  GitCompare,
  X,
  FileText,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { useDiffSnapshots, useSnapshot } from '@/hooks';
import type { SnapshotDiff } from '@/types/snapshot';
import { cn } from '@/lib/utils';

/**
 * Props for VersionComparisonView component
 */
export interface VersionComparisonViewProps {
  /** First snapshot ID (older version) */
  snapshotId1: string;
  /** Second snapshot ID (newer version) */
  snapshotId2: string;
  /** Optional collection name */
  collectionName?: string;
  /** Callback when user closes the comparison view */
  onClose?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Loading skeleton for comparison view
 */
function ComparisonSkeleton() {
  return (
    <div className="space-y-4">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-8 w-8 rounded-md" />
      </div>

      {/* Stats skeleton */}
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>

      {/* Content skeleton */}
      <div className="space-y-2">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-20" />
      </div>
    </div>
  );
}

/**
 * Error display component
 */
function ErrorDisplay({ error, onClose }: { error: Error; onClose?: () => void }) {
  return (
    <Card className="border-destructive">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-destructive">Error Loading Comparison</CardTitle>
          {onClose && (
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{error.message}</p>
      </CardContent>
    </Card>
  );
}

/**
 * File list section component
 */
function FileSection({
  title,
  files,
  icon: Icon,
  badgeVariant,
  emptyMessage,
}: {
  title: string;
  files: string[];
  icon: typeof Plus;
  badgeVariant: 'default' | 'secondary' | 'destructive';
  emptyMessage: string;
}) {
  if (files.length === 0) {
    return (
      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <Icon className="h-4 w-4" />
          {title}
        </h3>
        <p className="text-sm text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
        <Icon className="h-4 w-4" />
        {title} ({files.length})
      </h3>
      <div className="flex flex-wrap gap-2">
        {files.map((file, index) => (
          <Badge key={index} variant={badgeVariant} className="font-mono text-xs">
            <FileText className="mr-1 h-3 w-3" />
            {file}
          </Badge>
        ))}
      </div>
    </div>
  );
}

/**
 * VersionComparisonView - Compare two version snapshots
 *
 * Displays a detailed comparison between two snapshots showing:
 * - Snapshot metadata (IDs, timestamps)
 * - Statistics summary (total changes, lines added/removed)
 * - Files added, removed, and modified with visual indicators
 *
 * Features:
 * - Automatic diff loading on mount
 * - Loading skeleton during diff computation
 * - Error handling with user feedback
 * - Color-coded file changes (green for additions, red for deletions, amber for modifications)
 * - Close button with optional callback
 *
 * @example
 * Basic usage:
 * ```tsx
 * <VersionComparisonView
 *   snapshotId1="abc123..."
 *   snapshotId2="def456..."
 *   collectionName="default"
 *   onClose={() => setShowComparison(false)}
 * />
 * ```
 *
 * @param props - VersionComparisonViewProps configuration
 * @returns Comparison view component with diff visualization
 */
export function VersionComparisonView({
  snapshotId1,
  snapshotId2,
  collectionName,
  onClose,
  className,
}: VersionComparisonViewProps) {
  // Fetch snapshot details
  const { data: snapshot1 } = useSnapshot(snapshotId1, collectionName);
  const { data: snapshot2 } = useSnapshot(snapshotId2, collectionName);

  // Fetch diff between snapshots
  const {
    mutate: fetchDiff,
    data: diff,
    isLoading,
    error,
  } = useDiffSnapshots();

  // Load diff on mount or when IDs change
  useEffect(() => {
    fetchDiff({
      snapshotId1,
      snapshotId2,
      collectionName,
    });
  }, [snapshotId1, snapshotId2, collectionName, fetchDiff]);

  // Show loading state
  if (isLoading) {
    return (
      <div className={cn('rounded-lg border bg-card p-6', className)}>
        <ComparisonSkeleton />
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className={className}>
        <ErrorDisplay error={error as Error} onClose={onClose} />
      </div>
    );
  }

  // No diff data yet
  if (!diff) {
    return null;
  }

  // Calculate total files changed
  const totalFilesChanged = diff.filesAdded.length + diff.filesRemoved.length + diff.filesModified.length;

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="border-b">
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-1">
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              Version Comparison
            </CardTitle>
            <div className="flex flex-col gap-1 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs">{snapshotId1.substring(0, 8)}</span>
                {snapshot1 && (
                  <>
                    <span>•</span>
                    <span>{format(new Date(snapshot1.timestamp), 'PPp')}</span>
                    {snapshot1.message && (
                      <>
                        <span>•</span>
                        <span className="italic">{snapshot1.message}</span>
                      </>
                    )}
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs">{snapshotId2.substring(0, 8)}</span>
                {snapshot2 && (
                  <>
                    <span>•</span>
                    <span>{format(new Date(snapshot2.timestamp), 'PPp')}</span>
                    {snapshot2.message && (
                      <>
                        <span>•</span>
                        <span className="italic">{snapshot2.message}</span>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
          {onClose && (
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-6">
        {/* Statistics Summary */}
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Total Changes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalFilesChanged}</div>
              <p className="text-xs text-muted-foreground">files modified</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-1 text-sm font-medium text-green-600 dark:text-green-400">
                <TrendingUp className="h-4 w-4" />
                Lines Added
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                +{diff.totalLinesAdded}
              </div>
              <p className="text-xs text-muted-foreground">insertions</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-1 text-sm font-medium text-red-600 dark:text-red-400">
                <TrendingDown className="h-4 w-4" />
                Lines Removed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                -{diff.totalLinesRemoved}
              </div>
              <p className="text-xs text-muted-foreground">deletions</p>
            </CardContent>
          </Card>
        </div>

        <Separator className="my-6" />

        {/* File Changes */}
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-6">
            {/* Added Files */}
            <FileSection
              title="Added Files"
              files={diff.filesAdded}
              icon={Plus}
              badgeVariant="default"
              emptyMessage="No files added"
            />

            {/* Modified Files */}
            <FileSection
              title="Modified Files"
              files={diff.filesModified}
              icon={FileEdit}
              badgeVariant="secondary"
              emptyMessage="No files modified"
            />

            {/* Removed Files */}
            <FileSection
              title="Removed Files"
              files={diff.filesRemoved}
              icon={Minus}
              badgeVariant="destructive"
              emptyMessage="No files removed"
            />
          </div>
        </ScrollArea>

        {/* Empty State */}
        {totalFilesChanged === 0 && (
          <div className="flex h-[400px] items-center justify-center">
            <div className="text-center">
              <GitCompare className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-sm font-medium">No Changes Detected</p>
              <p className="mt-1 text-sm text-muted-foreground">
                These snapshots are identical
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
