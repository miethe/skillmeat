/**
 * Workflow Execution Action Utilities
 *
 * Status-to-action mapping and helpers for execution quick actions and
 * bulk action operations on the All Executions page.
 */

import type { ExecutionStatus, WorkflowExecution } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ExecutionAction = 'cancel' | 'pause' | 'resume' | 'rerun';

// ---------------------------------------------------------------------------
// Status → action mapping
// ---------------------------------------------------------------------------

/**
 * Maps each ExecutionStatus to the set of actions that can be taken on it.
 * Terminal statuses (completed, failed, cancelled) only allow re-run.
 * waiting_for_approval is a paused-like state that supports cancel only
 * (approval/rejection is handled via the gate action UI).
 */
export const EXECUTION_ACTION_MAP: Record<ExecutionStatus, ExecutionAction[]> = {
  pending: ['cancel'],
  running: ['cancel', 'pause'],
  paused: ['cancel', 'resume'],
  completed: ['rerun'],
  failed: ['rerun'],
  cancelled: ['rerun'],
  waiting_for_approval: ['cancel'],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Returns the actions available for a given execution status. */
export function getAvailableActions(status: ExecutionStatus): ExecutionAction[] {
  return EXECUTION_ACTION_MAP[status] ?? [];
}

/**
 * Returns the union of all actions applicable to any execution in the list.
 * Used to determine which buttons to render in the bulk action bar.
 */
export function getBulkActions(executions: WorkflowExecution[]): ExecutionAction[] {
  const actionSet = new Set<ExecutionAction>();
  for (const execution of executions) {
    for (const action of getAvailableActions(execution.status)) {
      actionSet.add(action);
    }
  }
  // Deterministic order: cancel, pause, resume, rerun
  const order: ExecutionAction[] = ['cancel', 'pause', 'resume', 'rerun'];
  return order.filter((a) => actionSet.has(a));
}

/**
 * Filters executions to only those where the given action is applicable.
 * Used to determine which items to act on in a bulk operation.
 */
export function getApplicableExecutions(
  executions: WorkflowExecution[],
  action: ExecutionAction
): WorkflowExecution[] {
  return executions.filter((e) => getAvailableActions(e.status).includes(action));
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

/** Human-readable label for an action. */
export function getActionLabel(action: ExecutionAction): string {
  switch (action) {
    case 'cancel':
      return 'Cancel';
    case 'pause':
      return 'Pause';
    case 'resume':
      return 'Resume';
    case 'rerun':
      return 'Re-run';
  }
}

/**
 * Returns the Lucide icon name (as a string key) for each action.
 * Consumers import the icon directly from lucide-react using this mapping.
 */
export function getActionIconName(
  action: ExecutionAction
): 'XCircle' | 'Pause' | 'Play' | 'RotateCcw' {
  switch (action) {
    case 'cancel':
      return 'XCircle';
    case 'pause':
      return 'Pause';
    case 'resume':
      return 'Play';
    case 'rerun':
      return 'RotateCcw';
  }
}

/**
 * Returns the Button variant appropriate for each action.
 * Cancel uses destructive; all others use ghost for row actions.
 */
export function getActionVariant(
  action: ExecutionAction
): 'ghost' | 'destructive' | 'outline' {
  if (action === 'cancel') return 'destructive';
  return 'ghost';
}

/**
 * Returns a Tailwind text-color class for the action icon in row buttons.
 * Cancel is styled destructive; others inherit foreground.
 */
export function getActionColorClass(action: ExecutionAction): string {
  switch (action) {
    case 'cancel':
      return 'text-destructive hover:text-destructive';
    case 'pause':
      return 'text-amber-500 hover:text-amber-400';
    case 'resume':
      return 'text-emerald-500 hover:text-emerald-400';
    case 'rerun':
      return 'text-blue-500 hover:text-blue-400';
  }
}
