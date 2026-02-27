/**
 * ExecutionHeader Component
 *
 * Sticky header bar for the workflow execution dashboard page.
 * Displays: workflow name (link), truncated run ID, relative started
 * timestamp, colour-coded status badge, and context-sensitive action
 * buttons (Pause / Resume / Cancel / Re-run).
 *
 * On narrow viewports the action buttons collapse into a dropdown menu.
 *
 * @example
 * ```tsx
 * <ExecutionHeader
 *   execution={execution}
 *   workflowName="Code Review Pipeline"
 *   workflowId="wf-abc123"
 *   onPause={handlePause}
 *   onResume={handleResume}
 *   onCancel={handleCancel}
 *   onRerun={handleRerun}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import Link from 'next/link';
import { Pause, Play, X, RotateCcw, MoreHorizontal, Clock, Hash } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import type { WorkflowExecution, ExecutionStatus } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface ExecutionHeaderProps {
  /** The full execution object from the API */
  execution: WorkflowExecution;
  /** Human-readable workflow display name */
  workflowName: string;
  /** Workflow ID used to build the back-link href */
  workflowId: string;
  /** Called when the user clicks Pause */
  onPause: () => void;
  /** Called when the user clicks Resume */
  onResume: () => void;
  /** Called when the user clicks Cancel */
  onCancel: () => void;
  /** Called when the user clicks Re-run */
  onRerun: () => void;
  /** Optional Tailwind class overrides for the outer element */
  className?: string;
}

// ============================================================================
// Constants — status badge styling
// ============================================================================

/**
 * Maps each ExecutionStatus to:
 *  - `label`   : human-readable display text
 *  - `variant` : shadcn Badge variant base
 *  - `extra`   : additional Tailwind classes for colour-coded look
 */
const STATUS_META: Record<
  ExecutionStatus,
  { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive'; extra: string }
> = {
  running: {
    label: 'Running',
    variant: 'default',
    extra:
      'bg-blue-500/15 text-blue-600 border-blue-500/30 dark:text-blue-400 dark:border-blue-500/40',
  },
  completed: {
    label: 'Completed',
    variant: 'default',
    extra:
      'bg-green-500/15 text-green-600 border-green-500/30 dark:text-green-400 dark:border-green-500/40',
  },
  failed: {
    label: 'Failed',
    variant: 'destructive',
    extra: 'bg-red-500/15 text-red-600 border-red-500/30 dark:text-red-400 dark:border-red-500/40',
  },
  paused: {
    label: 'Paused',
    variant: 'outline',
    extra:
      'bg-amber-500/15 text-amber-600 border-amber-500/30 dark:text-amber-400 dark:border-amber-500/40',
  },
  cancelled: {
    label: 'Cancelled',
    variant: 'outline',
    extra: 'text-muted-foreground border-border',
  },
  pending: {
    label: 'Pending',
    variant: 'secondary',
    extra: 'text-muted-foreground',
  },
  waiting_for_approval: {
    label: 'Awaiting Approval',
    variant: 'outline',
    extra:
      'bg-purple-500/15 text-purple-600 border-purple-500/30 dark:text-purple-400 dark:border-purple-500/40',
  },
};

// ============================================================================
// Helpers
// ============================================================================

/**
 * Returns a human-readable relative timestamp string for an ISO 8601 date.
 * Falls back to an em-dash when the timestamp is absent.
 */
function formatRelativeTime(iso: string | undefined): string {
  if (!iso) return '\u2014';
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffSeconds = Math.floor(diffMs / 1_000);
  const diffMin = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMin > 0) return `${diffMin}m ago`;
  if (diffSeconds > 10) return `${diffSeconds}s ago`;
  return 'just now';
}

/**
 * Truncates a run ID to the first 8 hex characters for compact display.
 * The full ID is preserved for the title attribute (tooltip).
 */
function truncateRunId(id: string): string {
  return id.replace(/-/g, '').slice(0, 8);
}

// ============================================================================
// Sub-components
// ============================================================================

/** Colour-coded status badge derived from ExecutionStatus */
function ExecutionStatusBadge({ status }: { status: ExecutionStatus }) {
  const meta = STATUS_META[status] ?? STATUS_META.pending;
  return (
    <Badge
      variant={meta.variant}
      className={cn('shrink-0 select-none tabular-nums', meta.extra)}
      aria-label={`Execution status: ${meta.label}`}
    >
      {/* Animated dot for live/in-progress states */}
      {(status === 'running' || status === 'pending') && (
        <span
          aria-hidden="true"
          className={cn(
            'mr-1.5 inline-block h-1.5 w-1.5 rounded-full',
            status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-muted-foreground/60'
          )}
        />
      )}
      {meta.label}
    </Badge>
  );
}

// ============================================================================
// Action button set
// ============================================================================

interface ActionConfig {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  variant: 'default' | 'outline' | 'ghost' | 'destructive';
  /** When true, renders with destructive text in the dropdown */
  destructive?: boolean;
}

/** Returns the relevant action configs for the given execution status */
function getActions(
  status: ExecutionStatus,
  callbacks: Pick<ExecutionHeaderProps, 'onPause' | 'onResume' | 'onCancel' | 'onRerun'>
): ActionConfig[] {
  const { onPause, onResume, onCancel, onRerun } = callbacks;

  switch (status) {
    case 'running':
      return [
        {
          label: 'Pause',
          icon: <Pause className="h-3.5 w-3.5" aria-hidden="true" />,
          onClick: onPause,
          variant: 'outline',
        },
        {
          label: 'Cancel',
          icon: <X className="h-3.5 w-3.5" aria-hidden="true" />,
          onClick: onCancel,
          variant: 'ghost',
          destructive: true,
        },
      ];

    case 'paused':
      return [
        {
          label: 'Resume',
          icon: <Play className="h-3.5 w-3.5" aria-hidden="true" />,
          onClick: onResume,
          variant: 'default',
        },
        {
          label: 'Cancel',
          icon: <X className="h-3.5 w-3.5" aria-hidden="true" />,
          onClick: onCancel,
          variant: 'ghost',
          destructive: true,
        },
      ];

    case 'completed':
    case 'failed':
    case 'cancelled':
      return [
        {
          label: 'Re-run',
          icon: <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />,
          onClick: onRerun,
          variant: 'outline',
        },
      ];

    // pending / waiting_for_approval / initializing fallthrough
    default:
      return [
        {
          label: 'Cancel',
          icon: <X className="h-3.5 w-3.5" aria-hidden="true" />,
          onClick: onCancel,
          variant: 'ghost',
          destructive: true,
        },
      ];
  }
}

/** Desktop: inline row of action buttons */
function DesktopActions({ actions }: { actions: ActionConfig[] }) {
  return (
    <div className="hidden sm:flex items-center gap-2" role="group" aria-label="Execution actions">
      {actions.map((action) => (
        <Button
          key={action.label}
          variant={action.variant}
          size="sm"
          onClick={action.onClick}
          aria-label={action.label}
          className={cn(
            'h-8 gap-1.5 text-sm',
            action.destructive &&
              'text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/30'
          )}
        >
          {action.icon}
          {action.label}
        </Button>
      ))}
    </div>
  );
}

/** Mobile: actions collapsed to a dropdown menu */
function MobileActions({ actions }: { actions: ActionConfig[] }) {
  return (
    <div className="sm:hidden" aria-label="Execution actions">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            aria-label="More execution actions"
          >
            <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[140px]">
          {actions.map((action, idx) => (
            <React.Fragment key={action.label}>
              {/* Separator before destructive actions when there are prior items */}
              {action.destructive && idx > 0 && <DropdownMenuSeparator />}
              <DropdownMenuItem
                onClick={action.onClick}
                className={cn(
                  'gap-2',
                  action.destructive && 'text-destructive focus:text-destructive'
                )}
              >
                {action.icon}
                {action.label}
              </DropdownMenuItem>
            </React.Fragment>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ============================================================================
// Main component
// ============================================================================

/**
 * ExecutionHeader — sticky control bar for the workflow execution dashboard.
 *
 * Layout (left to right):
 *   [Workflow name link] › [Run ID chip] · [Started time] [Status badge] | [Actions]
 *
 * Responsive:
 *   - Desktop (sm+): full inline action buttons
 *   - Mobile (<sm): actions collapse to a three-dot dropdown menu
 *
 * Accessibility:
 *   - Workflow name is an anchor with descriptive aria-label
 *   - Run ID chip has a title attribute (full ID on hover) and sr-only full text
 *   - Status badge carries aria-label
 *   - Action group uses role="group" with aria-label
 *   - Destructive actions are visually and semantically differentiated
 */
export function ExecutionHeader({
  execution,
  workflowName,
  workflowId,
  onPause,
  onResume,
  onCancel,
  onRerun,
  className,
}: ExecutionHeaderProps) {
  const actions = getActions(execution.status, { onPause, onResume, onCancel, onRerun });
  const shortId = truncateRunId(execution.id);
  const relativeTime = formatRelativeTime(execution.startedAt);

  return (
    <header
      className={cn(
        // Sticky below global app header
        'sticky top-0 z-10',
        // Surface — slight backdrop blur for depth; falls back gracefully
        'bg-background/95 backdrop-blur-sm',
        // Bottom border as a subtle divider
        'border-b border-border',
        // Layout: single horizontal band, vertically centred
        'flex min-w-0 items-center gap-3 px-4 py-2.5',
        className
      )}
      aria-label="Execution header"
    >
      {/* ── Left: identity section ───────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
        {/* Workflow name — links back to the workflow detail page */}
        <Link
          href={`/workflows/${workflowId}`}
          className={cn(
            'shrink-0 text-sm font-semibold leading-none tracking-tight',
            'text-foreground underline-offset-2 hover:underline',
            'truncate max-w-[20ch] sm:max-w-[30ch]',
            'transition-colors'
          )}
          aria-label={`Back to workflow: ${workflowName}`}
          title={workflowName}
        >
          {workflowName}
        </Link>

        {/* Chevron separator */}
        <span aria-hidden="true" className="shrink-0 text-muted-foreground/40 select-none">
          ›
        </span>

        {/* Run ID chip — monospace, truncated to 8 chars, full ID in title */}
        <span
          className={cn(
            'flex shrink-0 items-center gap-1',
            'rounded-md border border-border bg-muted/60 px-1.5 py-0.5',
            'font-mono text-[11px] text-muted-foreground',
            'select-all tabular-nums'
          )}
          title={execution.id}
          aria-label={`Run ID: ${execution.id}`}
        >
          <Hash className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
          {shortId}
          <span className="sr-only">{execution.id}</span>
        </span>

        {/* Metadata separator — hidden on very narrow screens */}
        <span
          aria-hidden="true"
          className="hidden shrink-0 text-muted-foreground/30 select-none xs:inline"
        >
          ·
        </span>

        {/* Started timestamp */}
        {execution.startedAt && (
          <time
            dateTime={execution.startedAt}
            className={cn(
              'hidden shrink-0 items-center gap-1 text-xs text-muted-foreground xs:flex'
            )}
            aria-label={`Started ${relativeTime}`}
          >
            <Clock className="h-3 w-3 shrink-0" aria-hidden="true" />
            {relativeTime}
          </time>
        )}

        {/* Status badge */}
        <ExecutionStatusBadge status={execution.status} />
      </div>

      {/* ── Right: action buttons ─────────────────────────────────────── */}
      {actions.length > 0 && (
        <>
          {/* Vertical rule separating identity from actions */}
          <div className="h-5 w-px shrink-0 bg-border" aria-hidden="true" />

          <DesktopActions actions={actions} />
          <MobileActions actions={actions} />
        </>
      )}
    </header>
  );
}
