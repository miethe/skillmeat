/**
 * Workflow Execution API client functions
 *
 * Fetch wrappers for the workflow execution REST endpoints.
 * All paths confirmed against skillmeat/api/routers/workflow_executions.py.
 *
 * Endpoint summary:
 *   GET    /api/v1/workflow-executions                           → list
 *   POST   /api/v1/workflow-executions                          → start execution
 *   GET    /api/v1/workflow-executions/{id}                     → single detail
 *   GET    /api/v1/workflow-executions/{id}/stream              → SSE stream
 *   POST   /api/v1/workflow-executions/{id}/pause               → pause
 *   POST   /api/v1/workflow-executions/{id}/resume              → resume
 *   POST   /api/v1/workflow-executions/{id}/cancel              → cancel
 *   POST   /api/v1/workflow-executions/{id}/gates/{stageId}/approve → approve gate
 *   POST   /api/v1/workflow-executions/{id}/gates/{stageId}/reject  → reject gate
 */

import type {
  WorkflowExecution,
  StageExecution,
  ExecutionFilters,
  RunWorkflowRequest,
  GateRejectRequest,
  BatchExecutionResponse,
  ExecutionStatus,
} from '@/types/workflow';

// ---------------------------------------------------------------------------
// Field mappers (snake_case backend → camelCase frontend)
// ---------------------------------------------------------------------------

function computeDurationMs(startedAt?: string, completedAt?: string): number | undefined {
  if (!startedAt || !completedAt) return undefined;
  const diff = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  return diff >= 0 ? diff : undefined;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapStep(raw: Record<string, any>): StageExecution {
  const startedAt: string | undefined = raw.started_at ?? undefined;
  const completedAt: string | undefined = raw.completed_at ?? undefined;
  return {
    id: raw.id,
    stageId: raw.stage_id,
    stageName: raw.stage_name,
    stageType: raw.stage_type,
    batchIndex: raw.batch_index,
    status: raw.status,
    startedAt,
    completedAt,
    durationMs: computeDurationMs(startedAt, completedAt),
    errorMessage: raw.error_message ?? undefined,
    agentUsed: undefined,
    logs: [],
    outputs: {},
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapExecution(raw: Record<string, any>): WorkflowExecution {
  const startedAt: string | undefined = raw.started_at ?? undefined;
  const completedAt: string | undefined = raw.completed_at ?? undefined;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stages: StageExecution[] = (raw.steps ?? []).map((s: Record<string, any>) => mapStep(s));

  const runningIndex = stages.findIndex((s) => s.status === 'running');
  const completedCount = stages.filter((s) => s.status === 'completed').length;
  const progressPct = stages.length > 0 ? (completedCount / stages.length) * 100 : 0;

  return {
    id: raw.id,
    workflowId: raw.workflow_id,
    workflowName: undefined,
    status: raw.status,
    trigger: 'manual',
    parameters: raw.parameters ?? undefined,
    startedAt,
    completedAt,
    durationMs: computeDurationMs(startedAt, completedAt),
    stages,
    currentStageIndex: runningIndex,
    progressPct,
    errorMessage: raw.error_message ?? undefined,
  };
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

// ---------------------------------------------------------------------------
// Error helper
// ---------------------------------------------------------------------------

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body?.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

// ---------------------------------------------------------------------------
// List executions
// ---------------------------------------------------------------------------

/**
 * Fetch a paginated list of workflow executions.
 *
 * Maps ExecutionFilters to the query params accepted by
 * GET /api/v1/workflow-executions:
 *   - workflow_id (optional)
 *   - status     (optional)
 *   - skip       (default 0)
 *   - limit      (default 50)
 *
 * Note: The backend currently returns a plain array, not a paginated envelope.
 */
export async function fetchWorkflowExecutions(
  filters?: ExecutionFilters
): Promise<WorkflowExecution[]> {
  const params = new URLSearchParams();

  if (filters?.workflowId) params.set('workflow_id', filters.workflowId);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.skip != null) params.set('skip', String(filters.skip));
  if (filters?.limit != null) params.set('limit', String(filters.limit));

  const qs = params.toString();
  const url = buildUrl(`/workflow-executions${qs ? `?${qs}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to fetch workflow executions: ${msg}`);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: Record<string, any>[] = await response.json();
  return data.map(mapExecution);
}

// ---------------------------------------------------------------------------
// Single execution
// ---------------------------------------------------------------------------

/**
 * Fetch a single workflow execution by ID including all step records.
 *
 * GET /api/v1/workflow-executions/{id}
 */
export async function fetchWorkflowExecution(id: string): Promise<WorkflowExecution> {
  const response = await fetch(buildUrl(`/workflow-executions/${id}`));

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to fetch workflow execution ${id}: ${msg}`);
  }

  return mapExecution(await response.json());
}

// ---------------------------------------------------------------------------
// Start (run) execution
// ---------------------------------------------------------------------------

/**
 * Start a new workflow execution.
 *
 * POST /api/v1/workflow-executions
 *
 * The backend router accepts:
 *   { workflow_id, parameters?, overrides? }
 *
 * Our RunWorkflowRequest uses camelCase; we map to snake_case here.
 */
export async function runWorkflow(
  workflowId: string,
  data?: Omit<RunWorkflowRequest, 'workflowId'>
): Promise<WorkflowExecution> {
  const response = await fetch(buildUrl('/workflow-executions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      workflow_id: workflowId,
      parameters: data?.parameters ?? null,
      overrides: data?.overrides ?? null,
    }),
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to start workflow execution: ${msg}`);
  }

  return mapExecution(await response.json());
}

// ---------------------------------------------------------------------------
// Pause
// ---------------------------------------------------------------------------

/**
 * Pause a running workflow execution.
 *
 * POST /api/v1/workflow-executions/{id}/pause
 */
export async function pauseExecution(id: string): Promise<WorkflowExecution> {
  const response = await fetch(buildUrl(`/workflow-executions/${id}/pause`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to pause execution ${id}: ${msg}`);
  }

  return mapExecution(await response.json());
}

// ---------------------------------------------------------------------------
// Resume
// ---------------------------------------------------------------------------

/**
 * Resume a paused workflow execution.
 *
 * POST /api/v1/workflow-executions/{id}/resume
 */
export async function resumeExecution(id: string): Promise<WorkflowExecution> {
  const response = await fetch(buildUrl(`/workflow-executions/${id}/resume`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to resume execution ${id}: ${msg}`);
  }

  return mapExecution(await response.json());
}

// ---------------------------------------------------------------------------
// Cancel
// ---------------------------------------------------------------------------

/**
 * Cancel a running or paused workflow execution.
 *
 * POST /api/v1/workflow-executions/{id}/cancel
 */
export async function cancelExecution(id: string): Promise<WorkflowExecution> {
  const response = await fetch(buildUrl(`/workflow-executions/${id}/cancel`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to cancel execution ${id}: ${msg}`);
  }

  return mapExecution(await response.json());
}

// ---------------------------------------------------------------------------
// Gate: approve
// ---------------------------------------------------------------------------

/**
 * Approve a pending gate stage in a workflow execution.
 *
 * POST /api/v1/workflow-executions/{executionId}/gates/{stageId}/approve
 *
 * Note: the router uses the path segment "gates" (not "steps").
 */
export async function approveGate(executionId: string, stageId: string): Promise<unknown> {
  const response = await fetch(
    buildUrl(`/workflow-executions/${executionId}/gates/${stageId}/approve`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to approve gate ${stageId} on execution ${executionId}: ${msg}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Gate: reject
// ---------------------------------------------------------------------------

/**
 * Reject a pending gate stage in a workflow execution.
 *
 * POST /api/v1/workflow-executions/{executionId}/gates/{stageId}/reject
 *
 * An optional reason can be included in the request body.
 */
export async function rejectGate(
  executionId: string,
  stageId: string,
  data?: GateRejectRequest
): Promise<unknown> {
  const response = await fetch(
    buildUrl(`/workflow-executions/${executionId}/gates/${stageId}/reject`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data ?? {}),
    }
  );

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to reject gate ${stageId} on execution ${executionId}: ${msg}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Batch helpers
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapBatchResponse(raw: Record<string, any>): BatchExecutionResponse {
  return {
    results: (raw.results ?? []).map((r: Record<string, any>) => ({
      executionId: r.execution_id,
      success: r.success,
      status: r.status as ExecutionStatus | undefined,
      error: r.error ?? undefined,
    })),
    succeeded: raw.succeeded ?? 0,
    failed: raw.failed ?? 0,
  };
}

// ---------------------------------------------------------------------------
// Batch: pause
// ---------------------------------------------------------------------------

/**
 * Pause multiple running executions in a single request.
 *
 * POST /api/v1/workflow-executions/batch/pause
 */
export async function batchPauseExecutions(executionIds: string[]): Promise<BatchExecutionResponse> {
  const response = await fetch(buildUrl('/workflow-executions/batch/pause'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ execution_ids: executionIds }),
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to batch pause executions: ${msg}`);
  }

  return mapBatchResponse(await response.json());
}

// ---------------------------------------------------------------------------
// Batch: resume
// ---------------------------------------------------------------------------

/**
 * Resume multiple paused executions in a single request.
 *
 * POST /api/v1/workflow-executions/batch/resume
 */
export async function batchResumeExecutions(executionIds: string[]): Promise<BatchExecutionResponse> {
  const response = await fetch(buildUrl('/workflow-executions/batch/resume'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ execution_ids: executionIds }),
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to batch resume executions: ${msg}`);
  }

  return mapBatchResponse(await response.json());
}

// ---------------------------------------------------------------------------
// Batch: cancel
// ---------------------------------------------------------------------------

/**
 * Cancel multiple running or paused executions in a single request.
 *
 * POST /api/v1/workflow-executions/batch/cancel
 */
export async function batchCancelExecutions(executionIds: string[]): Promise<BatchExecutionResponse> {
  const response = await fetch(buildUrl('/workflow-executions/batch/cancel'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ execution_ids: executionIds }),
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to batch cancel executions: ${msg}`);
  }

  return mapBatchResponse(await response.json());
}
