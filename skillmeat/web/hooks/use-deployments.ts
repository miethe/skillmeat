/**
 * Custom hooks for deployment management using TanStack Query
 *
 * Provides hooks for deploying artifacts, listing deployments, and managing
 * deployment state with automatic cache invalidation.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query';
import {
  deployArtifact,
  undeployArtifact,
  listDeployments,
  getDeploymentSummary,
  getDeployments,
  type DeploymentSummary,
  type DeploymentQueryParams,
} from '@/lib/api/deployments';
import type {
  ArtifactDeployRequest,
  ArtifactUndeployRequest,
  ArtifactDeploymentResponse,
  ArtifactUndeployResponse,
  ArtifactDeploymentInfo,
  ArtifactDeploymentListResponse,
} from '@/types/deployments';

/**
 * Query keys factory for deployment-related queries
 * Structured hierarchically for efficient cache invalidation
 */
export const deploymentKeys = {
  all: ['deployments'] as const,
  lists: () => [...deploymentKeys.all, 'list'] as const,
  list: (projectPath?: string) => [...deploymentKeys.lists(), { projectPath }] as const,
  summaries: () => [...deploymentKeys.all, 'summary'] as const,
  summary: (projectPath?: string) => [...deploymentKeys.summaries(), { projectPath }] as const,
  filtered: (params?: DeploymentQueryParams) =>
    [...deploymentKeys.lists(), 'filtered', params] as const,
};

/**
 * List all deployments for a project
 *
 * @param projectPath - Optional project path (uses CWD if not specified)
 * @param options - Optional query options (enabled, staleTime)
 * @returns Query result with deployment list
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useDeploymentList('/path/to/project');
 * if (data) {
 *   console.log(`${data.total} deployments found`);
 *   data.deployments.map(deployment => (
 *     <DeploymentCard key={deployment.artifact_name} deployment={deployment} />
 *   ))
 * }
 * ```
 *
 * @example
 * ```tsx
 * // Performance: only fetch when dialog is open
 * const { data } = useDeploymentList(undefined, { enabled: open });
 * ```
 */
export function useDeploymentList(
  projectPath?: string,
  options?: { enabled?: boolean; staleTime?: number }
): UseQueryResult<ArtifactDeploymentListResponse, Error> {
  return useQuery({
    queryKey: deploymentKeys.list(projectPath),
    queryFn: () => listDeployments(projectPath),
    staleTime: options?.staleTime ?? 120_000, // 2 min: deployment domain standard
    gcTime: 300_000,                          // 5 min: keep in cache after unmount
    refetchOnWindowFocus: true, // Refetch when user returns to window
    enabled: options?.enabled ?? true,
  });
}

/**
 * Get deployments with optional filtering
 *
 * @param params - Query parameters for filtering
 * @returns Query result with filtered deployments
 *
 * @example
 * ```tsx
 * const { data: skillDeployments } = useDeployments({
 *   projectPath: '/path/to/project',
 *   artifactType: 'skill',
 *   syncStatus: 'synced',
 * });
 * ```
 */
export function useDeployments(
  params?: DeploymentQueryParams
): UseQueryResult<ArtifactDeploymentInfo[], Error> {
  return useQuery({
    queryKey: deploymentKeys.filtered(params),
    queryFn: () => getDeployments(params),
    staleTime: 120_000, // 2 min: deployment domain standard
    gcTime: 300_000,    // 5 min: keep in cache after unmount
    enabled: true,
  });
}

/**
 * Get deployment summary statistics
 *
 * @param projectPath - Optional project path
 * @returns Query result with deployment summary
 *
 * @example
 * ```tsx
 * const { data: summary } = useDeploymentSummary();
 * if (summary) {
 *   console.log(`Total: ${summary.total}`);
 *   console.log(`Skills: ${summary.byType.skill || 0}`);
 *   console.log(`Synced: ${summary.byStatus.synced}`);
 * }
 * ```
 */
export function useDeploymentSummary(
  projectPath?: string
): UseQueryResult<DeploymentSummary, Error> {
  return useQuery({
    queryKey: deploymentKeys.summary(projectPath),
    queryFn: () => getDeploymentSummary(projectPath),
    staleTime: 120_000, // 2 min: deployment domain standard
    gcTime: 300_000,    // 5 min: keep in cache after unmount
  });
}

/**
 * Deploy an artifact to a project mutation
 *
 * Automatically invalidates deployment queries for the target project on success
 *
 * @example
 * ```tsx
 * const deployMutation = useDeployArtifact();
 *
 * const handleDeploy = async () => {
 *   await deployMutation.mutateAsync({
 *     artifact_id: 'skill:pdf',
 *     artifact_name: 'pdf',
 *     artifact_type: 'skill',
 *     project_path: '/path/to/project',
 *     overwrite: false,
 *   });
 * };
 * ```
 */
export function useDeployArtifact(): UseMutationResult<
  ArtifactDeploymentResponse,
  Error,
  ArtifactDeployRequest
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deployArtifact,
    onSuccess: (_, variables) => {
      // Invalidate all deployment queries for this project
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.list(variables.project_path),
      });
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.summary(variables.project_path),
      });
      // Invalidate all filtered queries
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.lists(),
      });
    },
    onError: (error) => {
      console.error('[deployments] Deploy failed:', error);
    },
  });
}

/**
 * Undeploy (remove) an artifact from a project mutation
 *
 * Automatically invalidates deployment queries for the target project on success
 *
 * @example
 * ```tsx
 * const undeployMutation = useUndeployArtifact();
 *
 * const handleUndeploy = async () => {
 *   await undeployMutation.mutateAsync({
 *     artifact_name: 'pdf',
 *     artifact_type: 'skill',
 *     project_path: '/path/to/project',
 *   });
 * };
 * ```
 */
export function useUndeployArtifact(): UseMutationResult<
  ArtifactUndeployResponse,
  Error,
  ArtifactUndeployRequest
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: undeployArtifact,
    onSuccess: (_, variables) => {
      // Invalidate all deployment queries for this project
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.list(variables.project_path),
      });
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.summary(variables.project_path),
      });
      // Invalidate all filtered queries
      queryClient.invalidateQueries({
        queryKey: deploymentKeys.lists(),
      });
    },
    onError: (error) => {
      console.error('[deployments] Undeploy failed:', error);
    },
  });
}

/**
 * Refresh deployment data for a project
 *
 * Utility hook to manually refresh deployment queries
 *
 * @example
 * ```tsx
 * const refreshDeployments = useRefreshDeployments();
 *
 * const handleRefresh = () => {
 *   refreshDeployments('/path/to/project');
 * };
 * ```
 */
export function useRefreshDeployments() {
  const queryClient = useQueryClient();

  return (projectPath?: string) => {
    queryClient.invalidateQueries({
      queryKey: deploymentKeys.list(projectPath),
    });
    queryClient.invalidateQueries({
      queryKey: deploymentKeys.summary(projectPath),
    });
  };
}
