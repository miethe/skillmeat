/**
 * Hook for force re-importing catalog entries from upstream sources
 *
 * Re-downloads artifact files from the upstream GitHub repository,
 * overwriting any local changes. Optionally preserves deployment records.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from './use-toast';
import { apiRequest } from '@/lib/api';
import { sourceKeys } from './useMarketplaceSources';

export interface ReimportRequest {
  keep_deployments: boolean;
}

export interface ReimportResponse {
  success: boolean;
  artifact_id: string | null;
  message: string;
  deployments_restored: number;
}

/**
 * Force re-import a catalog entry from its upstream source
 *
 * @param sourceId - The marketplace source ID
 * @returns Mutation hook for re-importing entries
 *
 * @example
 * ```tsx
 * const reimportMutation = useReimportCatalogEntry(sourceId);
 *
 * const handleReimport = () => {
 *   reimportMutation.mutate({
 *     entryId: entry.id,
 *     keepDeployments: true,
 *   });
 * };
 * ```
 */
export function useReimportCatalogEntry(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<ReimportResponse, Error, { entryId: string; keepDeployments: boolean }>({
    mutationFn: async ({ entryId, keepDeployments }) => {
      const response = await apiRequest<ReimportResponse>(
        `/marketplace/sources/${sourceId}/entries/${entryId}/reimport`,
        {
          method: 'POST',
          body: JSON.stringify({ keep_deployments: keepDeployments } as ReimportRequest),
        }
      );
      return response;
    },
    onSuccess: (result) => {
      // Invalidate catalog entries for this source
      queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
      // Invalidate artifacts list since the artifact was updated
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      // Invalidate collections to refresh artifact data
      queryClient.invalidateQueries({ queryKey: ['collections'] });

      const description =
        result.deployments_restored > 0
          ? `${result.message}. ${result.deployments_restored} deployment(s) restored.`
          : result.message;

      toast({
        title: 'Re-import successful',
        description,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Re-import failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}
