/**
 * Custom hook for artifact deletion orchestration using TanStack Query
 *
 * Handles coordinated deletion of artifacts from collection, projects, and deployments.
 * Uses TanStack Query mutation pattern with proper error handling and cache invalidation.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteArtifactFromCollection } from '@/lib/api/artifacts';
import { undeployArtifact } from '@/lib/api/deployments';
import type { Artifact } from '@/types/artifact';

/**
 * Parameters for artifact deletion operation
 */
export interface DeletionParams {
  /** Artifact to delete */
  artifact: Artifact;
  /** Whether to delete from collection */
  deleteFromCollection: boolean;
  /** Whether to delete from projects (undeploy) */
  deleteFromProjects: boolean;
  /** Whether to delete deployments metadata */
  deleteDeployments: boolean;
  /** Project paths to undeploy from */
  selectedProjectPaths: string[];
  /** Deployment paths to delete (future use) */
  selectedDeploymentPaths: string[];
}

/**
 * Result of deletion operation
 */
export interface DeletionResult {
  /** Whether collection deletion succeeded */
  collectionDeleted: boolean;
  /** Number of projects successfully undeployed */
  projectsUndeployed: number;
  /** Number of deployments deleted (future use) */
  deploymentsDeleted: number;
  /** List of errors encountered during deletion */
  errors: Array<{ operation: string; error: string }>;
}

/**
 * Hook for orchestrating artifact deletion across collection and projects
 *
 * Uses Promise.allSettled for parallel undeploy operations with comprehensive error tracking.
 *
 * @returns Mutation hook with deletion orchestration
 *
 * @example
 * ```tsx
 * const deletion = useArtifactDeletion();
 * await deletion.mutateAsync({
 *   artifact,
 *   deleteFromCollection: true,
 *   deleteFromProjects: true,
 *   deleteDeployments: false,
 *   selectedProjectPaths: ['/path/to/project'],
 *   selectedDeploymentPaths: [],
 * });
 * ```
 */
export function useArtifactDeletion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: DeletionParams): Promise<DeletionResult> => {
      const result: DeletionResult = {
        collectionDeleted: false,
        projectsUndeployed: 0,
        deploymentsDeleted: 0,
        errors: [],
      };

      // Step 1: Delete from collection if requested
      if (params.deleteFromCollection) {
        try {
          await deleteArtifactFromCollection(params.artifact.id);
          result.collectionDeleted = true;
        } catch (error) {
          result.errors.push({
            operation: 'collection_deletion',
            error: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      }

      // Step 2: Undeploy from selected projects in parallel
      if (params.deleteFromProjects && params.selectedProjectPaths.length > 0) {
        const undeployPromises = params.selectedProjectPaths.map((projectPath) =>
          undeployArtifact({
            artifact_name: params.artifact.name,
            artifact_type: params.artifact.type,
            project_path: projectPath,
          })
        );

        const undeployResults = await Promise.allSettled(undeployPromises);

        undeployResults.forEach((outcome, index) => {
          if (outcome.status === 'fulfilled') {
            result.projectsUndeployed++;
          } else {
            result.errors.push({
              operation: `undeploy:${params.selectedProjectPaths[index]}`,
              error: outcome.reason?.message || 'Unknown error',
            });
          }
        });
      }

      // If ALL operations failed, throw an error
      const totalOperations =
        (params.deleteFromCollection ? 1 : 0) + params.selectedProjectPaths.length;
      const totalFailures = result.errors.length;

      if (totalOperations > 0 && totalFailures === totalOperations) {
        throw new Error(
          `All deletion operations failed:\n${result.errors.map((e) => `- ${e.operation}: ${e.error}`).join('\n')}`
        );
      }

      return result;
    },
    onSuccess: () => {
      // Invalidate all relevant query caches
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['entities'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
