/**
 * React Query hook for bundle import operations
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ImportRequest,
  ImportResult,
  BundlePreview,
  BundleSource,
} from "@/types/bundle";
import { apiConfig, apiRequest } from "@/lib/api";

const USE_MOCKS = apiConfig.useMocks;

export interface ImportProgress {
  step: "uploading" | "validating" | "resolving" | "installing" | "complete";
  progress: number; // 0-100
  message: string;
  currentArtifact?: string;
}

export interface ImportBundleResult {
  result: ImportResult;
  streamUrl?: string; // SSE endpoint for progress updates
}

/**
 * Hook to preview a bundle before importing
 */
export function usePreviewBundle(source: BundleSource | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ["bundle-preview", source],
    queryFn: async (): Promise<BundlePreview | null> => {
      if (!source) return null;

      try {
        // Create FormData for multipart upload
        const formData = new FormData();

        // Handle different source types
        if (source.type === "file") {
          formData.append("bundle_file", source.file);
        } else if (source.type === "url") {
          // For URL sources, we need to fetch the file first
          // This is a limitation - the backend expects a file upload
          throw new Error("URL source type not yet supported for preview");
        } else if (source.type === "vault") {
          // Vault sources also not supported directly
          throw new Error("Vault source type not yet supported for preview");
        }

        const response = await apiRequest<BundlePreview>("/bundles/preview", {
          method: "POST",
          body: formData,
          // Don't set Content-Type header - browser will set it with boundary
        });
        return response;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] Preview API failed, falling back to mock", error);
          await new Promise((resolve) => setTimeout(resolve, 500));

          // Mock preview
          return {
            bundle: {
              id: "preview-bundle",
              metadata: {
                name: "Sample Bundle",
                description: "A sample bundle for testing",
                tags: ["test", "sample"],
                author: "Test User",
                version: "1.0.0",
                createdAt: new Date().toISOString(),
              },
              artifacts: [
                {
                  artifact: {
                    id: "1",
                    name: "canvas-design",
                    type: "skill",
                    scope: "user",
                    status: "active",
                    version: "v2.1.0",
                    metadata: {
                      title: "Canvas Design",
                      description: "Create visual designs",
                    },
                    upstreamStatus: { hasUpstream: false, isOutdated: false },
                    usageStats: {
                      totalDeployments: 0,
                      activeProjects: 0,
                      usageCount: 0,
                    },
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                  },
                },
              ],
              exportedAt: new Date().toISOString(),
              exportedBy: "test-user",
              format: "zip",
              size: 1024 * 1024,
              checksumSha256: "mock-checksum",
            },
            conflicts: [],
            newArtifacts: ["1"],
            existingArtifacts: [],
            willImport: 1,
            willSkip: 0,
            willMerge: 0,
            willFork: 0,
          };
        }
        throw error;
      }
    },
    enabled: enabled && !!source,
    staleTime: 0, // Always fetch fresh preview
  });
}

/**
 * Hook to import a bundle with progress tracking
 */
export function useImportBundle({
  onSuccess,
  onError,
}: {
  onSuccess?: (data: ImportBundleResult) => void;
  onError?: (error: Error) => void;
} = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ImportRequest): Promise<ImportBundleResult> => {
      try {
        // Create FormData for multipart upload
        const formData = new FormData();

        // Handle bundle source
        if (request.source.type === "file") {
          formData.append("bundle_file", request.source.file);
        } else if (request.source.type === "url") {
          // URL sources need different handling
          throw new Error("URL source type not yet supported for import");
        } else if (request.source.type === "vault") {
          // Vault sources need different handling
          throw new Error("Vault source type not yet supported for import");
        }

        // The backend expects form fields, but the current ImportRequest
        // type may not have all needed fields. Add them as they become available.
        // TODO: Update ImportRequest type to match backend schema

        const response = await apiRequest<ImportBundleResult>("/bundles/import", {
          method: "POST",
          body: formData,
          // Don't set Content-Type header - browser will set it with boundary
        });
        return response;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] Import API failed, falling back to mock", error);
          await new Promise((resolve) => setTimeout(resolve, 1500));

          // Mock response
          const result: ImportResult = {
            success: true,
            imported: ["1"],
            skipped: [],
            merged: [],
            forked: [],
            errors: [],
            summary: "Successfully imported 1 artifact",
          };

          return {
            result,
            streamUrl: `/api/bundles/import/stream`,
          };
        }
        throw error;
      }
    },
    onSuccess: (data) => {
      // Invalidate artifact and bundle queries
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["bundles"] });
      onSuccess?.(data);
    },
    onError: (error: Error) => {
      console.error("Import failed:", error);
      onError?.(error);
    },
  });
}

/**
 * Hook to validate import request before executing
 * Note: Uses client-side validation as no backend validation endpoint exists
 */
export function useValidateImport() {
  return useMutation({
    mutationFn: async (req: Partial<ImportRequest>): Promise<{
      valid: boolean;
      errors: string[];
      warnings: string[];
    }> => {
      // Client-side validation
      await new Promise((resolve) => setTimeout(resolve, 300));

      const errors: string[] = [];
      const warnings: string[] = [];

      if (!req.source) {
        errors.push("Bundle source is required");
      }

      return {
        valid: errors.length === 0,
        errors,
        warnings,
      };
    },
  });
}
