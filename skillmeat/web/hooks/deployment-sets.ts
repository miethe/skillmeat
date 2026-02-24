/**
 * React Query hooks for Deployment Sets
 *
 * Covers all 11 API endpoints under /api/v1/deployment-sets.
 *
 * Stale times:
 *   - List/detail queries: 5 minutes (standard browsing)
 *   - Resolve query: 30 seconds (interactive/monitoring — content changes on member edits)
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  DeploymentSet,
  DeploymentSetCreate,
  DeploymentSetUpdate,
  DeploymentSetListResponse,
  DeploymentSetListParams,
  DeploymentSetMember,
  DeploymentSetMemberCreate,
  DeploymentSetResolution,
  BatchDeployRequest,
  BatchDeployResponse,
} from '@/types/deployment-sets';
import {
  fetchDeploymentSets,
  fetchDeploymentSet,
  fetchDeploymentSetMembers,
  createDeploymentSet,
  updateDeploymentSet,
  deleteDeploymentSet,
  cloneDeploymentSet,
  addDeploymentSetMember,
  removeDeploymentSetMember,
  updateDeploymentSetMemberPosition,
  resolveDeploymentSet,
  batchDeployDeploymentSet,
  batchDeploySetByProjectId,
} from '@/lib/api/deployment-sets';

// =============================================================================
// Query Key Factory
// =============================================================================

export const deploymentSetKeys = {
  all: ['deployment-sets'] as const,
  lists: () => [...deploymentSetKeys.all, 'list'] as const,
  list: (params?: DeploymentSetListParams) => [...deploymentSetKeys.lists(), params] as const,
  details: () => [...deploymentSetKeys.all, 'detail'] as const,
  detail: (id: string) => [...deploymentSetKeys.details(), id] as const,
  members: (id: string) => [...deploymentSetKeys.all, 'members', id] as const,
  resolves: () => [...deploymentSetKeys.all, 'resolve'] as const,
  resolve: (id: string) => [...deploymentSetKeys.resolves(), id] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * List deployment sets with optional filtering and pagination.
 *
 * @param params - Optional filters: name substring, tag, limit, offset
 */
export function useDeploymentSets(params?: DeploymentSetListParams) {
  return useQuery<DeploymentSetListResponse, Error>({
    queryKey: deploymentSetKeys.list(params),
    queryFn: () => fetchDeploymentSets(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch a single deployment set by ID.
 *
 * @param id - Deployment set UUID hex
 */
export function useDeploymentSet(id: string) {
  return useQuery<DeploymentSet, Error>({
    queryKey: deploymentSetKeys.detail(id),
    queryFn: () => fetchDeploymentSet(id),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!id,
  });
}

/**
 * List all members of a deployment set, ordered by position.
 *
 * Uses a 5-minute stale time (same as detail — member list is stable between
 * add/remove mutations which invalidate this query key).
 *
 * @param id - Deployment set UUID hex
 */
export function useDeploymentSetMembers(id: string) {
  return useQuery<DeploymentSetMember[], Error>({
    queryKey: deploymentSetKeys.members(id),
    queryFn: () => fetchDeploymentSetMembers(id),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!id,
  });
}

/**
 * Recursively resolve a deployment set to its flat, deduplicated artifact list.
 *
 * Uses a 30-second stale time because resolution results change immediately
 * after member add/remove mutations.
 *
 * @param id - Deployment set UUID hex
 */
export function useResolveSet(id: string) {
  return useQuery<DeploymentSetResolution, Error>({
    queryKey: deploymentSetKeys.resolve(id),
    queryFn: () => resolveDeploymentSet(id),
    staleTime: 30 * 1000, // 30 seconds — interactive freshness
    enabled: !!id,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Create a new deployment set.
 *
 * Invalidates all deployment set list queries on success.
 */
export function useCreateDeploymentSet() {
  const queryClient = useQueryClient();

  return useMutation<DeploymentSet, Error, DeploymentSetCreate>({
    mutationFn: (data) => createDeploymentSet(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.lists() });
    },
  });
}

/**
 * Update an existing deployment set (partial update).
 *
 * Invalidates the specific detail query and all list queries on success.
 */
export function useUpdateDeploymentSet() {
  const queryClient = useQueryClient();

  return useMutation<DeploymentSet, Error, { id: string; data: DeploymentSetUpdate }>({
    mutationFn: ({ id, data }) => updateDeploymentSet(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.lists() });
    },
  });
}

/**
 * Delete a deployment set.
 *
 * Cascade-deletes all member rows on the backend.
 * Invalidates the specific detail query and all list queries on success.
 */
export function useDeleteDeploymentSet() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => deleteDeploymentSet(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.lists() });
    },
  });
}

/**
 * Clone a deployment set and all its members.
 *
 * The clone receives a name of "<original name> (copy)".
 * Invalidates all list queries on success.
 */
export function useCloneDeploymentSet() {
  const queryClient = useQueryClient();

  return useMutation<DeploymentSet, Error, string>({
    mutationFn: (id) => cloneDeploymentSet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.lists() });
    },
  });
}

/**
 * Add an artifact, group, or nested deployment set as a member.
 *
 * Exactly one of artifact_uuid, group_id, or nested_set_id must be set
 * in the payload (validated on the backend). Adding a nested set member
 * triggers circular-reference detection on the backend.
 *
 * Invalidates:
 *   - The parent set's detail query
 *   - The parent set's resolve query (resolution changes after member add)
 *   - All list queries (member_count changes)
 */
export function useAddMember() {
  const queryClient = useQueryClient();

  return useMutation<
    DeploymentSetMember,
    Error,
    { setId: string; data: DeploymentSetMemberCreate }
  >({
    mutationFn: ({ setId, data }) => addDeploymentSetMember(setId, data),
    onSuccess: (_, { setId }) => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.detail(setId) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.members(setId) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.resolve(setId) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.lists() });
    },
  });
}

/**
 * Remove a member from a deployment set.
 *
 * Invalidates:
 *   - The parent set's detail query
 *   - The parent set's resolve query (resolution changes after member remove)
 *   - All list queries (member_count changes)
 */
export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { setId: string; memberId: string }>({
    mutationFn: ({ setId, memberId }) => removeDeploymentSetMember(setId, memberId),
    onSuccess: (_, { setId }) => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.detail(setId) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.members(setId) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.resolve(setId) });
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.lists() });
    },
  });
}

/**
 * Update the ordering position of a member within a deployment set.
 *
 * Invalidates the parent set's detail query on success.
 */
export function useUpdateMemberPosition() {
  const queryClient = useQueryClient();

  return useMutation<
    DeploymentSetMember,
    Error,
    { setId: string; memberId: string; position: number }
  >({
    mutationFn: ({ setId, memberId, position }) =>
      updateDeploymentSetMemberPosition(setId, memberId, { position }),
    onSuccess: (_, { setId }) => {
      queryClient.invalidateQueries({ queryKey: deploymentSetKeys.detail(setId) });
    },
  });
}

/**
 * Batch-deploy all artifacts in a deployment set to a target project (by path).
 *
 * Per-artifact errors are captured and returned in results — a single failure
 * does not abort the entire batch.
 *
 * Invalidates all deployment-related queries on success.
 */
export function useBatchDeploy() {
  const queryClient = useQueryClient();

  return useMutation<BatchDeployResponse, Error, { id: string; data: BatchDeployRequest }>({
    mutationFn: ({ id, data }) => batchDeployDeploymentSet(id, data),
    onSuccess: () => {
      // Invalidate deployment queries so deployed artifact status refreshes
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
    },
  });
}

/**
 * Batch-deploy all artifacts in a deployment set to a target project (by project ID).
 *
 * Variant of useBatchDeploy that accepts a database project ID and an optional
 * deployment profile ID instead of a filesystem project path. Use this when the
 * caller has a project record from the DB rather than a raw filesystem path.
 *
 * Per-artifact errors are captured and returned in results — a single failure
 * does not abort the entire batch. Does not invalidate deployment-set cache
 * because the deploy operation does not mutate set data.
 *
 * Invalidates ['deployments'] so deployed artifact status reflects the new state.
 *
 * @example
 * const deploy = useBatchDeploySet();
 * deploy.mutate({ set_id: 'abc123', project_id: 'proj456', profile_id: 'prof789' });
 */
export function useBatchDeploySet() {
  const queryClient = useQueryClient();

  return useMutation<
    BatchDeployResponse,
    Error,
    { set_id: string; project_id: string; profile_id?: string }
  >({
    mutationFn: ({ set_id, project_id, profile_id }) =>
      batchDeploySetByProjectId(set_id, { project_id, profile_id }),
    onSuccess: () => {
      // Invalidate deployment queries so deployed artifact status reflects the batch deploy
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
    },
  });
}
