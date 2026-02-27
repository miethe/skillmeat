/**
 * TanStack React Query hooks for workflow orchestration CRUD operations.
 *
 * Provides data fetching, caching, and mutation state management for
 * workflow definitions. Stale time follows the standard browsing cadence
 * (5 minutes) from the data-flow-patterns spec.
 *
 * Usage:
 *   import { workflowKeys, useWorkflows, useWorkflow, useCreateWorkflow } from '@/hooks';
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import {
  fetchWorkflows,
  fetchWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  duplicateWorkflow,
  validateWorkflow,
  planWorkflow,
} from '@/lib/api/workflows';

// ============================================================================
// Query key factory
// ============================================================================

/**
 * Stable query key factory for workflow-related queries.
 *
 * Key hierarchy:
 *   ['workflows']                          — root (invalidate all)
 *   ['workflows', 'list']                  — all list queries
 *   ['workflows', 'list', filters]         — specific filtered list
 *   ['workflows', 'detail']                — all detail queries
 *   ['workflows', 'detail', id]            — specific workflow detail
 *   ['workflows', 'validate', id]          — validation result for a workflow
 *   ['workflows', 'plan', id]              — execution plan for a workflow
 */
export const workflowKeys = {
  all: ['workflows'] as const,
  lists: () => [...workflowKeys.all, 'list'] as const,
  list: (filters?: WorkflowFilters) => [...workflowKeys.lists(), filters] as const,
  details: () => [...workflowKeys.all, 'detail'] as const,
  detail: (id: string) => [...workflowKeys.details(), id] as const,
  validations: () => [...workflowKeys.all, 'validate'] as const,
  validation: (id: string) => [...workflowKeys.validations(), id] as const,
  plans: () => [...workflowKeys.all, 'plan'] as const,
  plan: (id: string) => [...workflowKeys.plans(), id] as const,
};

// ============================================================================
// Query hooks
// ============================================================================

/**
 * Fetch a paginated, optionally filtered list of workflow definitions.
 *
 * Stale time: 5 minutes (standard browsing cadence).
 *
 * @param filters - Optional search, status, tags, sort, and pagination params
 * @returns Query result with WorkflowListResponse (items + pagination metadata)
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useWorkflows({ status: 'active', limit: 20 });
 * const workflows = data?.items ?? [];
 * ```
 */
export function useWorkflows(filters?: WorkflowFilters) {
  return useQuery<WorkflowListResponse>({
    queryKey: workflowKeys.list(filters),
    queryFn: () => fetchWorkflows(filters),
    staleTime: 5 * 60 * 1000, // 5 min — standard browsing stale time
  });
}

/**
 * Fetch a single workflow definition by its UUID.
 *
 * Query is disabled when id is falsy (empty string or undefined).
 * Stale time: 5 minutes (standard browsing cadence).
 *
 * @param id - Workflow UUID hex string
 * @returns Query result with full Workflow object including stages and parameters
 *
 * @example
 * ```tsx
 * const { data: workflow, isLoading } = useWorkflow(workflowId);
 * if (workflow) {
 *   console.log(workflow.stages.length, 'stages');
 * }
 * ```
 */
export function useWorkflow(id: string) {
  return useQuery<Workflow>({
    queryKey: workflowKeys.detail(id),
    queryFn: () => fetchWorkflow(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 min — standard browsing stale time
  });
}

// ============================================================================
// Mutation hooks
// ============================================================================

/**
 * Create a new workflow definition from a YAML string.
 *
 * On success invalidates all workflow list queries so any list views
 * refresh automatically.
 *
 * @returns Mutation with `mutateAsync(CreateWorkflowRequest) => Workflow`
 *
 * @example
 * ```tsx
 * const createWorkflow = useCreateWorkflow();
 * const workflow = await createWorkflow.mutateAsync({
 *   yamlContent: '...',
 *   projectId: 'proj-123',
 * });
 * ```
 */
export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<Workflow, Error, CreateWorkflowRequest>({
    mutationFn: (data) => createWorkflow(data),
    onSuccess: () => {
      // Invalidate all list queries — new workflow must appear in list views
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
  });
}

/**
 * Replace an existing workflow's YAML definition atomically.
 *
 * On success invalidates the specific detail query and all list queries
 * so any consumers reflecting this workflow's data refresh automatically.
 *
 * @returns Mutation with `mutateAsync({ id, data }) => Workflow`
 *
 * @example
 * ```tsx
 * const updateWorkflow = useUpdateWorkflow();
 * await updateWorkflow.mutateAsync({
 *   id: workflow.id,
 *   data: { yamlContent: updatedYaml },
 * });
 * ```
 */
export function useUpdateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<Workflow, Error, { id: string; data: UpdateWorkflowRequest }>({
    mutationFn: ({ id, data }) => updateWorkflow(id, data),
    onSuccess: (_, { id }) => {
      // Invalidate the specific workflow detail to force a fresh fetch
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(id) });
      // Invalidate all lists since the workflow's metadata may have changed
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      // Also invalidate any cached validation/plan results since definition changed
      queryClient.invalidateQueries({ queryKey: workflowKeys.validation(id) });
      queryClient.invalidateQueries({ queryKey: workflowKeys.plan(id) });
    },
  });
}

/**
 * Delete a workflow and all its associated stages.
 *
 * On success invalidates all workflow list queries. The deleted item will
 * disappear from list views on the next render cycle.
 *
 * @returns Mutation with `mutateAsync(id: string) => void`
 *
 * @example
 * ```tsx
 * const deleteWorkflow = useDeleteWorkflow();
 * await deleteWorkflow.mutateAsync(workflow.id);
 * ```
 */
export function useDeleteWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => deleteWorkflow(id),
    onSuccess: (_, id) => {
      // Remove the stale detail from cache immediately
      queryClient.removeQueries({ queryKey: workflowKeys.detail(id) });
      // Invalidate all list queries so the deleted item disappears
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
  });
}

/**
 * Duplicate an existing workflow as a new draft copy.
 *
 * The duplicate is created with status='draft' and receives a new UUID.
 * On success invalidates all workflow list queries so the copy appears.
 *
 * @returns Mutation with `mutateAsync({ id, data? }) => Workflow`
 *
 * @example
 * ```tsx
 * const duplicateWorkflow = useDuplicateWorkflow();
 * const copy = await duplicateWorkflow.mutateAsync({
 *   id: workflow.id,
 *   data: { newName: 'My Workflow (v2)' },
 * });
 * ```
 */
export function useDuplicateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<Workflow, Error, { id: string; data?: DuplicateWorkflowRequest }>({
    mutationFn: ({ id, data }) => duplicateWorkflow(id, data),
    onSuccess: () => {
      // Invalidate all list queries — the duplicate must appear in list views
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
  });
}

/**
 * Run all static validation passes against a persisted workflow definition.
 *
 * This is a mutation (not a query) because validation is a side-effectful
 * server operation and results are not meant to be cached long-term.
 * The backend always responds with HTTP 200 — inspect `result.isValid` to
 * determine whether the workflow definition has blocking errors.
 *
 * @returns Mutation with `mutateAsync({ id, data? }) => ValidationResult`
 *
 * @example
 * ```tsx
 * const validateWorkflow = useValidateWorkflow();
 * const result = await validateWorkflow.mutateAsync({ id: workflow.id });
 * if (!result.isValid) {
 *   console.error(result.errors);
 * }
 * ```
 */
export function useValidateWorkflow() {
  return useMutation<ValidationResult, Error, { id: string; data?: ValidateWorkflowRequest }>({
    mutationFn: ({ id, data }) => validateWorkflow(id, data),
    // No cache invalidation needed — validation is read-only
  });
}

/**
 * Generate a static execution plan preview for a persisted workflow.
 *
 * The backend validates the workflow first; a 422 error is thrown when the
 * definition has blocking validation errors.
 *
 * This is a mutation because plan generation is a compute-intensive server
 * operation triggered explicitly by the user, not background data fetching.
 *
 * @returns Mutation with `mutateAsync({ id, data? }) => ExecutionPlan`
 *
 * @example
 * ```tsx
 * const planWorkflow = usePlanWorkflow();
 * const plan = await planWorkflow.mutateAsync({
 *   id: workflow.id,
 *   data: { parameters: { feature_name: 'auth' } },
 * });
 * console.log(`${plan.totalBatches} parallel batches, ${plan.totalStages} stages`);
 * ```
 */
export function usePlanWorkflow() {
  return useMutation<ExecutionPlan, Error, { id: string; data?: PlanWorkflowRequest }>({
    mutationFn: ({ id, data }) => planWorkflow(id, data),
    // No cache invalidation needed — plan generation is read-only
  });
}
