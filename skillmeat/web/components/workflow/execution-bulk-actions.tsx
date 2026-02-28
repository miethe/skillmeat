/**
 * ExecutionBulkActions
 *
 * Floating bulk action bar that appears when executions are selected on the
 * All Executions page. Renders at the bottom of the viewport, centered, with
 * a smooth slide-in/out transition.
 *
 * Each action button shows how many of the selected executions it applies to
 * (e.g. "Cancel (3)"). Clicking executes mutations in parallel via
 * Promise.allSettled, then shows a toast summarizing results and clears selection.
 *
 * Accessibility:
 * - Role="toolbar" with aria-label for screen readers
 * - Each button has an accessible label with count
 * - Live region announces selection count
 */

'use client';

import * as React from 'react';
import {
  XCircle,
  Pause,
  Play,
  RotateCcw,
  X,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  useBatchPauseExecutions,
  useBatchCancelExecutions,
  useBatchResumeExecutions,
  useRunWorkflow,
} from '@/hooks';
import type { WorkflowExecution, BatchExecutionResponse } from '@/types/workflow';
import {
  getBulkActions,
  getApplicableExecutions,
  getActionLabel,
  type ExecutionAction,
} from '@/lib/workflow-action-utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExecutionBulkActionsProps {
  /** The currently selected executions. */
  selectedExecutions: WorkflowExecution[];
  /** Called after all mutations for a bulk action settle (to clear selection). */
  onClearSelection: () => void;
}

// ---------------------------------------------------------------------------
// Icon map
// ---------------------------------------------------------------------------

const ACTION_ICONS: Record<ExecutionAction, React.ElementType> = {
  cancel: XCircle,
  pause: Pause,
  resume: Play,
  rerun: RotateCcw,
};

// ---------------------------------------------------------------------------
// Bulk action color map (for button label text)
// ---------------------------------------------------------------------------

const ACTION_LABEL_COLOR: Record<ExecutionAction, string> = {
  cancel: 'text-destructive',
  pause: 'text-amber-500',
  resume: 'text-emerald-500',
  rerun: 'text-blue-500',
};

// ---------------------------------------------------------------------------
// ExecutionBulkActions
// ---------------------------------------------------------------------------

/**
 * Floating bar fixed to the bottom of the viewport that appears when one or
 * more executions are selected. Disappears when selection is empty.
 */
export function ExecutionBulkActions({
  selectedExecutions,
  onClearSelection,
}: ExecutionBulkActionsProps) {
  const batchCancel = useBatchCancelExecutions();
  const batchPause = useBatchPauseExecutions();
  const batchResume = useBatchResumeExecutions();
  const rerun = useRunWorkflow();

  const [pendingAction, setPendingAction] = React.useState<ExecutionAction | null>(null);

  const hasSelection = selectedExecutions.length > 0;
  const availableActions = getBulkActions(selectedExecutions);

  // ── Mutation dispatcher ────────────────────────────────────────────────────

  function buildBatchToast(
    label: string,
    response: BatchExecutionResponse,
    skipped: number
  ) {
    const { succeeded, failed } = response;
    if (failed === 0) {
      const skippedNote =
        skipped > 0
          ? ` (${skipped} skipped — not in a ${label.toLowerCase()}able state)`
          : '';
      toast.success(
        `${label}d ${succeeded} execution${succeeded !== 1 ? 's' : ''}${skippedNote}`
      );
    } else {
      toast.warning(`${label}d ${succeeded} of ${succeeded + failed}`, {
        description: `${failed} failed. ${skipped > 0 ? `${skipped} skipped (wrong state).` : ''}`,
      });
    }
  }

  async function handleBulkAction(action: ExecutionAction) {
    const applicable = getApplicableExecutions(selectedExecutions, action);
    if (applicable.length === 0) return;

    setPendingAction(action);
    const label = getActionLabel(action);
    const skipped = selectedExecutions.length - applicable.length;

    try {
      if (action === 'rerun') {
        // rerun has no batch endpoint — keep Promise.allSettled for now
        const results = await Promise.allSettled(
          applicable.map((execution) =>
            rerun.mutateAsync({
              workflowId: execution.workflowId,
              parameters: execution.parameters as Record<string, unknown> | undefined,
            })
          )
        );
        const succeeded = results.filter((r) => r.status === 'fulfilled').length;
        const failed = results.filter((r) => r.status === 'rejected').length;
        if (failed === 0) {
          toast.success(`Re-ran ${succeeded} execution${succeeded !== 1 ? 's' : ''}`);
        } else {
          toast.warning(`Re-ran ${succeeded} of ${applicable.length}`, {
            description: `${failed} failed.`,
          });
        }
      } else {
        const ids = applicable.map((e) => e.id);
        const response: BatchExecutionResponse =
          action === 'cancel'
            ? await batchCancel.mutateAsync(ids)
            : action === 'pause'
              ? await batchPause.mutateAsync(ids)
              : await batchResume.mutateAsync(ids);
        buildBatchToast(label, response, skipped);
      }

      onClearSelection();
    } catch {
      toast.error(`Bulk ${label.toLowerCase()} failed`, {
        description: 'An unexpected error occurred. Please try again.',
      });
    } finally {
      setPendingAction(null);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div
      className={cn(
        // Positioning — fixed to bottom, centered
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
        // Visibility transition
        'transition-all duration-200 ease-out',
        hasSelection
          ? 'translate-y-0 opacity-100 pointer-events-auto'
          : 'translate-y-4 opacity-0 pointer-events-none'
      )}
      aria-hidden={!hasSelection}
    >
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl border border-border/60',
          'bg-background/95 backdrop-blur-sm shadow-xl px-4 py-2.5'
        )}
        role="toolbar"
        aria-label={`Bulk actions for ${selectedExecutions.length} selected execution${selectedExecutions.length !== 1 ? 's' : ''}`}
      >
        {/* Selection count */}
        <span className="text-sm font-medium text-foreground pr-2 border-r border-border/50 mr-1">
          <span aria-live="polite" aria-atomic="true">
            {selectedExecutions.length} selected
          </span>
        </span>

        {/* Action buttons */}
        {availableActions.map((action) => {
          const applicable = getApplicableExecutions(selectedExecutions, action);
          const count = applicable.length;
          const Icon = ACTION_ICONS[action];
          const label = getActionLabel(action);
          const isCurrentlyPending = pendingAction === action;
          const isAnyPending = pendingAction !== null;
          const colorClass = ACTION_LABEL_COLOR[action];

          return (
            <Button
              key={action}
              variant="ghost"
              size="sm"
              className={cn(
                'h-8 gap-1.5 text-sm font-medium px-2.5',
                colorClass,
                `hover:${colorClass}`,
                isCurrentlyPending && 'opacity-70'
              )}
              disabled={isAnyPending || count === 0}
              aria-label={`${label} ${count} selected execution${count !== 1 ? 's' : ''}`}
              onClick={() => handleBulkAction(action)}
            >
              {isCurrentlyPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              {label}
              <span className="text-xs opacity-70 font-mono">({count})</span>
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
          disabled={pendingAction !== null}
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
