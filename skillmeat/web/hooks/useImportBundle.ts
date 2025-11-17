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

      // TODO: Replace with actual API call when P2-002 is complete
      // const preview = await apiClient.bundles.previewBundle({ source });

      // Simulate network delay
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
    mutationFn: async (_request: ImportRequest): Promise<ImportBundleResult> => {
      // TODO: Replace with actual API call when P2-002 is complete
      // const response = await apiClient.bundles.importBundle({ data: request });

      // Simulate network delay
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
 */
export function useValidateImport() {
  return useMutation({
    mutationFn: async (req: Partial<ImportRequest>): Promise<{
      valid: boolean;
      errors: string[];
      warnings: string[];
    }> => {
      // TODO: Replace with actual API call
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
