/**
 * React Query hook for bundle export operations
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { ExportRequest, Bundle, ShareLink } from '@/types/bundle';
import { apiConfig, apiRequest } from '@/lib/api';

const USE_MOCKS = apiConfig.useMocks;

export interface ExportProgress {
  step: 'preparing' | 'collecting' | 'compressing' | 'uploading' | 'generating-link' | 'complete';
  progress: number; // 0-100
  message: string;
}

export interface ExportBundleResult {
  bundle: Bundle;
  downloadUrl?: string;
  streamUrl?: string; // SSE endpoint for progress updates
}

/**
 * Hook to export a bundle with progress tracking
 */
export function useExportBundle({
  onSuccess,
  onError,
}: {
  onSuccess?: (data: ExportBundleResult) => void;
  onError?: (error: Error) => void;
} = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ExportRequest): Promise<ExportBundleResult> => {
      try {
        const response = await apiRequest<ExportBundleResult>('/bundles/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });
        return response;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[bundles] Export API failed, falling back to mock', error);
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Mock response
          const bundle: Bundle = {
            id: `bundle-${Date.now()}`,
            metadata: request.metadata,
            artifacts: request.artifactIds.map((id) => ({
              artifact: {
                id,
                uuid: '',
                name: `artifact-${id}`,
                type: 'skill',
                scope: 'user',
                syncStatus: 'synced',
                version: '1.0.0',
                upstream: { enabled: false, updateAvailable: false },
                usageStats: {
                  totalDeployments: 0,
                  activeProjects: 0,
                  usageCount: 0,
                },
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
              },
              dependencies: [],
              files: [],
            })),
            exportedAt: new Date().toISOString(),
            exportedBy: 'current-user',
            format: request.options.format,
            size: 1024 * 1024, // 1MB
            checksumSha256: 'mock-checksum',
          };

          if (request.options.generateShareLink) {
            const shareLink: ShareLink = {
              url: `https://skillmeat.example.com/share/${bundle.id}`,
              shortUrl: `https://sm.example.com/${bundle.id.slice(0, 8)}`,
              qrCode: 'data:image/png;base64,mock-qr-code',
              permissionLevel: request.options.permissionLevel,
              downloadCount: 0,
              createdAt: new Date().toISOString(),
            };

            if (request.options.linkExpiration && request.options.linkExpiration > 0) {
              const expiresAt = new Date();
              expiresAt.setHours(expiresAt.getHours() + request.options.linkExpiration);
              shareLink.expiresAt = expiresAt.toISOString();
            }

            bundle.shareLink = shareLink;
          }

          if (request.options.vault) {
            bundle.vault = request.options.vault;
          }

          return {
            bundle,
            downloadUrl: `/api/bundles/${bundle.id}/download`,
            streamUrl: `/api/bundles/${bundle.id}/export/stream`,
          };
        }
        throw error;
      }
    },
    onSuccess: (data) => {
      // Invalidate bundle queries
      queryClient.invalidateQueries({ queryKey: ['bundles'] });
      onSuccess?.(data);
    },
    onError: (error: Error) => {
      console.error('Export failed:', error);
      onError?.(error);
    },
  });
}

/**
 * Hook to validate export request before executing
 * Note: Uses client-side validation as no backend validation endpoint exists
 */
export function useValidateExport() {
  return useMutation({
    mutationFn: async (
      request: Partial<ExportRequest>
    ): Promise<{
      valid: boolean;
      errors: string[];
      warnings: string[];
      estimatedSize: number;
    }> => {
      // Client-side validation
      await new Promise((resolve) => setTimeout(resolve, 300));

      const errors: string[] = [];
      const warnings: string[] = [];

      if (!request.artifactIds || request.artifactIds.length === 0) {
        errors.push('At least one artifact must be selected');
      }

      if (!request.metadata?.name) {
        errors.push('Bundle name is required');
      }

      if (request.artifactIds && request.artifactIds.length > 100) {
        warnings.push('Large bundles may take longer to export');
      }

      return {
        valid: errors.length === 0,
        errors,
        warnings,
        estimatedSize: (request.artifactIds?.length || 0) * 100 * 1024, // 100KB per artifact
      };
    },
  });
}
