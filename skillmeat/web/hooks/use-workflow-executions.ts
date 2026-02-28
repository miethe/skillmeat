/**
 * TanStack Query hooks for workflow execution operations.
 *
 * Covers listing, fetching, controlling (pause/resume/cancel), gate
 * approvals/rejections, and real-time SSE streaming of execution events.
 *
 * Stale time: 30 s (interactive/monitoring standard) for all execution queries.
 *
 * SSE hook behaviour:
 *   - Connects to GET /api/v1/workflow-executions/{id}/stream via EventSource.
 *   - Parses stage lifecycle events and updates local React state.
 *   - Auto-reconnects with exponential backoff (max 30 s interval).
 *   - Falls back to polling via useWorkflowExecution (30 s stale time) when
 *     the browser/environment does not support EventSource or when SSE
 *     repeatedly fails to connect.
 *   - Stream is closed and EventSource cleaned up on unmount or when
 *     `enabled` becomes false.
 */

'use client';

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import {
  fetchWorkflowExecutions,
  fetchWorkflowExecution,
  runWorkflow,
  pauseExecution,
  resumeExecution,
  cancelExecution,
  approveGate,
  rejectGate,
  batchPauseExecutions,
  batchResumeExecutions,
  batchCancelExecutions,
} from '@/lib/api/workflow-executions';
import type {
  WorkflowExecution,
  ExecutionFilters,
  RunWorkflowRequest,
  GateRejectRequest,
  ExecutionStatus,
  BatchExecutionResponse,
} from '@/types/workflow';
import { isTerminalExecutionStatus } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Stale / gc times
// ---------------------------------------------------------------------------

/** 30 s: interactive/monitoring standard for execution data. */
const EXECUTION_STALE_TIME = 30_000;
/** 5 min: keep in cache after unmount. */
const EXECUTION_GC_TIME = 300_000;

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

/**
 * Hierarchical query key factory for workflow execution queries.
 *
 * Shape:
 *   all:      ['workflow-executions']
 *   lists:    ['workflow-executions', 'list']
 *   filtered: ['workflow-executions', 'list', 'filtered', filters]
 *   details:  ['workflow-executions', 'detail']
 *   detail:   ['workflow-executions', 'detail', id]
 *   stream:   ['workflow-executions', 'stream', id]
 */
export const executionKeys = {
  all: ['workflow-executions'] as const,

  lists: () => [...executionKeys.all, 'list'] as const,

  filtered: (filters?: ExecutionFilters) =>
    [...executionKeys.lists(), 'filtered', filters] as const,

  details: () => [...executionKeys.all, 'detail'] as const,

  detail: (id: string) => [...executionKeys.details(), id] as const,

  stream: (id: string) => [...executionKeys.all, 'stream', id] as const,
};

// ---------------------------------------------------------------------------
// useWorkflowExecutions — list with optional filters
// ---------------------------------------------------------------------------

/**
 * Fetch a paginated, filterable list of workflow executions.
 *
 * @param filters - Optional ExecutionFilters (workflowId, status, skip, limit, …)
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useWorkflowExecutions({ status: 'running' });
 * ```
 */
export function useWorkflowExecutions(
  filters?: ExecutionFilters
): UseQueryResult<WorkflowExecution[], Error> {
  return useQuery({
    queryKey: executionKeys.filtered(filters),
    queryFn: () => fetchWorkflowExecutions(filters),
    staleTime: EXECUTION_STALE_TIME,
    gcTime: EXECUTION_GC_TIME,
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useWorkflowExecution — single execution detail
// ---------------------------------------------------------------------------

/**
 * Fetch a single workflow execution by ID, including all per-step state.
 *
 * @param id - Execution primary key (uuid hex). Pass empty string to disable.
 *
 * @example
 * ```tsx
 * const { data: execution } = useWorkflowExecution(executionId);
 * ```
 */
export function useWorkflowExecution(
  id: string
): UseQueryResult<WorkflowExecution, Error> {
  return useQuery({
    queryKey: executionKeys.detail(id),
    queryFn: () => fetchWorkflowExecution(id),
    staleTime: EXECUTION_STALE_TIME,
    gcTime: EXECUTION_GC_TIME,
    enabled: Boolean(id),
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useRunWorkflow — mutation: start a new execution
// ---------------------------------------------------------------------------

type RunWorkflowVariables = {
  workflowId: string;
} & Omit<RunWorkflowRequest, 'workflowId'>;

/**
 * Mutation to start a new workflow execution.
 *
 * On success, invalidates all execution list queries so they refetch with
 * the newly created execution.
 *
 * @example
 * ```tsx
 * const run = useRunWorkflow();
 *
 * const handleRun = () => {
 *   run.mutate({ workflowId: workflow.id, parameters: { env: 'prod' } });
 * };
 * ```
 */
export function useRunWorkflow(): UseMutationResult<
  WorkflowExecution,
  Error,
  RunWorkflowVariables
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workflowId, parameters, overrides }) =>
      runWorkflow(workflowId, { parameters, overrides }),
    onSuccess: () => {
      // Invalidate all list queries — the new execution should appear in every filter.
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
    onError: (error) => {
      console.error('[workflow-executions] Run failed:', error);
    },
  });
}

// ---------------------------------------------------------------------------
// Optimistic update context type
// ---------------------------------------------------------------------------

/** Rollback context returned from onMutate for error recovery. */
interface OptimisticRollbackContext {
  previous: WorkflowExecution | undefined;
  previousLists?: [readonly unknown[], unknown][];
}

// ---------------------------------------------------------------------------
// Cache update helper — applies a status patch to executions in list caches
// ---------------------------------------------------------------------------

/**
 * Update the status of specific executions in a list/filtered cache entry.
 * Handles both plain array and future paginated envelope shapes.
 */
function updateExecutionsInCache(
  cacheData: unknown,
  executionIds: Set<string>,
  newStatus: ExecutionStatus
): unknown {
  if (!cacheData) return cacheData;

  // Plain array (current backend shape)
  if (Array.isArray(cacheData)) {
    return cacheData.map((exec: WorkflowExecution) =>
      executionIds.has(exec.id) ? { ...exec, status: newStatus } : exec
    );
  }

  // Paginated envelope shape (future): { items: WorkflowExecution[], total, skip, limit }
  if (
    typeof cacheData === 'object' &&
    cacheData !== null &&
    'items' in cacheData &&
    Array.isArray((cacheData as { items: unknown }).items)
  ) {
    const envelope = cacheData as { items: WorkflowExecution[]; [key: string]: unknown };
    return {
      ...envelope,
      items: envelope.items.map((exec) =>
        executionIds.has(exec.id) ? { ...exec, status: newStatus } : exec
      ),
    };
  }

  return cacheData;
}

// ---------------------------------------------------------------------------
// usePauseExecution — mutation: pause a running execution
// ---------------------------------------------------------------------------

/**
 * Mutation to pause a running workflow execution.
 *
 * Applies an optimistic status update to `paused` immediately on mutate,
 * rolling back to the previous cached data on error. Invalidates both the
 * detail and list queries on settled to reconcile with server truth.
 *
 * @example
 * ```tsx
 * const pause = usePauseExecution();
 * pause.mutate(executionId);
 * ```
 */
export function usePauseExecution(): UseMutationResult<
  WorkflowExecution,
  Error,
  string,
  OptimisticRollbackContext
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: pauseExecution,
    onMutate: async (runId) => {
      // Cancel any in-flight refetches so they don't overwrite the optimistic update.
      await queryClient.cancelQueries({ queryKey: executionKeys.detail(runId) });
      await queryClient.cancelQueries({ queryKey: executionKeys.lists() });

      // Snapshot current cached data for rollback.
      const previous = queryClient.getQueryData<WorkflowExecution>(
        executionKeys.detail(runId)
      );
      const previousLists = queryClient.getQueriesData<unknown>({
        queryKey: executionKeys.lists(),
      }) as [readonly unknown[], unknown][];

      // Apply optimistic update to detail cache.
      queryClient.setQueryData<WorkflowExecution>(
        executionKeys.detail(runId),
        (old) => (old ? { ...old, status: 'paused' as ExecutionStatus } : old)
      );

      // Apply optimistic update to all list caches.
      const idSet = new Set([runId]);
      queryClient.setQueriesData(
        { queryKey: executionKeys.lists() },
        (old) => updateExecutionsInCache(old, idSet, 'paused')
      );

      return { previous, previousLists };
    },
    onError: (error, runId, context) => {
      // Roll back detail cache.
      if (context?.previous !== undefined) {
        queryClient.setQueryData(executionKeys.detail(runId), context.previous);
      }
      // Roll back list caches.
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          queryClient.setQueryData(key, data);
        }
      }
      console.error('[workflow-executions] Pause failed:', error);
      toast.error('Failed to pause execution', {
        description: error instanceof Error ? error.message : 'Please try again.',
        duration: 5000,
      });
    },
    onSettled: (_data, _error, runId) => {
      // Always reconcile with server truth after the mutation settles.
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useResumeExecution — mutation: resume a paused execution
// ---------------------------------------------------------------------------

/**
 * Mutation to resume a paused workflow execution.
 *
 * Applies an optimistic status update to `running` immediately on mutate,
 * rolling back to the previous cached data on error. Invalidates both the
 * detail and list queries on settled to reconcile with server truth.
 *
 * @example
 * ```tsx
 * const resume = useResumeExecution();
 * resume.mutate(executionId);
 * ```
 */
export function useResumeExecution(): UseMutationResult<
  WorkflowExecution,
  Error,
  string,
  OptimisticRollbackContext
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resumeExecution,
    onMutate: async (runId) => {
      // Cancel any in-flight refetches so they don't overwrite the optimistic update.
      await queryClient.cancelQueries({ queryKey: executionKeys.detail(runId) });
      await queryClient.cancelQueries({ queryKey: executionKeys.lists() });

      // Snapshot current cached data for rollback.
      const previous = queryClient.getQueryData<WorkflowExecution>(
        executionKeys.detail(runId)
      );
      const previousLists = queryClient.getQueriesData<unknown>({
        queryKey: executionKeys.lists(),
      }) as [readonly unknown[], unknown][];

      // Apply optimistic update to detail cache.
      queryClient.setQueryData<WorkflowExecution>(
        executionKeys.detail(runId),
        (old) => (old ? { ...old, status: 'running' as ExecutionStatus } : old)
      );

      // Apply optimistic update to all list caches.
      const idSet = new Set([runId]);
      queryClient.setQueriesData(
        { queryKey: executionKeys.lists() },
        (old) => updateExecutionsInCache(old, idSet, 'running')
      );

      return { previous, previousLists };
    },
    onError: (error, runId, context) => {
      // Roll back detail cache.
      if (context?.previous !== undefined) {
        queryClient.setQueryData(executionKeys.detail(runId), context.previous);
      }
      // Roll back list caches.
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          queryClient.setQueryData(key, data);
        }
      }
      console.error('[workflow-executions] Resume failed:', error);
      toast.error('Failed to resume execution', {
        description: error instanceof Error ? error.message : 'Please try again.',
        duration: 5000,
      });
    },
    onSettled: (_data, _error, runId) => {
      // Always reconcile with server truth after the mutation settles.
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useCancelExecution — mutation: cancel an execution
// ---------------------------------------------------------------------------

/**
 * Mutation to cancel a running or paused workflow execution.
 *
 * Applies an optimistic status update to `cancelled` immediately on mutate,
 * rolling back to the previous cached data on error. Invalidates both the
 * detail and list queries on settled to reconcile with server truth.
 *
 * @example
 * ```tsx
 * const cancel = useCancelExecution();
 * cancel.mutate(executionId);
 * ```
 */
export function useCancelExecution(): UseMutationResult<
  WorkflowExecution,
  Error,
  string,
  OptimisticRollbackContext
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelExecution,
    onMutate: async (runId) => {
      // Cancel any in-flight refetches so they don't overwrite the optimistic update.
      await queryClient.cancelQueries({ queryKey: executionKeys.detail(runId) });
      await queryClient.cancelQueries({ queryKey: executionKeys.lists() });

      // Snapshot current cached data for rollback.
      const previous = queryClient.getQueryData<WorkflowExecution>(
        executionKeys.detail(runId)
      );
      const previousLists = queryClient.getQueriesData<unknown>({
        queryKey: executionKeys.lists(),
      }) as [readonly unknown[], unknown][];

      // Apply optimistic update to detail cache.
      queryClient.setQueryData<WorkflowExecution>(
        executionKeys.detail(runId),
        (old) => (old ? { ...old, status: 'cancelled' as ExecutionStatus } : old)
      );

      // Apply optimistic update to all list caches.
      const idSet = new Set([runId]);
      queryClient.setQueriesData(
        { queryKey: executionKeys.lists() },
        (old) => updateExecutionsInCache(old, idSet, 'cancelled')
      );

      return { previous, previousLists };
    },
    onError: (error, runId, context) => {
      // Roll back detail cache.
      if (context?.previous !== undefined) {
        queryClient.setQueryData(executionKeys.detail(runId), context.previous);
      }
      // Roll back list caches.
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          queryClient.setQueryData(key, data);
        }
      }
      console.error('[workflow-executions] Cancel failed:', error);
      toast.error('Failed to cancel execution', {
        description: error instanceof Error ? error.message : 'Please try again.',
        duration: 5000,
      });
    },
    onSettled: (_data, _error, runId) => {
      // Always reconcile with server truth after the mutation settles.
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// Batch rollback context
// ---------------------------------------------------------------------------

/** Rollback context for batch mutations — only list caches are optimistically updated. */
interface BatchOptimisticRollbackContext {
  previousLists: [readonly unknown[], unknown][];
}

// ---------------------------------------------------------------------------
// useBatchPauseExecutions — mutation: pause multiple executions
// ---------------------------------------------------------------------------

/**
 * Mutation to pause multiple running workflow executions via a single batch API call.
 *
 * Optimistically updates all matching executions in the list cache to `paused`,
 * rolling back on error. Invalidates list queries on settled.
 *
 * @example
 * ```tsx
 * const batchPause = useBatchPauseExecutions();
 * batchPause.mutate(['id-1', 'id-2']);
 * ```
 */
export function useBatchPauseExecutions(): UseMutationResult<
  BatchExecutionResponse,
  Error,
  string[],
  BatchOptimisticRollbackContext
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: batchPauseExecutions,
    onMutate: async (executionIds) => {
      await queryClient.cancelQueries({ queryKey: executionKeys.lists() });

      const previousLists = queryClient.getQueriesData<unknown>({
        queryKey: executionKeys.lists(),
      }) as [readonly unknown[], unknown][];

      const idSet = new Set(executionIds);
      queryClient.setQueriesData(
        { queryKey: executionKeys.lists() },
        (old) => updateExecutionsInCache(old, idSet, 'paused')
      );

      return { previousLists };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          queryClient.setQueryData(key, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useBatchResumeExecutions — mutation: resume multiple executions
// ---------------------------------------------------------------------------

/**
 * Mutation to resume multiple paused workflow executions via a single batch API call.
 *
 * Optimistically updates all matching executions in the list cache to `running`,
 * rolling back on error. Invalidates list queries on settled.
 *
 * @example
 * ```tsx
 * const batchResume = useBatchResumeExecutions();
 * batchResume.mutate(['id-1', 'id-2']);
 * ```
 */
export function useBatchResumeExecutions(): UseMutationResult<
  BatchExecutionResponse,
  Error,
  string[],
  BatchOptimisticRollbackContext
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: batchResumeExecutions,
    onMutate: async (executionIds) => {
      await queryClient.cancelQueries({ queryKey: executionKeys.lists() });

      const previousLists = queryClient.getQueriesData<unknown>({
        queryKey: executionKeys.lists(),
      }) as [readonly unknown[], unknown][];

      const idSet = new Set(executionIds);
      queryClient.setQueriesData(
        { queryKey: executionKeys.lists() },
        (old) => updateExecutionsInCache(old, idSet, 'running')
      );

      return { previousLists };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          queryClient.setQueryData(key, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useBatchCancelExecutions — mutation: cancel multiple executions
// ---------------------------------------------------------------------------

/**
 * Mutation to cancel multiple running or paused workflow executions via a single batch API call.
 *
 * Optimistically updates all matching executions in the list cache to `cancelled`,
 * rolling back on error. Invalidates list queries on settled.
 *
 * @example
 * ```tsx
 * const batchCancel = useBatchCancelExecutions();
 * batchCancel.mutate(['id-1', 'id-2']);
 * ```
 */
export function useBatchCancelExecutions(): UseMutationResult<
  BatchExecutionResponse,
  Error,
  string[],
  BatchOptimisticRollbackContext
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: batchCancelExecutions,
    onMutate: async (executionIds) => {
      await queryClient.cancelQueries({ queryKey: executionKeys.lists() });

      const previousLists = queryClient.getQueriesData<unknown>({
        queryKey: executionKeys.lists(),
      }) as [readonly unknown[], unknown][];

      const idSet = new Set(executionIds);
      queryClient.setQueriesData(
        { queryKey: executionKeys.lists() },
        (old) => updateExecutionsInCache(old, idSet, 'cancelled')
      );

      return { previousLists };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousLists) {
        for (const [key, data] of context.previousLists) {
          queryClient.setQueryData(key, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useApproveGate — mutation: approve a gate step
// ---------------------------------------------------------------------------

type GateVariables = {
  executionId: string;
  stageId: string;
};

/**
 * Mutation to approve a pending gate stage.
 *
 * On success, invalidates the execution detail so stage state is refreshed.
 *
 * @example
 * ```tsx
 * const approve = useApproveGate();
 * approve.mutate({ executionId, stageId: 'review-gate' });
 * ```
 */
export function useApproveGate(): UseMutationResult<unknown, Error, GateVariables> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ executionId, stageId }) => approveGate(executionId, stageId),
    onSuccess: (_data, { executionId }) => {
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(executionId) });
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
    onError: (error) => {
      console.error('[workflow-executions] Gate approve failed:', error);
    },
  });
}

// ---------------------------------------------------------------------------
// useRejectGate — mutation: reject a gate step
// ---------------------------------------------------------------------------

type RejectGateVariables = GateVariables & {
  data?: GateRejectRequest;
};

/**
 * Mutation to reject a pending gate stage, with an optional reason.
 *
 * @example
 * ```tsx
 * const reject = useRejectGate();
 * reject.mutate({
 *   executionId,
 *   stageId: 'review-gate',
 *   data: { reason: 'Not ready for production' },
 * });
 * ```
 */
export function useRejectGate(): UseMutationResult<unknown, Error, RejectGateVariables> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ executionId, stageId, data }) => rejectGate(executionId, stageId, data),
    onSuccess: (_data, { executionId }) => {
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(executionId) });
      queryClient.invalidateQueries({ queryKey: executionKeys.lists() });
    },
    onError: (error) => {
      console.error('[workflow-executions] Gate reject failed:', error);
    },
  });
}

// ---------------------------------------------------------------------------
// SSE event types (subset of what the server emits)
// ---------------------------------------------------------------------------

/** Union of SSE event type strings emitted by the backend stream. */
type SseEventType =
  | 'stage_started'
  | 'stage_completed'
  | 'stage_failed'
  | 'stage_skipped'
  | 'log_line'
  | 'execution_completed';

/** Parsed SSE event received from the execution stream. */
export interface ExecutionSseEvent {
  type: SseEventType;
  data: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// useExecutionStream — SSE hook for real-time execution updates
// ---------------------------------------------------------------------------

/** Maximum exponential backoff interval in milliseconds (30 s). */
const SSE_MAX_BACKOFF_MS = 30_000;
/** Initial reconnect delay in milliseconds. */
const SSE_INITIAL_BACKOFF_MS = 1_000;
/** Number of consecutive SSE failures before falling back to polling. */
const SSE_FAILURE_THRESHOLD = 5;

export interface UseExecutionStreamResult {
  /** Latest parsed SSE event received from the stream. */
  lastEvent: ExecutionSseEvent | null;
  /** Log lines accumulated from 'log_line' events during this session. */
  logLines: string[];
  /** Whether the SSE connection is currently open. */
  isConnected: boolean;
  /** Whether the hook has fallen back to polling (no SSE support). */
  isPolling: boolean;
  /** The latest full execution snapshot (populated by polling fallback). */
  execution: WorkflowExecution | undefined;
  /** Last connection error, if any. */
  error: Error | null;
}

/**
 * Real-time execution monitoring via Server-Sent Events with polling fallback.
 *
 * Connects to GET /api/v1/workflow-executions/{executionId}/stream and
 * parses SSE events to track execution progress. Automatically reconnects
 * with exponential backoff when the connection drops. Closes the stream once
 * a terminal event is received (`execution_completed`) or when `enabled` is
 * set to false.
 *
 * Falls back to polling with `useWorkflowExecution` (30 s stale time) when
 * `EventSource` is unavailable (e.g. SSR environment or network proxy that
 * strips chunked transfer) or when SSE repeatedly fails to connect.
 *
 * @param executionId - Execution primary key to stream.
 * @param enabled     - Set to false to disable the stream (safe to toggle).
 *
 * @example
 * ```tsx
 * const {
 *   lastEvent,
 *   logLines,
 *   isConnected,
 *   isPolling,
 *   execution,
 * } = useExecutionStream(executionId, isDialogOpen);
 * ```
 */
export function useExecutionStream(
  executionId: string,
  enabled: boolean
): UseExecutionStreamResult {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
  const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

  // -------------------------------------------------------------------------
  // Feature detection: does this environment support EventSource?
  // -------------------------------------------------------------------------
  const sseSupported = typeof EventSource !== 'undefined';

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  const [lastEvent, setLastEvent] = useState<ExecutionSseEvent | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isPolling, setIsPolling] = useState(!sseSupported);
  const [error, setError] = useState<Error | null>(null);
  const [isTerminal, setIsTerminal] = useState(false);

  // -------------------------------------------------------------------------
  // Mutable refs — stable references used inside EventSource callbacks
  // to avoid stale closure problems without adding them to useCallback deps.
  // -------------------------------------------------------------------------
  const esRef = useRef<EventSource | null>(null);
  const backoffRef = useRef<number>(SSE_INITIAL_BACKOFF_MS);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const consecutiveFailuresRef = useRef<number>(0);
  // Stable ref to the connect function so it can call itself recursively.
  const connectRef = useRef<(() => void) | null>(null);

  // -------------------------------------------------------------------------
  // Polling fallback
  // -------------------------------------------------------------------------
  const shouldPoll = isPolling && enabled && !isTerminal && Boolean(executionId);

  const { data: polledExecution } = useWorkflowExecution(
    shouldPoll ? executionId : ''
  );

  // Detect terminal status from poll data.
  useEffect(() => {
    if (polledExecution && isTerminalExecutionStatus(polledExecution.status)) {
      setIsTerminal(true);
    }
  }, [polledExecution]);

  // -------------------------------------------------------------------------
  // SSE connect / disconnect logic
  // Defined as a plain function stored in a ref to allow self-reference in
  // the onerror handler without creating a circular useCallback dependency.
  // -------------------------------------------------------------------------
  useEffect(() => {
    connectRef.current = () => {
      if (!sseSupported || !enabled || !executionId || isTerminal) return;

      const streamUrl = `${API_BASE}/api/${API_VERSION}/workflow-executions/${executionId}/stream`;
      const es = new EventSource(streamUrl);
      esRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        setError(null);
        backoffRef.current = SSE_INITIAL_BACKOFF_MS;
        consecutiveFailuresRef.current = 0;
      };

      // Handler factory for each named SSE event type.
      const handleNamedEvent = (type: SseEventType) => (ev: MessageEvent) => {
        let data: Record<string, unknown> = {};
        try {
          data = JSON.parse(ev.data) as Record<string, unknown>;
        } catch {
          // Ignore malformed JSON; data stays as empty object.
        }

        setLastEvent({ type, data });

        // Accumulate log lines from the stream.
        if (type === 'log_line' && typeof data.message === 'string') {
          setLogLines((prev) => [...prev, data.message as string]);
        }

        // Close stream on terminal execution_completed event.
        if (type === 'execution_completed') {
          const terminalStatus = data.status as ExecutionStatus | undefined;
          if (terminalStatus && isTerminalExecutionStatus(terminalStatus)) {
            setIsTerminal(true);
            es.close();
            esRef.current = null;
            setIsConnected(false);
          }
        }
      };

      // Register a handler for every named event the backend emits.
      const eventTypes: SseEventType[] = [
        'stage_started',
        'stage_completed',
        'stage_failed',
        'stage_skipped',
        'log_line',
        'execution_completed',
      ];
      eventTypes.forEach((type) => {
        es.addEventListener(type, handleNamedEvent(type) as EventListener);
      });

      es.onerror = () => {
        setIsConnected(false);
        consecutiveFailuresRef.current += 1;

        // After SSE_FAILURE_THRESHOLD consecutive failures, give up and poll.
        if (consecutiveFailuresRef.current >= SSE_FAILURE_THRESHOLD) {
          console.warn(
            '[workflow-executions] SSE repeatedly failed — falling back to polling.'
          );
          setIsPolling(true);
          es.close();
          esRef.current = null;
          return;
        }

        // Exponential backoff before reconnecting.
        const delay = Math.min(backoffRef.current * 2, SSE_MAX_BACKOFF_MS);
        backoffRef.current = delay;
        setError(new Error('SSE connection lost; reconnecting…'));

        reconnectTimerRef.current = setTimeout(() => {
          if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
          }
          // Use the ref to call connect — avoids circular dep in useCallback.
          connectRef.current?.();
        }, delay);
      };
    };
  }); // No deps — intentionally runs every render to keep the closure fresh.

  // -------------------------------------------------------------------------
  // Effect: open SSE when enabled and not already polling or terminal.
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!enabled || !executionId || isPolling || isTerminal) return;

    connectRef.current?.();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      setIsConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, executionId, isPolling, isTerminal]);

  // -------------------------------------------------------------------------
  // Effect: reset local state when executionId changes (new execution).
  // -------------------------------------------------------------------------
  useEffect(() => {
    setLastEvent(null);
    setLogLines([]);
    setIsConnected(false);
    setIsPolling(!sseSupported);
    setError(null);
    setIsTerminal(false);
    backoffRef.current = SSE_INITIAL_BACKOFF_MS;
    consecutiveFailuresRef.current = 0;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executionId]);

  return {
    lastEvent,
    logLines,
    isConnected,
    isPolling,
    execution: polledExecution,
    error,
  };
}
