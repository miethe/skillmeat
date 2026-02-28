'use client';

/**
 * Execution Dashboard Page
 *
 * Real-time dashboard for a single workflow execution run.
 * Shows header, progress bar, and a split layout with the stage timeline
 * on the left and detailed stage information + logs on the right.
 *
 * Layout:
 *   ┌──────────────────────────────────────────┐
 *   │ ExecutionHeader (sticky, full width)      │
 *   ├──────────────────────────────────────────┤
 *   │ ExecutionProgress (compact strip)         │
 *   ├──────────────┬───────────────────────────┤
 *   │ StageTimeline│ ExecutionDetail            │
 *   │  (w-72)      │  (flex-1)                 │
 *   │              │   └── LogViewer (children) │
 *   └──────────────┴───────────────────────────┘
 *
 * Mobile (<md): stacked — timeline above, detail below.
 *
 * Next.js 15: `params` is a Promise. Unwrapped via `use()` in this
 * client component per the App Router client-side pattern.
 *
 * SSE streaming (FE-6.7): `useExecutionStream` provides real-time log lines,
 * stage status events, and connection state. The stream is active when the
 * execution is in a non-terminal state. A subtle connection indicator appears
 * near the progress bar. Stage lifecycle events trigger query invalidation so
 * the timeline stays in sync with server state.
 */

import * as React from 'react';
import { use, useEffect, useRef } from 'react';
import { AlertTriangle, RefreshCw, Activity, WifiOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { ExecutionHeader } from '@/components/workflow/execution-header';
import { ExecutionProgress } from '@/components/workflow/execution-progress';
import { StageTimeline } from '@/components/workflow/stage-timeline';
import { ExecutionDetail } from '@/components/workflow/execution-detail';
import { LogViewer } from '@/components/workflow/log-viewer';
import type { LogLine } from '@/components/workflow/log-viewer';

import {
  useWorkflowExecution,
  usePauseExecution,
  useResumeExecution,
  useCancelExecution,
  useRunWorkflow,
  useApproveGate,
  useRejectGate,
  useExecutionStream,
  executionKeys,
} from '@/hooks';
import { useWorkflow } from '@/hooks';
import { useQueryClient } from '@tanstack/react-query';

import type { StageExecution } from '@/types/workflow';

// ============================================================================
// Page props
// ============================================================================

interface ExecutionDashboardPageProps {
  params: Promise<{ id: string; runId: string }>;
}

// ============================================================================
// Non-terminal execution statuses — stream is active for these
// ============================================================================

/**
 * Set of execution statuses where SSE streaming should be enabled.
 * Excludes 'pending' (no stages running yet, nothing to stream) and all
 * terminal statuses (completed, failed, cancelled).
 */
const STREAMING_STATUSES = new Set([
  'running',
  'paused',
  'waiting_for_approval',
] as const);

function isStreamingStatus(
  status: string | undefined
): boolean {
  if (!status) return false;
  return STREAMING_STATUSES.has(status as 'running' | 'paused' | 'waiting_for_approval');
}

// ============================================================================
// Connection indicator
// ============================================================================

interface ConnectionIndicatorProps {
  /** True when the SSE EventSource is currently connected. */
  isConnected: boolean;
  /** True when the stream should be active (execution is non-terminal). */
  shouldStream: boolean;
  /** True when the hook has fallen back to polling. */
  isPolling: boolean;
  /** Last SSE error, if any. */
  error: Error | null;
}

/**
 * Subtle real-time connection status indicator shown inline near the progress
 * bar. Renders nothing when streaming is not active.
 *
 * States:
 *   - Green pulse dot  → Connected and receiving events
 *   - Amber loader     → Connecting / reconnecting
 *   - Red wifi-off     → Connection error (with short message)
 *   - Hidden           → Not streaming (terminal execution)
 */
function ConnectionIndicator({
  isConnected,
  shouldStream,
  isPolling,
  error,
}: ConnectionIndicatorProps) {
  if (!shouldStream && !isPolling) return null;

  // Polling fallback — show a neutral indicator so users know updates are
  // still happening, just via polling rather than live SSE.
  if (isPolling) {
    return (
      <span
        className="flex items-center gap-1 text-[10px] text-muted-foreground/60 select-none"
        title="Real-time streaming unavailable — using polling"
        aria-label="Polling for updates"
      >
        <Loader2 className="h-2.5 w-2.5 animate-spin" aria-hidden="true" />
        <span className="hidden sm:inline">Polling</span>
      </span>
    );
  }

  if (isConnected) {
    return (
      <span
        className="flex items-center gap-1.5 text-[10px] text-emerald-500/80 select-none"
        title="Live — receiving real-time events"
        aria-label="Live streaming connected"
      >
        {/* Pulsing green dot */}
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
        </span>
        <span className="hidden sm:inline">Live</span>
      </span>
    );
  }

  // Reconnecting or errored
  if (error) {
    return (
      <span
        className="flex items-center gap-1 text-[10px] text-amber-500/80 select-none"
        title={error.message}
        aria-label="Reconnecting to live stream"
      >
        <WifiOff className="h-2.5 w-2.5" aria-hidden="true" />
        <span className="hidden sm:inline">Reconnecting</span>
      </span>
    );
  }

  // Connecting (no error yet, not connected)
  return (
    <span
      className="flex items-center gap-1 text-[10px] text-muted-foreground/50 select-none"
      title="Connecting to live stream..."
      aria-label="Connecting to live stream"
    >
      <Loader2 className="h-2.5 w-2.5 animate-spin" aria-hidden="true" />
      <span className="hidden sm:inline">Connecting</span>
    </span>
  );
}

// ============================================================================
// SSE error banner
// ============================================================================

interface SseErrorBannerProps {
  error: Error | null;
  shouldStream: boolean;
  isConnected: boolean;
}

/**
 * Non-intrusive warning banner rendered below the progress strip when the SSE
 * connection has dropped and auto-reconnect is in progress. Disappears once
 * the connection is restored or streaming is no longer needed.
 */
function SseErrorBanner({ error, shouldStream, isConnected }: SseErrorBannerProps) {
  if (!error || !shouldStream || isConnected) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center gap-2 border-b border-amber-500/20',
        'bg-amber-500/5 px-4 py-1.5 text-xs text-amber-600 dark:text-amber-400'
      )}
    >
      <WifiOff className="h-3 w-3 shrink-0" aria-hidden="true" />
      <span>
        Live stream interrupted — reconnecting automatically.
        Stage data may be delayed.
      </span>
    </div>
  );
}

// ============================================================================
// Loading skeleton
// ============================================================================

function ExecutionDashboardSkeleton() {
  return (
    <div className="flex h-full flex-col" aria-label="Loading execution dashboard">
      {/* Header skeleton */}
      <div className="flex items-center gap-3 border-b px-4 py-2.5">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-md" />
        <Skeleton className="h-5 w-16 rounded-full" />
        <div className="ml-auto flex gap-2">
          <Skeleton className="h-8 w-16 rounded-md" />
          <Skeleton className="h-8 w-16 rounded-md" />
        </div>
      </div>

      {/* Progress skeleton */}
      <div className="flex items-center gap-3 border-b px-4 py-2">
        <Skeleton className="h-1.5 flex-1 rounded-full" />
        <Skeleton className="h-4 w-32" />
      </div>

      {/* Main area skeleton */}
      <div className="flex flex-1 overflow-hidden">
        {/* Timeline skeleton */}
        <div className="hidden w-72 shrink-0 flex-col gap-4 border-r p-3 md:flex">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3">
              <Skeleton className="h-9 w-9 shrink-0 rounded-full" />
              <div className="flex-1 space-y-1.5 pt-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          ))}
        </div>

        {/* Detail skeleton */}
        <div className="flex-1 p-4 space-y-4">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
          </div>
          <Skeleton className="h-px w-full" />
          <div className="space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-8 w-full" />
          </div>
          <Skeleton className="h-px w-full" />
          <div className="space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Error state
// ============================================================================

function ExecutionDashboardError({
  error,
  onRetry,
}: {
  error: Error;
  onRetry: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
      <div
        role="alert"
        className="flex max-w-md flex-col items-center gap-3"
        aria-label="Failed to load execution"
      >
        <AlertTriangle
          className="h-10 w-10 text-destructive/60"
          aria-hidden="true"
        />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-foreground">
            Failed to load execution
          </p>
          <p className="text-xs text-muted-foreground">{error.message}</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={onRetry}
          className="gap-1.5"
          aria-label="Retry loading execution"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Page component
// ============================================================================

export default function ExecutionDashboardPage({
  params,
}: ExecutionDashboardPageProps) {
  // Unwrap async params using React.use() — required for client components in
  // Next.js 15 where dynamic route params are Promises.
  const { id, runId } = use(params);

  const queryClient = useQueryClient();

  // ── Data fetching ─────────────────────────────────────────────────────────

  const {
    data: execution,
    isLoading: executionLoading,
    error: executionError,
    refetch: refetchExecution,
  } = useWorkflowExecution(runId);

  const {
    data: workflow,
    isLoading: workflowLoading,
  } = useWorkflow(id);

  // ── SSE streaming ─────────────────────────────────────────────────────────
  //
  // shouldStream is true for non-terminal, non-pending statuses: running,
  // paused, waiting_for_approval. We do not stream for 'pending' because no
  // stages have started yet and the backend won't emit stage events.

  const shouldStream = isStreamingStatus(execution?.status);

  const {
    lastEvent,
    logLines: sseLogLines,
    isConnected,
    isPolling,
    error: sseError,
  } = useExecutionStream(runId, shouldStream);

  // ── Map SSE log lines to LogLine[] for LogViewer ──────────────────────────
  //
  // The SSE hook accumulates raw string lines from `log_line` events.
  // LogViewer expects `LogLine[]` with an optional `timestamp` and `level`.
  // We produce minimal `LogLine` objects from the raw strings — the component
  // will detect [ERROR]/[WARN] tokens in the message text automatically.

  const logLines: LogLine[] = React.useMemo(
    () => sseLogLines.map((message) => ({ message })),
    [sseLogLines]
  );

  // ── React to SSE events: invalidate queries + show toasts ─────────────────
  //
  // We track the previous lastEvent via a ref so the effect only fires when
  // the event object actually changes (referential equality check on the event).

  const prevLastEventRef = useRef<typeof lastEvent>(null);

  useEffect(() => {
    if (!lastEvent || lastEvent === prevLastEventRef.current) return;
    prevLastEventRef.current = lastEvent;

    const { type, data } = lastEvent;

    switch (type) {
      case 'stage_started': {
        // Invalidate to refresh stage state (status -> running, startedAt set)
        queryClient.invalidateQueries({
          queryKey: executionKeys.detail(runId),
        });
        break;
      }

      case 'stage_completed': {
        const stageName =
          typeof data.stage_name === 'string' ? data.stage_name : 'Stage';
        queryClient.invalidateQueries({
          queryKey: executionKeys.detail(runId),
        });
        toast.success(`${stageName} completed`, {
          description: 'Stage finished successfully.',
          duration: 3000,
        });
        break;
      }

      case 'stage_failed': {
        const stageName =
          typeof data.stage_name === 'string' ? data.stage_name : 'Stage';
        const errorMsg =
          typeof data.error === 'string' ? data.error : undefined;
        queryClient.invalidateQueries({
          queryKey: executionKeys.detail(runId),
        });
        toast.error(`${stageName} failed`, {
          description: errorMsg ?? 'The stage encountered an error.',
          duration: 5000,
        });
        break;
      }

      case 'stage_skipped': {
        queryClient.invalidateQueries({
          queryKey: executionKeys.detail(runId),
        });
        break;
      }

      case 'execution_completed': {
        const status = data.status;
        queryClient.invalidateQueries({
          queryKey: executionKeys.detail(runId),
        });
        queryClient.invalidateQueries({
          queryKey: executionKeys.lists(),
        });

        if (status === 'completed') {
          toast.success('Execution completed', {
            description: 'All stages finished successfully.',
            duration: 4000,
          });
        } else if (status === 'failed') {
          const errorMsg =
            typeof data.error === 'string' ? data.error : undefined;
          toast.error('Execution failed', {
            description: errorMsg ?? 'One or more stages encountered errors.',
            duration: 6000,
          });
        } else if (status === 'cancelled') {
          toast.info('Execution cancelled', {
            duration: 3000,
          });
        } else {
          // Other terminal statuses — do a final refetch to sync UI
          refetchExecution();
        }
        break;
      }

      default:
        break;
    }
  }, [lastEvent, runId, queryClient, refetchExecution]);

  // ── Mutations ─────────────────────────────────────────────────────────────

  const pauseExecution = usePauseExecution();
  const resumeExecution = useResumeExecution();
  const cancelExecution = useCancelExecution();
  const runWorkflow = useRunWorkflow();
  const approveGate = useApproveGate();
  const rejectGate = useRejectGate();

  // ── Selected stage state ──────────────────────────────────────────────────
  //
  // Initialized to the first running stage; falls back to the last stage once
  // all stages have reached a terminal state.

  const [selectedStageId, setSelectedStageId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!execution?.stages?.length) return;

    // Only auto-select if we have no selection yet (or current selection
    // is no longer valid after a data refresh).
    const stages = execution.stages;
    const currentStillValid = stages.some((s) => s.id === selectedStageId);
    if (currentStillValid) return;

    // Prefer the first running stage, then the last stage as fallback.
    const running = stages.find((s) => s.status === 'running');
    const target = running ?? stages[stages.length - 1];
    setSelectedStageId(target?.id ?? null);
  }, [execution?.stages, selectedStageId]);

  // ── Derived values ────────────────────────────────────────────────────────

  const stages: StageExecution[] = execution?.stages ?? [];

  const selectedStage: StageExecution | null =
    stages.find((s) => s.id === selectedStageId) ?? null;

  const workflowName = workflow?.name ?? 'Workflow';

  // ── Control button handlers ───────────────────────────────────────────────

  const handlePause = React.useCallback(() => {
    pauseExecution.mutate(runId);
  }, [pauseExecution, runId]);

  const handleResume = React.useCallback(() => {
    resumeExecution.mutate(runId);
  }, [resumeExecution, runId]);

  const handleCancel = React.useCallback(() => {
    cancelExecution.mutate(runId);
  }, [cancelExecution, runId]);

  const handleRerun = React.useCallback(() => {
    if (!execution) return;
    runWorkflow.mutate({
      workflowId: id,
      parameters: execution.parameters,
    });
  }, [runWorkflow, id, execution]);

  // ── Gate approval handlers ────────────────────────────────────────────────

  const handleApproveGate = React.useCallback(
    (stageId: string) => {
      approveGate.mutate({ executionId: runId, stageId });
    },
    [approveGate, runId]
  );

  const handleRejectGate = React.useCallback(
    (stageId: string, reason?: string) => {
      rejectGate.mutate({ executionId: runId, stageId, data: reason ? { reason } : undefined });
    },
    [rejectGate, runId]
  );

  // ── Loading state ─────────────────────────────────────────────────────────

  if (executionLoading || workflowLoading) {
    return <ExecutionDashboardSkeleton />;
  }

  // ── Error state ───────────────────────────────────────────────────────────

  if (executionError || !execution) {
    return (
      <ExecutionDashboardError
        error={executionError ?? new Error('Execution not found')}
        onRetry={() => refetchExecution()}
      />
    );
  }

  // ── No stages guard ───────────────────────────────────────────────────────

  if (stages.length === 0) {
    return (
      <div className="flex h-full flex-col">
        <ExecutionHeader
          execution={execution}
          workflowName={workflowName}
          workflowId={id}
          onPause={handlePause}
          onResume={handleResume}
          onCancel={handleCancel}
          onRerun={handleRerun}
        />
        <div className="flex flex-1 items-center justify-center gap-2 p-8 text-center">
          <Activity
            className="h-8 w-8 text-muted-foreground/30"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            No stages recorded for this execution yet.
          </p>
        </div>
      </div>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────

  // isStreaming for LogViewer: auto-scroll is active when the SSE connection
  // is open AND the execution status warrants streaming.
  const isLogStreaming = isConnected && shouldStream;

  return (
    /*
     * Outer wrapper: fills the available page height without causing the
     * browser to scroll the outer page when the inner panels overflow.
     * `overflow-hidden` here contains both inner scroll regions.
     */
    <div className="flex h-full min-h-0 flex-col">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <ExecutionHeader
        execution={execution}
        workflowName={workflowName}
        workflowId={id}
        onPause={handlePause}
        onResume={handleResume}
        onCancel={handleCancel}
        onRerun={handleRerun}
      />

      {/* ── Progress strip + connection indicator ───────────────────────── */}
      {/*
       * The connection indicator sits inline at the right end of the progress
       * strip. It is a sibling of ExecutionProgress rendered in a flex row so
       * neither component needs to know about the other's internals.
       */}
      <div className="relative flex items-center border-b">
        <ExecutionProgress
          stages={stages}
          executionStatus={execution.status}
          startedAt={execution.startedAt ?? null}
          className="flex-1"
        />

        {/* Connection indicator — inline, right-aligned within the strip */}
        <div className="flex shrink-0 items-center pr-3">
          <ConnectionIndicator
            isConnected={isConnected}
            shouldStream={shouldStream}
            isPolling={isPolling}
            error={sseError}
          />
        </div>
      </div>

      {/* ── SSE error banner ─────────────────────────────────────────────── */}
      <SseErrorBanner
        error={sseError}
        shouldStream={shouldStream}
        isConnected={isConnected}
      />

      {/* ── Main split layout ────────────────────────────────────────────── */}
      {/*
       * Desktop (md+): side-by-side flex row.
       *   Left:  StageTimeline — fixed width w-72, full height, internal scroll.
       *   Right: ExecutionDetail — flex-1, full height, internal scroll.
       *
       * Mobile (<md): stacked column.
       *   StageTimeline collapses to a capped-height scrollable strip at top.
       *   ExecutionDetail fills the remaining space below.
       */}
      <main
        className="flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row"
        aria-label="Execution detail"
      >
        {/* ── Stage Timeline (left panel / mobile top) ──────────────────── */}
        <aside
          className={[
            // Mobile: limited height with horizontal scroll fallback
            'max-h-48 overflow-hidden border-b md:max-h-none md:border-b-0',
            // Desktop: fixed width side panel with right border
            'md:w-72 md:shrink-0 md:border-r md:border-border',
            // Both: full height of the flex parent
            'md:h-full',
          ].join(' ')}
          aria-label="Stage timeline"
        >
          <StageTimeline
            stages={stages}
            selectedStageId={selectedStageId}
            onSelectStage={setSelectedStageId}
            className="h-full"
          />
        </aside>

        {/* ── Execution Detail (right panel / mobile bottom) ────────────── */}
        <section
          className="flex min-h-0 flex-1 flex-col overflow-hidden p-3"
          aria-label="Stage detail and logs"
        >
          <ExecutionDetail
            stage={selectedStage}
            onApproveGate={handleApproveGate}
            onRejectGate={handleRejectGate}
            className="h-full"
          >
            {/*
             * LogViewer slot — passed as children to ExecutionDetail.
             *
             * lines:       Mapped from SSE logLines (string[] -> LogLine[]).
             *              Empty until the first log_line event arrives.
             * isStreaming: True when connected and execution is live, enabling
             *              auto-scroll as new lines append.
             */}
            <LogViewer
              lines={logLines}
              isStreaming={isLogStreaming}
              maxHeight="16rem"
              showLineNumbers={true}
            />
          </ExecutionDetail>
        </section>
      </main>
    </div>
  );
}
