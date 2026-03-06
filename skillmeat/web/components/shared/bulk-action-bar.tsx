/**
 * BulkActionBar
 *
 * Generic floating bulk action bar that appears when items are selected.
 * Renders fixed at the bottom-center of the viewport with a smooth slide-up
 * transition when `hasSelection` becomes true.
 *
 * Usage:
 *   const actions: BulkAction[] = [
 *     {
 *       id: 'delete',
 *       label: 'Delete',
 *       icon: <Trash2 className="h-3.5 w-3.5" />,
 *       variant: 'destructive',
 *       onClick: handleDelete,
 *     },
 *   ];
 *
 *   <BulkActionBar
 *     selectedCount={selected.size}
 *     hasSelection={selected.size > 0}
 *     actions={actions}
 *     onClearSelection={() => setSelected(new Set())}
 *   />
 *
 * Accessibility:
 * - role="toolbar" with aria-label describing the selection count
 * - aria-hidden when not visible
 * - aria-live region announces selection count changes
 * - Each button has an explicit aria-label
 * - Clear button is keyboard-reachable and labelled
 */

'use client';

import * as React from 'react';
import { X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BulkAction {
  id: string;
  label: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost';
  onClick: () => void | Promise<void>;
  disabled?: boolean;
}

export interface BulkActionBarProps {
  /** Number of currently selected items. */
  selectedCount: number;
  /** Controls visibility (slide-up animation on true, slide-down on false). */
  hasSelection: boolean;
  /** Action buttons to render in the bar. */
  actions: BulkAction[];
  /** Called when the user clicks the Clear / X button. */
  onClearSelection: () => void;
  /** Optional extra className applied to the outer positioning wrapper. */
  className?: string;
}

// ---------------------------------------------------------------------------
// BulkActionBar
// ---------------------------------------------------------------------------

export function BulkActionBar({
  selectedCount,
  hasSelection,
  actions,
  onClearSelection,
  className,
}: BulkActionBarProps) {
  // Track which action id is currently loading.
  const [loadingId, setLoadingId] = React.useState<string | null>(null);

  const isAnyLoading = loadingId !== null;

  async function handleAction(action: BulkAction) {
    if (isAnyLoading || action.disabled) return;

    setLoadingId(action.id);
    try {
      await action.onClick();
    } finally {
      setLoadingId(null);
    }
  }

  const itemLabel = selectedCount === 1 ? 'item' : 'items';

  return (
    <div
      className={cn(
        // Positioning — fixed to bottom, centered
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
        // Visibility transition (slide + fade)
        'transition-all duration-200 ease-out',
        hasSelection
          ? 'translate-y-0 opacity-100 pointer-events-auto'
          : 'translate-y-4 opacity-0 pointer-events-none',
        className
      )}
      aria-hidden={!hasSelection}
    >
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl border border-border/60',
          'bg-background/95 backdrop-blur-sm shadow-xl px-4 py-2.5'
        )}
        role="toolbar"
        aria-label={`Bulk actions for ${selectedCount} selected ${itemLabel}`}
      >
        {/* Selection count */}
        <span className="text-sm font-medium text-foreground pr-2 border-r border-border/50 mr-1">
          <span aria-live="polite" aria-atomic="true">
            {selectedCount} selected
          </span>
        </span>

        {/* Action buttons */}
        {actions.map((action) => {
          const isCurrentlyLoading = loadingId === action.id;

          return (
            <Button
              key={action.id}
              variant={action.variant ?? 'ghost'}
              size="sm"
              className={cn(
                'h-8 gap-1.5 text-sm font-medium px-2.5',
                isCurrentlyLoading && 'opacity-70'
              )}
              disabled={isAnyLoading || !!action.disabled}
              aria-label={`${action.label} ${selectedCount} selected ${itemLabel}`}
              onClick={() => handleAction(action)}
            >
              {isCurrentlyLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : action.icon != null ? (
                <span className="h-3.5 w-3.5 flex items-center justify-center" aria-hidden="true">
                  {action.icon}
                </span>
              ) : null}
              {action.label}
            </Button>
          );
        })}

        {/* Divider + Clear */}
        <div className="h-5 w-px bg-border/50 mx-1" aria-hidden="true" />
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-foreground"
          aria-label="Clear selection"
          onClick={onClearSelection}
          disabled={isAnyLoading}
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
