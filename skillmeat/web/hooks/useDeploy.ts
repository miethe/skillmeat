/**
 * Deploy hook for artifact deployment operations
 *
 * Provides React Query mutation for deploying artifacts to projects
 * with SSE progress tracking.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiRequest } from '@/lib/api';

export interface DeployRequest {
  artifactId: string;
  artifactName: string;
  artifactType: string;
  projectPath?: string;
  collectionName?: string;
  overwrite?: boolean;
}

export interface DeployResponse {
  success: boolean;
  message: string;
  artifact_name: string;
  artifact_type: string;
  deployed_path?: string;
  error_message?: string;
}

export interface DeployError {
  message: string;
  code?: string;
  details?: any;
}

export interface UseDeployOptions {
  onSuccess?: (data: DeployResponse, variables: DeployRequest) => void;
  onError?: (error: DeployError, variables: DeployRequest) => void;
  onSettled?: () => void;
}

/**
 * Hook to deploy artifacts to projects
 */
export function useDeploy(options: UseDeployOptions = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DeployRequest): Promise<DeployResponse> => {
      // Construct artifact_id in format "type:name"
      const artifactId = `${request.artifactType}:${request.artifactName}`;

      // Call backend API
      const response = await apiRequest<DeployResponse>(`/artifacts/${artifactId}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: request.projectPath,
          overwrite: request.overwrite ?? false,
        }),
      });

      // Check if deployment was successful
      if (!response.success) {
        throw new Error(response.error_message || response.message || 'Deploy failed');
      }

      return response;
    },

    onSuccess: async (data, variables) => {
      // AWAIT all invalidations to ensure cache is fresh before mutation completes
      await queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      await queryClient.invalidateQueries({ queryKey: ['deployments'] });

      // Only invalidate the specific project if we have the project path
      if (variables.projectPath) {
        // Use predicate to only invalidate queries for the deployed project
        await queryClient.invalidateQueries({
          queryKey: ['projects', 'detail'],
          predicate: (query) => {
            // Only invalidate if this query is for the deployed project
            return query.queryKey.some(k =>
              typeof k === 'string' && k.includes(variables.projectPath || '')
            );
          }
        });
      }

      // Show success toast
      toast.success(data.message || 'Deployment successful');

      // Call custom success handler
      options.onSuccess?.(data, variables);
    },

    onError: (error: any, variables) => {
      const deployError: DeployError = {
        message: error.message || 'Deployment failed',
        code: error.code,
        details: error.details,
      };

      // Show error toast
      toast.error(deployError.message);

      // Call custom error handler
      options.onError?.(deployError, variables);
    },

    onSettled: () => {
      options.onSettled?.();
    },
  });
}

/**
 * Hook to undeploy (remove) artifacts from projects
 */
export function useUndeploy(options: UseDeployOptions = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: {
      artifactId: string;
      artifactName: string;
      artifactType: string;
      projectPath?: string;
    }): Promise<DeployResponse> => {
      // Construct artifact_id in format "type:name"
      const artifactId = `${request.artifactType}:${request.artifactName}`;

      if (!request.projectPath) {
        throw new Error('Project path is required for undeploy');
      }

      // Call backend API
      const response = await apiRequest<DeployResponse>(`/artifacts/${artifactId}/undeploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: request.projectPath,
        }),
      });

      // Check if undeploy was successful
      if (!response.success) {
        throw new Error(response.error_message || response.message || 'Undeploy failed');
      }

      return response;
    },

    onSuccess: async (data, variables) => {
      // AWAIT all invalidations to ensure cache is fresh before mutation completes
      await queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      await queryClient.invalidateQueries({ queryKey: ['deployments'] });

      // Only invalidate the specific project if we have the project path
      if (variables.projectPath) {
        // Use predicate to only invalidate queries for the undeployed project
        await queryClient.invalidateQueries({
          queryKey: ['projects', 'detail'],
          predicate: (query) => {
            // Only invalidate if this query is for the undeployed project
            return query.queryKey.some(k =>
              typeof k === 'string' && k.includes(variables.projectPath || '')
            );
          }
        });
      }

      toast.success(data.message || 'Artifact removed successfully');

      options.onSuccess?.(data, variables as DeployRequest);
    },

    onError: (error: any, variables) => {
      const deployError: DeployError = {
        message: error.message || 'Failed to remove artifact',
      };

      toast.error(deployError.message);

      options.onError?.(deployError, variables as DeployRequest);
    },

    onSettled: () => {
      options.onSettled?.();
    },
  });
}
