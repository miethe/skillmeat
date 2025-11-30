'use client';

import { ArrowDown, ArrowUp, GitMerge, Check, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface SyncActionsFooterProps {
  onPullCollectionUpdates: () => void;
  onPushLocalChanges: () => void;
  onMergeConflicts: () => void;
  onResolveAll: () => void;
  onCancel: () => void;
  onApply: () => void;
  hasPendingActions: boolean;
  hasConflicts: boolean;
  isApplying: boolean;
}

export function SyncActionsFooter({
  onPullCollectionUpdates,
  onPushLocalChanges,
  onMergeConflicts,
  onResolveAll,
  onCancel,
  onApply,
  hasPendingActions,
  hasConflicts,
  isApplying,
}: SyncActionsFooterProps) {
  return (
    <div className="flex items-center justify-between border-t bg-background p-4">
      {/* Left: Action buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="default"
          size="sm"
          onClick={onPullCollectionUpdates}
          disabled={isApplying}
        >
          <ArrowDown className="mr-2 h-4 w-4" />
          Pull Collection Updates
        </Button>

        <div title="Coming Soon: Push local changes to collection">
          <Button
            variant="ghost"
            size="sm"
            onClick={onPushLocalChanges}
            disabled={true}
          >
            <ArrowUp className="mr-2 h-4 w-4" />
            Push Local Changes
          </Button>
        </div>

        {hasConflicts && (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onMergeConflicts}
              disabled={isApplying}
              className="text-orange-600 hover:text-orange-700 dark:text-orange-400 dark:hover:text-orange-300"
            >
              <GitMerge className="mr-2 h-4 w-4" />
              Merge Conflicts
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onResolveAll}
              disabled={isApplying}
            >
              <Check className="mr-2 h-4 w-4" />
              Resolve All
            </Button>
          </>
        )}
      </div>

      {/* Right: Final action buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
          disabled={isApplying}
        >
          <X className="mr-2 h-4 w-4" />
          Cancel
        </Button>

        <Button
          variant="default"
          size="sm"
          onClick={onApply}
          disabled={!hasPendingActions || isApplying}
        >
          {isApplying ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Applying...
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              Apply Sync Actions
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
