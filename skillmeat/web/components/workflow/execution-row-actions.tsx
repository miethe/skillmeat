/**
 * ExecutionRowActions
 *
 * Per-row quick action buttons for the All Executions table. Renders small
 * icon buttons (cancel, pause, resume, re-run) based on the execution's
 * current status. Each button triggers the appropriate mutation hook.
 *
 * Re-run opens the RunWorkflowDialog with the execution's workflow pre-filled.
 * All other actions call the control mutation directly.
 *
 * Accessibility:
 * - Each button has an aria-label describing the action + execution ID.
 * - Tooltips provide hover-visible labels for icon-only buttons.
 * - Loading states disable the button and show a spinner.
 */

'use client';

import * as React from 'react';
import { XCircle, Pause, Play, RotateCcw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  usePauseExecution,
  useCancelExecution,
  useResumeExecution,
  useWorkflow,
} from '@/hooks';
import { RunWorkflowDialog } from '@/components/workflow/run-workflow-dialog';
import type { WorkflowExecution } from '@/types/workflow';
import {
  getAvailableActions,
  getActionLabel,
  getActionColorClass,
  type ExecutionAction,
} from '@/lib/workflow-action-utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExecutionRowActionsProps {
  execution: WorkflowExecution;
  /** Prevent click events from bubbling to the row click handler. */
  onActionStart?: () => void;
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
// RerunAction — lazily fetches the workflow only when needed
// ---------------------------------------------------------------------------

function RerunAction({ execution }: { execution: WorkflowExecution }) {
  const [dialogOpen, setDialogOpen] = React.useState(false);

  // Only fetch workflow definition when user opens the dialog
  const { data: workflow } = useWorkflow(dialogOpen ? execution.workflowId : '');

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              'h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity',
              getActionColorClass('rerun')
            )}
            aria-label={`Re-run execution ${execution.id.slice(0, 8)}`}
            onClick={(e) => {
              e.stopPropagation();
              setDialogOpen(true);
            }}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p className="text-xs">{getActionLabel('rerun')}</p>
        </TooltipContent>
      </Tooltip>

      <RunWorkflowDialog
        workflow={workflow ?? null}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// ActionButton — handles cancel, pause, resume mutations
// ---------------------------------------------------------------------------

type DirectAction = Exclude<ExecutionAction, 'rerun'>;

function DirectActionButton({
  action,
  execution,
}: {
  action: DirectAction;
  execution: WorkflowExecution;
}) {
  const cancel = useCancelExecution();
  const pause = usePauseExecution();
  const resume = useResumeExecution();

  const mutationMap: Record<DirectAction, { mutate: (id: string) => void; isPending: boolean }> = {
    cancel: { mutate: cancel.mutate, isPending: cancel.isPending },
    pause: { mutate: pause.mutate, isPending: pause.isPending },
    resume: { mutate: resume.mutate, isPending: resume.isPending },
  };

  const { mutate, isPending } = mutationMap[action];
  const Icon = ACTION_ICONS[action];
  const label = getActionLabel(action);
  const colorClass = getActionColorClass(action);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            'h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity',
            colorClass,
            isPending && 'opacity-50 cursor-not-allowed'
          )}
          aria-label={`${label} execution ${execution.id.slice(0, 8)}`}
          disabled={isPending}
          onClick={(e) => {
            e.stopPropagation();
            mutate(execution.id);
          }}
        >
          {isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top">
        <p className="text-xs">{label}</p>
      </TooltipContent>
    </Tooltip>
  );
}

// ---------------------------------------------------------------------------
// ExecutionRowActions — main export
// ---------------------------------------------------------------------------

/**
 * Renders the available quick action buttons for a single execution row.
 * Buttons are hidden until row hover (opacity-0 group-hover:opacity-100).
 */
export function ExecutionRowActions({ execution }: ExecutionRowActionsProps) {
  const actions = getAvailableActions(execution.status);

  if (actions.length === 0) return null;

  return (
    <TooltipProvider delayDuration={400}>
      <div
        className="flex items-center gap-0.5"
        role="group"
        aria-label={`Actions for execution ${execution.id.slice(0, 8)}`}
      >
        {actions.map((action) =>
          action === 'rerun' ? (
            <RerunAction key={action} execution={execution} />
          ) : (
            <DirectActionButton key={action} action={action} execution={execution} />
          )
        )}
      </div>
    </TooltipProvider>
  );
}
