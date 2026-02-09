'use client';

/**
 * BatchActionBar Component
 *
 * Fixed bottom toolbar that slides up when memory items are selected.
 * Provides bulk approve, reject, and clear-selection actions.
 *
 * Design spec reference: section 3.9
 */

import { Check, X, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface BatchActionBarProps {
  /** Number of currently selected items. */
  selectedCount: number;
  /** Approve (promote) all selected items. */
  onApproveAll: () => void;
  /** Reject (deprecate) all selected items. */
  onRejectAll: () => void;
  /** Permanently delete all selected items. */
  onDeleteAll: () => void;
  /** Clear the current selection. */
  onClearSelection: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * BatchActionBar -- fixed bottom toolbar for batch memory operations.
 *
 * Slides up with a CSS transform when `selectedCount > 0` and slides
 * back down when the selection is cleared. Uses backdrop-blur for a
 * polished overlay appearance.
 *
 * @example
 * ```tsx
 * <BatchActionBar
 *   selectedCount={selectedIds.size}
 *   onApproveAll={handleBatchApprove}
 *   onRejectAll={handleBatchReject}
 *   onClearSelection={clearSelection}
 * />
 * ```
 */
export function BatchActionBar({
  selectedCount,
  onApproveAll,
  onRejectAll,
  onDeleteAll,
  onClearSelection,
}: BatchActionBarProps) {
  return (
    <>
      {/* Live region for screen reader announcements */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {selectedCount > 0
          ? `${selectedCount} ${selectedCount === 1 ? 'item' : 'items'} selected. Use Approve or Reject to batch-process.`
          : ''}
      </div>

      {/* Toolbar */}
      <div
        className={cn(
          'fixed bottom-0 left-0 right-0 z-40',
          'border-t bg-background/95 backdrop-blur-sm',
          'flex items-center justify-between px-6 h-14',
          'transform transition-transform duration-200 ease-out',
          selectedCount > 0 ? 'translate-y-0' : 'translate-y-full'
        )}
        role="toolbar"
        aria-label="Batch actions"
      >
        <span className="text-sm font-medium">
          {selectedCount} {selectedCount === 1 ? 'item' : 'items'} selected
        </span>

        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={onClearSelection} aria-label="Clear selection">
            Clear
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
            onClick={onRejectAll}
            aria-label={`Reject ${selectedCount} selected ${selectedCount === 1 ? 'item' : 'items'}`}
          >
            <X className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
            Reject
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onDeleteAll}
            aria-label={`Delete ${selectedCount} selected ${selectedCount === 1 ? 'item' : 'items'}`}
          >
            <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
            Delete
          </Button>
          <Button size="sm" onClick={onApproveAll} aria-label={`Approve ${selectedCount} selected ${selectedCount === 1 ? 'item' : 'items'}`}>
            <Check className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
            Approve
          </Button>
        </div>
      </div>
    </>
  );
}
