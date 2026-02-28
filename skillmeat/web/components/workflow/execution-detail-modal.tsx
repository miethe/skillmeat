/**
 * ExecutionDetailModal Component
 *
 * Dialog-based summary view for a single workflow execution.
 * Intended as a lightweight preview that links out to the full
 * SSE-streaming dashboard page for real-time monitoring.
 *
 * Shows:
 *  - Execution identity (ID chip, status badge, workflow name link)
 *  - Progress strip (ExecutionProgress)
 *  - Stage summary list (name, status, duration)
 *  - Context-sensitive action buttons (Pause / Resume / Cancel / Rerun)
 *  - Prominent "Open Live Dashboard" link to the full execution page
 *  - Metadata footer (started at, total duration, trigger)
 *
 * @example
 * ```tsx
 * <ExecutionDetailModal
 *   executionId={selectedId}
 *   workflowId={workflowId}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onWorkflowClick={(id) => openWorkflowModal(id)}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Pause,
  Play,
  X,
  RotateCcw,
  ExternalLink,
  Hash,
  Clock,
  Zap,
  CheckCircle2,
  AlertCircle,
  Circle,
  Loader2,
  PauseCircle,
  Timer,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';

import { ExecutionProgress } from '@/components/workflow/execution-progress';

import {
  useWorkflowExecution,
  usePauseExecution,
  useResumeExecution,
  useCancelExecution,
  useRunWorkflow,
} from '@/hooks';

import type { StageExecution, ExecutionStatus } from '@/types/workflow';
import { EXECUTION_STATUS_META, isTerminalExecutionStatus } from '@/types/workflow';

// ============================================================================
// Props
// ============================================================================

export interface ExecutionDetailModalProps {
  /** Execution primary key — null means the modal is closed. */
  executionId: string | null;
  /** Parent workflow ID; used for API calls and "Open Live Dashboard" link. */
  workflowId: string;
  /** Controls dialog open state. */
  open: boolean;
  /** Called when the user dismisses the dialog. */
  onClose: () => void;
  /** Optional cross-link: called when the user clicks the workflow name. */
  onWorkflowClick?: (workflowId: string) => void;
}

// ============================================================================
// Constants — status badge styling (mirrors execution-header.tsx pattern)
// ============================================================================

const STATUS_BADGE_META: Record<
  ExecutionStatus,
  {
    label: string;
    variant: 'default' | 'secondary' | 'outline' | 'destructive';
    extra: string;
    dot?: string;
  }
> = {
  running: {
    label: 'Running',
    variant: 'default',
    extra:
      'bg-blue-500/15 text-blue-600 border-blue-500/30 dark:text-blue-400 dark:border-blue-500/40',
    dot: 'bg-blue-500 animate-pulse',
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
    extra:
      'bg-red-500/15 text-red-600 border-red-500/30 dark:text-red-400 dark:border-red-500/40',
  },
  paused: {
    label: 'Paused',
    variant: 'outline',
    extra:
      'bg-amber-500/15 text-amber-600 border-amber-500/30 dark:text-amber-400 dark:border-amber-500/40',
    dot: 'bg-amber-500',
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
    dot: 'bg-muted-foreground/60',
  },
  waiting_for_approval: {
    label: 'Awaiting Approval',
    variant: 'outline',
    extra:
      'bg-purple-500/15 text-purple-600 border-purple-500/30 dark:text-purple-400 dark:border-purple-500/40',
    dot: 'bg-purple-500 animate-pulse',
  },
};

// ============================================================================
// Helpers
// ============================================================================

/** Truncates a UUID to the first 8 hex chars for compact display. */
function truncateId(id: string): string {
  return id.replace(/-/g, '').slice(0, 8);
}

/** Formats an ISO 8601 timestamp as a human-readable local date/time string. */
function formatDateTime(iso: string | undefined): string {
  if (!iso) return '\u2014';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Formats elapsed milliseconds as "Xh Ym Zs". */
function formatDuration(ms: number | undefined): string {
  if (ms == null) return '\u2014';
  const totalSeconds = Math.floor(ms / 1_000);
  const hours = Math.floor(totalSeconds / 3_600);
  const minutes = Math.floor((totalSeconds % 3_600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  if (minutes > 0) return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  return `${seconds}s`;
}

/** Returns the icon component for a stage's execution status. */
function StageStatusIcon({ status }: { status: ExecutionStatus }) {
  switch (status) {
    case 'completed':
      return (
        <CheckCircle2
          className="h-3.5 w-3.5 shrink-0 text-green-500"
          aria-label="Completed"
        />
      );
    case 'failed':
      return (
        <AlertCircle
          className="h-3.5 w-3.5 shrink-0 text-destructive"
          aria-label="Failed"
        />
      );
    case 'running':
      return (
        <Loader2
          className="h-3.5 w-3.5 shrink-0 animate-spin text-blue-500"
          aria-label="Running"
        />
      );
    case 'paused':
      return (
        <PauseCircle
          className="h-3.5 w-3.5 shrink-0 text-amber-500"
          aria-label="Paused"
        />
      );
    case 'cancelled':
      return (
        <X
          className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
          aria-label="Cancelled"
        />
      );
    case 'waiting_for_approval':
      return (
        <PauseCircle
          className="h-3.5 w-3.5 shrink-0 text-purple-500"
          aria-label="Awaiting approval"
        />
      );
    default:
      return (
        <Circle
          className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40"
          aria-label="Pending"
        />
      );
  }
}

// ============================================================================
// Sub-components
// ============================================================================

/** Colour-coded status badge. */
function ExecutionStatusBadge({ status }: { status: ExecutionStatus }) {
  const meta = STATUS_BADGE_META[status] ?? STATUS_BADGE_META.pending;
  return (
    <Badge
      variant={meta.variant}
      className={cn('shrink-0 select-none', meta.extra)}
      aria-label={`Execution status: ${meta.label}`}
    >
      {meta.dot && (
        <span
          aria-hidden="true"
          className={cn('mr-1.5 inline-block h-1.5 w-1.5 rounded-full', meta.dot)}
        />
      )}
      {meta.label}
    </Badge>
  );
}

/** Single stage row in the summary list. */
function StageRow({ stage }: { stage: StageExecution }) {
  const statusLabel = EXECUTION_STATUS_META[stage.status]?.label ?? stage.status;
  const durationMs =
    stage.durationMs ??
    (stage.startedAt && stage.completedAt
      ? new Date(stage.completedAt).getTime() - new Date(stage.startedAt).getTime()
      : undefined);

  return (
    <li
      role="listitem"
      className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted/40"
    >
      <StageStatusIcon status={stage.status} />

      <span className="min-w-0 flex-1 truncate font-medium text-foreground">
        {stage.stageName}
      </span>

      <span
        className={cn(
          'shrink-0 text-xs',
          stage.status === 'completed'
            ? 'text-green-600 dark:text-green-400'
            : stage.status === 'failed'
              ? 'text-destructive'
              : stage.status === 'running'
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-muted-foreground'
        )}
        aria-label={`Status: ${statusLabel}`}
      >
        {statusLabel}
      </span>

      {durationMs != null && (
        <span
          className="flex shrink-0 items-center gap-1 text-xs tabular-nums text-muted-foreground"
          aria-label={`Duration: ${formatDuration(durationMs)}`}
        >
          <Timer className="h-2.5 w-2.5" aria-hidden="true" />
          {formatDuration(durationMs)}
        </span>
      )}
    </li>
  );
}

/** Loading skeleton shown while execution data is fetched. */
function ExecutionSkeleton() {
  return (
    <div className="space-y-4 p-6" aria-label="Loading execution details" aria-busy="true">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-5 w-48" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      </div>

      {/* Progress */}
      <Skeleton className="h-8 w-full rounded-md" />

      {/* Stage list */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-28" />
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-8 w-full rounded-md" />
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2">
        <Skeleton className="h-8 w-24 rounded-md" />
        <Skeleton className="h-8 w-24 rounded-md" />
      </div>
    </div>
  );
}

// ============================================================================
// Main component
// ============================================================================

export function ExecutionDetailModal({
  executionId,
  workflowId,
  open,
  onClose,
  onWorkflowClick,
}: ExecutionDetailModalProps) {
  // ── Data ──────────────────────────────────────────────────────────────────
  const { data: execution, isLoading } = useWorkflowExecution(executionId ?? '');

  // ── Mutations ─────────────────────────────────────────────────────────────
  const pauseMutation = usePauseExecution();
  const resumeMutation = useResumeExecution();
  const cancelMutation = useCancelExecution();
  const runMutation = useRunWorkflow();

  // ── Derived state ─────────────────────────────────────────────────────────
  const status = execution?.status;
  const isTerminal = status != null && isTerminalExecutionStatus(status);

  const isNonTerminal =
    status != null &&
    ['running', 'paused', 'pending', 'waiting_for_approval'].includes(status);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handlePause = React.useCallback(() => {
    if (executionId) pauseMutation.mutate(executionId);
  }, [executionId, pauseMutation]);

  const handleResume = React.useCallback(() => {
    if (executionId) resumeMutation.mutate(executionId);
  }, [executionId, resumeMutation]);

  const handleCancel = React.useCallback(() => {
    if (executionId) cancelMutation.mutate(executionId);
  }, [executionId, cancelMutation]);

  const handleRerun = React.useCallback(() => {
    runMutation.mutate({
      workflowId,
      parameters: execution?.parameters,
    });
  }, [workflowId, execution?.parameters, runMutation]);

  const handleWorkflowClick = React.useCallback(
    (e: React.MouseEvent) => {
      if (onWorkflowClick) {
        e.preventDefault();
        onWorkflowClick(workflowId);
      }
    },
    [onWorkflowClick, workflowId]
  );

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        className="max-w-2xl max-h-[80vh] flex flex-col gap-0 overflow-hidden p-0"
        aria-label="Execution detail"
      >
        {isLoading || !execution ? (
          <ExecutionSkeleton />
        ) : (
          <>
            {/* ── Header ─────────────────────────────────────────────── */}
            <DialogHeader className="flex-none border-b border-border px-6 py-4">
              {/* Row 1: run ID + status badge */}
              <div className="flex items-center gap-2.5">
                <span
                  className={cn(
                    'flex items-center gap-1 rounded-md border border-border',
                    'bg-muted/60 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground',
                    'select-all tabular-nums'
                  )}
                  title={execution.id}
                  aria-label={`Run ID: ${execution.id}`}
                >
                  <Hash className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
                  {truncateId(execution.id)}
                  <span className="sr-only">{execution.id}</span>
                </span>

                <ExecutionStatusBadge status={execution.status} />
              </div>

              {/* Row 2: workflow name */}
              <DialogTitle asChild>
                <h2 className="mt-1.5 text-base font-semibold leading-snug text-foreground">
                  {onWorkflowClick ? (
                    <button
                      type="button"
                      onClick={handleWorkflowClick}
                      className={cn(
                        'cursor-pointer underline-offset-2 hover:underline',
                        'text-foreground transition-colors'
                      )}
                      aria-label={`View workflow: ${execution.workflowName ?? workflowId}`}
                    >
                      {execution.workflowName ?? workflowId}
                    </button>
                  ) : (
                    <Link
                      href={`/workflows/${workflowId}`}
                      className="underline-offset-2 hover:underline"
                      aria-label={`View workflow: ${execution.workflowName ?? workflowId}`}
                    >
                      {execution.workflowName ?? workflowId}
                    </Link>
                  )}
                </h2>
              </DialogTitle>
            </DialogHeader>

            {/* ── Scrollable body ────────────────────────────────────── */}
            <ScrollArea className="flex-1 min-h-0">
              <div className="space-y-0">
                {/* Progress strip */}
                <ExecutionProgress
                  stages={execution.stages}
                  executionStatus={execution.status}
                  startedAt={execution.startedAt ?? null}
                />

                {/* Stage summary list */}
                <section
                  aria-label="Stage summary"
                  className="px-6 py-4"
                >
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Stages
                  </h3>

                  {execution.stages.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No stages recorded.</p>
                  ) : (
                    <ul role="list" className="space-y-0.5">
                      {execution.stages.map((stage) => (
                        <StageRow key={stage.id} stage={stage} />
                      ))}
                    </ul>
                  )}
                </section>

                <Separator />

                {/* Action buttons */}
                <section
                  aria-label="Execution actions"
                  className="px-6 py-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Non-terminal: show control actions */}
                    {isNonTerminal && (
                      <>
                        {(status === 'running' || status === 'pending') && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handlePause}
                            disabled={pauseMutation.isPending}
                            aria-label="Pause execution"
                            className="gap-1.5"
                          >
                            <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                            Pause
                          </Button>
                        )}

                        {status === 'paused' && (
                          <Button
                            variant="default"
                            size="sm"
                            onClick={handleResume}
                            disabled={resumeMutation.isPending}
                            aria-label="Resume execution"
                            className="gap-1.5"
                          >
                            <Play className="h-3.5 w-3.5" aria-hidden="true" />
                            Resume
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleCancel}
                          disabled={cancelMutation.isPending}
                          aria-label="Cancel execution"
                          className={cn(
                            'gap-1.5 text-destructive',
                            'hover:text-destructive hover:bg-destructive/10 border-destructive/30'
                          )}
                        >
                          <X className="h-3.5 w-3.5" aria-hidden="true" />
                          Cancel
                        </Button>
                      </>
                    )}

                    {/* Terminal: show rerun */}
                    {isTerminal && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRerun}
                        disabled={runMutation.isPending}
                        aria-label="Rerun this workflow"
                        className="gap-1.5"
                      >
                        <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                        Rerun
                      </Button>
                    )}

                    {/* Spacer pushes the "Open Live Dashboard" button to the right */}
                    <div className="flex-1" aria-hidden="true" />

                    {/* Open Live Dashboard — prominent primary link */}
                    <Button
                      asChild
                      size="sm"
                      className="gap-1.5 font-medium"
                      aria-label="Open the full live execution dashboard"
                    >
                      <Link
                        href={`/workflows/${workflowId}/executions/${executionId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                        Open Live Dashboard
                      </Link>
                    </Button>
                  </div>
                </section>

                <Separator />

                {/* Metadata footer */}
                <footer
                  className="grid grid-cols-3 gap-4 px-6 py-4"
                  aria-label="Execution metadata"
                >
                  <div className="space-y-0.5">
                    <dt className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      Started
                    </dt>
                    <dd className="text-sm tabular-nums text-foreground">
                      {formatDateTime(execution.startedAt)}
                    </dd>
                  </div>

                  <div className="space-y-0.5">
                    <dt className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      <Timer className="h-3 w-3" aria-hidden="true" />
                      Duration
                    </dt>
                    <dd className="text-sm tabular-nums text-foreground">
                      {formatDuration(execution.durationMs)}
                    </dd>
                  </div>

                  <div className="space-y-0.5">
                    <dt className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      <Zap className="h-3 w-3" aria-hidden="true" />
                      Triggered by
                    </dt>
                    <dd className="text-sm capitalize text-foreground">
                      {execution.trigger}
                    </dd>
                  </div>
                </footer>
              </div>
            </ScrollArea>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
