/**
 * Workflow API service functions
 *
 * Provides fetch wrapper functions for the workflow orchestration REST API.
 * All endpoints are under /api/v1/workflows.
 *
 * Note on casing: The backend returns snake_case field names from Python
 * dataclasses. These functions return the raw API response shape; consumers
 * (hooks) receive the snake_case payloads which are typed via WorkflowApiResponse
 * interfaces below. The canonical frontend types in types/workflow.ts use
 * camelCase — use mapWorkflowResponse() to convert.
 */

import type {
  Workflow,
  WorkflowListResponse,
  ValidationResult,
  ExecutionPlan,
  WorkflowFilters,
  CreateWorkflowRequest,
  UpdateWorkflowRequest,
  DuplicateWorkflowRequest,
  ValidateWorkflowRequest,
  PlanWorkflowRequest,
} from '@/types/workflow';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build a versioned API URL.
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Shared error extraction helper.
 * Reads the FastAPI `detail` field when available, falls back to statusText.
 */
async function extractError(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => ({}));
  return (body as { detail?: string }).detail || `${fallback}: ${response.statusText}`;
}

// ============================================================================
// Raw API response types (snake_case from backend dataclasses)
// ============================================================================

/**
 * Raw workflow object as returned by the backend (snake_case field names).
 * The backend converts WorkflowDTO via dataclasses.asdict(), so all nested
 * structures also use snake_case.
 */
export interface WorkflowApiResponse {
  id: string;
  uuid: string;
  name: string;
  description?: string;
  version: string;
  status: string;
  definition: string;
  tags: string[];
  stages: WorkflowStageApiResponse[];
  parameters: Record<string, unknown>;
  context_policy?: unknown;
  error_policy?: unknown;
  ui?: { color?: string; icon?: string };
  project_id?: string;
  created_at: string;
  updated_at: string;
}

/** Raw stage object nested within a WorkflowApiResponse. */
export interface WorkflowStageApiResponse {
  id: string;
  stage_id_ref: string;
  name: string;
  description?: string;
  order_index: number;
  stage_type: string;
  condition?: string;
  depends_on: string[];
  roles?: unknown;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  context?: unknown;
  error_policy?: unknown;
  handoff?: unknown;
  gate?: unknown;
  ui?: { position?: [number, number]; color?: string; icon?: string };
}

/** Raw validation result as returned by POST /workflows/{id}/validate. */
export interface ValidationResultApiResponse {
  is_valid: boolean;
  errors: Array<{
    category: string;
    message: string;
    stage_id?: string;
    field?: string;
  }>;
  warnings: Array<{
    category: string;
    message: string;
    stage_id?: string;
    field?: string;
  }>;
}

/** Raw execution plan as returned by POST /workflows/{id}/plan. */
export interface ExecutionPlanApiResponse {
  workflow_id: string;
  total_stages: number;
  total_batches: number;
  batches: Array<{
    batch_index: number;
    stages: Array<{
      stage_id: string;
      stage_name: string;
      stage_type: string;
      agent?: string;
      estimated_duration_seconds?: number;
    }>;
  }>;
  estimated_total_seconds?: number;
}

/** Raw paginated list response (backend returns a plain list for workflows). */
export type WorkflowListApiResponse = WorkflowApiResponse[];

// ============================================================================
// camelCase mappers
// ============================================================================

/**
 * Map a single raw backend workflow response to the camelCase Workflow type.
 */
export function mapWorkflowResponse(raw: WorkflowApiResponse): Workflow {
  return {
    id: raw.id,
    uuid: raw.uuid,
    name: raw.name,
    description: raw.description,
    version: raw.version,
    status: raw.status as Workflow['status'],
    definition: raw.definition,
    tags: raw.tags ?? [],
    stages: (raw.stages ?? []).map((s) => ({
      id: s.id,
      stageIdRef: s.stage_id_ref,
      name: s.name,
      description: s.description,
      orderIndex: s.order_index,
      stageType: s.stage_type as import('@/types/workflow').RawStageType,
      condition: s.condition,
      dependsOn: s.depends_on ?? [],
      roles: s.roles as import('@/types/workflow').StageRoles | undefined,
      inputs: (s.inputs ?? {}) as import('@/types/workflow').WorkflowStage['inputs'],
      outputs: (s.outputs ?? {}) as import('@/types/workflow').WorkflowStage['outputs'],
      context: s.context as import('@/types/workflow').ContextBinding | undefined,
      errorPolicy: s.error_policy as import('@/types/workflow').ErrorPolicy | undefined,
      handoff: s.handoff as import('@/types/workflow').HandoffConfig | undefined,
      gate: s.gate as import('@/types/workflow').GateConfig | undefined,
      ui: s.ui as import('@/types/workflow').StageUIMetadata | undefined,
    })),
    parameters: (raw.parameters ?? {}) as Workflow['parameters'],
    contextPolicy: raw.context_policy as Workflow['contextPolicy'],
    errorPolicy: raw.error_policy as Workflow['errorPolicy'],
    ui: raw.ui as Workflow['ui'],
    projectId: raw.project_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

/**
 * Map a raw validation result to the camelCase ValidationResult type.
 */
export function mapValidationResult(raw: ValidationResultApiResponse): ValidationResult {
  const mapIssue = (issue: ValidationResultApiResponse['errors'][number]) => ({
    category: issue.category as ValidationResult['errors'][number]['category'],
    message: issue.message,
    stageId: issue.stage_id,
    field: issue.field,
  });

  return {
    isValid: raw.is_valid,
    errors: (raw.errors ?? []).map(mapIssue),
    warnings: (raw.warnings ?? []).map(mapIssue),
  };
}

/**
 * Map a raw execution plan response to the camelCase ExecutionPlan type.
 */
export function mapExecutionPlan(raw: ExecutionPlanApiResponse): ExecutionPlan {
  return {
    workflowId: raw.workflow_id,
    totalStages: raw.total_stages,
    totalBatches: raw.total_batches,
    batches: (raw.batches ?? []).map((b) => ({
      batchIndex: b.batch_index,
      stages: (b.stages ?? []).map((s) => ({
        stageId: s.stage_id,
        stageName: s.stage_name,
        stageType: s.stage_type as import('@/types/workflow').RawStageType,
        agent: s.agent,
        estimatedDurationSeconds: s.estimated_duration_seconds,
      })),
    })),
    estimatedTotalSeconds: raw.estimated_total_seconds,
  };
}

// ============================================================================
// Request body serializers (camelCase → snake_case for the backend)
// ============================================================================

function serializeCreateRequest(data: CreateWorkflowRequest): Record<string, unknown> {
  return {
    yaml_content: data.yamlContent,
    ...(data.projectId !== undefined ? { project_id: data.projectId } : {}),
  };
}

function serializeUpdateRequest(data: UpdateWorkflowRequest): Record<string, unknown> {
  return {
    ...(data.yamlContent !== undefined ? { yaml_content: data.yamlContent } : {}),
    ...(data.projectId !== undefined ? { project_id: data.projectId } : {}),
  };
}

// ============================================================================
// API functions
// ============================================================================

/**
 * Fetch a paginated list of workflow definitions.
 *
 * GET /api/v1/workflows
 *
 * @param filters - Optional filter, sort, and pagination parameters
 * @returns List of mapped Workflow objects (backend returns a plain array)
 */
export async function fetchWorkflows(filters?: WorkflowFilters): Promise<WorkflowListResponse> {
  const params = new URLSearchParams();

  if (filters?.search) params.set('search', filters.search);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.tags && filters.tags.length > 0) params.set('tags', filters.tags.join(','));
  if (filters?.sortBy) params.set('sort_by', filters.sortBy);
  if (filters?.sortOrder) params.set('sort_order', filters.sortOrder);
  if (filters?.cursor) params.set('cursor', filters.cursor);
  if (filters?.limit !== undefined) params.set('limit', filters.limit.toString());
  if (filters?.skip !== undefined) params.set('skip', filters.skip.toString());

  const qs = params.toString();
  const url = buildUrl(`/workflows${qs ? `?${qs}` : ''}`);

  const response = await fetch(url);
  if (!response.ok) {
    const detail = await extractError(response, 'Failed to fetch workflows');
    throw new Error(detail);
  }

  // Backend returns a plain array (not a paginated envelope), so we wrap it
  const raw: WorkflowListApiResponse = await response.json();
  const items = raw.map(mapWorkflowResponse);
  const skip = filters?.skip ?? 0;
  const limit = filters?.limit ?? 50;

  return {
    items,
    total: items.length,
    skip,
    limit,
  };
}

/**
 * Fetch a single workflow definition by ID.
 *
 * GET /api/v1/workflows/{id}
 *
 * @param id - Workflow UUID hex string
 * @returns Mapped Workflow object
 */
export async function fetchWorkflow(id: string): Promise<Workflow> {
  const response = await fetch(buildUrl(`/workflows/${encodeURIComponent(id)}`));
  if (!response.ok) {
    const detail = await extractError(response, `Failed to fetch workflow ${id}`);
    throw new Error(detail);
  }
  const raw: WorkflowApiResponse = await response.json();
  return mapWorkflowResponse(raw);
}

/**
 * Create a new workflow definition from a YAML string.
 *
 * POST /api/v1/workflows
 *
 * @param data - Create request with yamlContent and optional projectId
 * @returns Newly created Workflow object (HTTP 201)
 */
export async function createWorkflow(data: CreateWorkflowRequest): Promise<Workflow> {
  const response = await fetch(buildUrl('/workflows'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(serializeCreateRequest(data)),
  });
  if (!response.ok) {
    const detail = await extractError(response, 'Failed to create workflow');
    throw new Error(detail);
  }
  const raw: WorkflowApiResponse = await response.json();
  return mapWorkflowResponse(raw);
}

/**
 * Replace an existing workflow's YAML definition atomically.
 *
 * PUT /api/v1/workflows/{id}
 *
 * @param id - Workflow UUID hex string
 * @param data - Update request with new yamlContent
 * @returns Updated Workflow object
 */
export async function updateWorkflow(id: string, data: UpdateWorkflowRequest): Promise<Workflow> {
  const response = await fetch(buildUrl(`/workflows/${encodeURIComponent(id)}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(serializeUpdateRequest(data)),
  });
  if (!response.ok) {
    const detail = await extractError(response, `Failed to update workflow ${id}`);
    throw new Error(detail);
  }
  const raw: WorkflowApiResponse = await response.json();
  return mapWorkflowResponse(raw);
}

/**
 * Delete a workflow and all its stages.
 *
 * DELETE /api/v1/workflows/{id}
 *
 * @param id - Workflow UUID hex string
 */
export async function deleteWorkflow(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/workflows/${encodeURIComponent(id)}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const detail = await extractError(response, `Failed to delete workflow ${id}`);
    throw new Error(detail);
  }
  // 204 No Content — no body to parse
}

/**
 * Duplicate an existing workflow as a new draft.
 *
 * POST /api/v1/workflows/{id}/duplicate
 *
 * @param id - Source workflow UUID hex string
 * @param data - Optional new name for the copy
 * @returns Newly created duplicate Workflow object (HTTP 201)
 */
export async function duplicateWorkflow(
  id: string,
  data?: DuplicateWorkflowRequest
): Promise<Workflow> {
  const response = await fetch(buildUrl(`/workflows/${encodeURIComponent(id)}/duplicate`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data?.newName !== undefined ? { new_name: data.newName } : {}),
  });
  if (!response.ok) {
    const detail = await extractError(response, `Failed to duplicate workflow ${id}`);
    throw new Error(detail);
  }
  const raw: WorkflowApiResponse = await response.json();
  return mapWorkflowResponse(raw);
}

/**
 * Run all static analysis passes against a persisted workflow.
 *
 * POST /api/v1/workflows/{id}/validate
 *
 * Always returns HTTP 200 — inspect ValidationResult.isValid to determine
 * whether the definition has blocking errors.
 *
 * @param id - Workflow UUID hex string
 * @param data - Optional parameter values for expression validation
 * @returns ValidationResult with errors and warnings
 */
export async function validateWorkflow(
  id: string,
  data?: ValidateWorkflowRequest
): Promise<ValidationResult> {
  const response = await fetch(buildUrl(`/workflows/${encodeURIComponent(id)}/validate`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data?.parameters !== undefined ? { parameters: data.parameters } : {}),
  });
  if (!response.ok) {
    const detail = await extractError(response, `Failed to validate workflow ${id}`);
    throw new Error(detail);
  }
  const raw: ValidationResultApiResponse = await response.json();
  return mapValidationResult(raw);
}

/**
 * Generate a static execution plan for a persisted workflow.
 *
 * POST /api/v1/workflows/{id}/plan
 *
 * Validates the workflow first — returns HTTP 422 if the definition has errors.
 *
 * @param id - Workflow UUID hex string
 * @param data - Optional parameter values merged with workflow defaults
 * @returns ExecutionPlan describing batches, stage order, and duration estimates
 */
export async function planWorkflow(
  id: string,
  data?: PlanWorkflowRequest
): Promise<ExecutionPlan> {
  const response = await fetch(buildUrl(`/workflows/${encodeURIComponent(id)}/plan`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data?.parameters !== undefined ? { parameters: data.parameters } : {}),
  });
  if (!response.ok) {
    const detail = await extractError(response, `Failed to generate execution plan for ${id}`);
    throw new Error(detail);
  }
  const raw: ExecutionPlanApiResponse = await response.json();
  return mapExecutionPlan(raw);
}
