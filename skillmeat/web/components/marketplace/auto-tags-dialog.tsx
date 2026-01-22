/**
 * Auto-Tags Dialog Component
 *
 * Dialog for reviewing and approving/rejecting auto-tags extracted from
 * GitHub repository topics. When approved, tags are automatically added
 * to the source's tag list.
 *
 * Features:
 * - Displays pending, approved, and rejected auto-tags
 * - Approve/reject actions with immediate feedback
 * - Shows when tags are added to source
 * - Status badges for each tag state
 * - Full accessibility support
 *
 * @example
 * ```tsx
 * <AutoTagsDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   sourceId="source-123"
 * />
 * ```
 */

'use client';

import { useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Check, X, Loader2, Tag, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSourceAutoTags, useUpdateAutoTag, useToast } from '@/hooks';
import type { AutoTagSegment } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

export interface AutoTagsDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Source ID to fetch auto-tags for */
  sourceId: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface AutoTagItemProps {
  segment: AutoTagSegment;
  onApprove: () => void;
  onReject: () => void;
  isUpdating: boolean;
}

function AutoTagItem({ segment, onApprove, onReject, isUpdating }: AutoTagItemProps) {
  const statusConfig = {
    pending: {
      label: 'Pending',
      className: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
    },
    approved: {
      label: 'Approved',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    rejected: {
      label: 'Rejected',
      className: 'border-gray-500 text-gray-700 bg-gray-50 dark:bg-gray-950',
    },
  };

  const config = statusConfig[segment.status];

  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg border p-3 transition-colors',
        segment.status === 'pending' && 'border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/20',
        segment.status === 'approved' && 'border-green-200 bg-green-50/50 dark:bg-green-950/20',
        segment.status === 'rejected' && 'border-gray-200 bg-gray-50/50 dark:bg-gray-950/20'
      )}
    >
      <div className="flex items-center gap-3">
        <Tag className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <div>
          <span className="font-medium">{segment.value}</span>
          {segment.normalized !== segment.value && (
            <span className="ml-2 text-sm text-muted-foreground">
              (normalized: {segment.normalized})
            </span>
          )}
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="outline" className={config.className}>
              {config.label}
            </Badge>
            {segment.source && (
              <span className="text-xs text-muted-foreground">from {segment.source}</span>
            )}
          </div>
        </div>
      </div>

      {segment.status === 'pending' && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onReject}
            disabled={isUpdating}
            className="text-gray-600 hover:bg-gray-100 hover:text-gray-700"
            aria-label={`Reject tag: ${segment.value}`}
          >
            {isUpdating ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <X className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onApprove}
            disabled={isUpdating}
            className="text-green-600 hover:bg-green-100 hover:text-green-700"
            aria-label={`Approve tag: ${segment.value}`}
          >
            {isUpdating ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Check className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      )}

      {segment.status === 'approved' && (
        <Badge variant="secondary" className="text-green-600">
          <Check className="mr-1 h-3 w-3" aria-hidden="true" />
          Added to source
        </Badge>
      )}

      {segment.status === 'rejected' && (
        <Badge variant="secondary" className="text-gray-500">
          <X className="mr-1 h-3 w-3" aria-hidden="true" />
          Skipped
        </Badge>
      )}
    </div>
  );
}

function AutoTagItemSkeleton() {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-4 w-4" />
        <div>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="mt-1 h-4 w-20" />
        </div>
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-8 w-8" />
        <Skeleton className="h-8 w-8" />
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function AutoTagsDialog({ open, onOpenChange, sourceId }: AutoTagsDialogProps) {
  const { toast } = useToast();
  const { data, isLoading, error } = useSourceAutoTags(sourceId);
  const updateMutation = useUpdateAutoTag(sourceId);

  // Sort segments: pending first, then approved, then rejected
  const sortedSegments = useMemo(() => {
    if (!data?.segments) return [];

    const statusOrder = { pending: 0, approved: 1, rejected: 2 };
    return [...data.segments].sort((a, b) => {
      return statusOrder[a.status] - statusOrder[b.status];
    });
  }, [data?.segments]);

  const pendingCount = sortedSegments.filter((s) => s.status === 'pending').length;
  const approvedCount = sortedSegments.filter((s) => s.status === 'approved').length;

  const handleApprove = async (segment: AutoTagSegment) => {
    try {
      const result = await updateMutation.mutateAsync({
        value: segment.value,
        status: 'approved',
      });
      if (result.tags_added.length > 0) {
        toast({
          title: 'Tag approved',
          description: `"${segment.value}" has been added to source tags`,
        });
      }
    } catch (err) {
      toast({
        title: 'Failed to approve tag',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleReject = async (segment: AutoTagSegment) => {
    try {
      await updateMutation.mutateAsync({
        value: segment.value,
        status: 'rejected',
      });
      toast({
        title: 'Tag rejected',
        description: `"${segment.value}" will not be added`,
      });
    } catch (err) {
      toast({
        title: 'Failed to reject tag',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg"
        onCloseAutoFocus={(e) => e.preventDefault()}
        aria-describedby="auto-tags-dialog-description"
      >
        <DialogHeader>
          <DialogTitle>Auto-Tags from GitHub Topics</DialogTitle>
          <DialogDescription id="auto-tags-dialog-description">
            Review and approve tags extracted from the repository's GitHub topics. Approved tags
            will be added to the source's tag list.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <AutoTagItemSkeleton key={i} />
              ))}
            </div>
          ) : error ? (
            <div
              className="flex flex-col items-center justify-center py-8 text-center"
              role="alert"
            >
              <AlertCircle className="mb-2 h-8 w-8 text-destructive" aria-hidden="true" />
              <p className="font-medium text-destructive">Failed to load auto-tags</p>
              <p className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          ) : sortedSegments.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground"
              role="status"
              aria-label="No auto-tags available"
            >
              <Tag className="mb-2 h-8 w-8" aria-hidden="true" />
              <p>No auto-tags available for this source.</p>
              <p className="text-sm">The repository may not have any GitHub topics configured.</p>
            </div>
          ) : (
            <>
              {/* Summary */}
              <div className="mb-4 flex items-center gap-4 text-sm text-muted-foreground">
                {pendingCount > 0 && (
                  <span>
                    {pendingCount} pending review
                  </span>
                )}
                {approvedCount > 0 && (
                  <span className="text-green-600">
                    {approvedCount} approved
                  </span>
                )}
              </div>

              <ScrollArea className="h-[300px] pr-4">
                <div className="space-y-3" role="list" aria-label="Auto-tags list">
                  {sortedSegments.map((segment) => (
                    <div key={segment.value} role="listitem">
                      <AutoTagItem
                        segment={segment}
                        onApprove={() => handleApprove(segment)}
                        onReject={() => handleReject(segment)}
                        isUpdating={updateMutation.isPending}
                      />
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
