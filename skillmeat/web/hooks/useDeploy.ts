/**
 * Deploy hook for artifact deployment operations
 *
 * Provides React Query mutation for deploying artifacts to projects
 * with SSE progress tracking.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiConfig, apiRequest } from "@/lib/api";

const USE_MOCKS = apiConfig.useMocks;

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
  deploymentId?: string;
  streamUrl?: string;
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
      try {
        const response = await apiRequest<DeployResponse>("/deploy", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        return response;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[deploy] Deploy API failed, falling back to mock", error);
          await new Promise((resolve) => setTimeout(resolve, 1000));

          return {
            success: true,
            message: `Successfully deployed ${request.artifactName}`,
            deploymentId: `deploy-${Date.now()}`,
            streamUrl: `/api/v1/deploy/${request.artifactId}/stream`,
          };
        }
        throw error;
      }
    },

    onSuccess: (data, variables) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["deployments"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });

      // Show success toast
      toast.success(data.message || "Deployment successful");

      // Call custom success handler
      options.onSuccess?.(data, variables);
    },

    onError: (error: any, variables) => {
      const deployError: DeployError = {
        message: error.message || "Deployment failed",
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
      projectPath?: string;
    }): Promise<DeployResponse> => {
      try {
        const response = await apiRequest<DeployResponse>("/deploy/undeploy", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        return response;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[deploy] Undeploy API failed, falling back to mock", error);
          await new Promise((resolve) => setTimeout(resolve, 500));

          return {
            success: true,
            message: `Successfully removed ${request.artifactName}`,
          };
        }
        throw error;
      }
    },

    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["deployments"] });

      toast.success(data.message || "Artifact removed successfully");

      options.onSuccess?.(data, variables as DeployRequest);
    },

    onError: (error: any, variables) => {
      const deployError: DeployError = {
        message: error.message || "Failed to remove artifact",
      };

      toast.error(deployError.message);

      options.onError?.(deployError, variables as DeployRequest);
    },

    onSettled: () => {
      options.onSettled?.();
    },
  });
}
