/**
 * React Query hook for project-specific artifact discovery
 *
 * This hook provides discovery capabilities for a single project's .claude/ directory,
 * as opposed to the collection-wide discovery hook.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { DiscoveryResult, BulkImportRequest, BulkImportResult } from '@/types/discovery';

/**
 * Hook for discovering artifacts in a specific project's .claude/ directory.
 *
 * @param projectPath - The filesystem path to the project
 * @returns Discovery state and functions
 */
export function useProjectDiscovery(projectPath: string | undefined, projectId?: string) {
  const queryClient = useQueryClient();

  // Encode the project path for URL
  const encodedPath = projectPath ? encodeURIComponent(projectPath) : '';

  // Discovery query - only runs when manually triggered
  const discoveryQuery = useQuery({
    queryKey: ['artifacts', 'discover', 'project', projectPath],
    queryFn: async (): Promise<DiscoveryResult> => {
      if (!projectPath) {
        return { discovered_count: 0, artifacts: [], errors: [], scan_duration_ms: 0 };
      }

      const result = await apiRequest<DiscoveryResult>(
        `/artifacts/discover/project/${encodedPath}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return result;
    },
    enabled: false, // Manual trigger only
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  // Bulk import mutation
  const bulkImportMutation = useMutation({
    mutationFn: async (request: BulkImportRequest): Promise<BulkImportResult> => {
      const params = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';

      return await apiRequest<BulkImportResult>(`/artifacts/discover/import${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
    },
    onSuccess: () => {
      // Invalidate both project discovery and artifacts list
      queryClient.invalidateQueries({ queryKey: ['artifacts', 'discover', 'project', projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ['projects', 'detail', projectId] });
        queryClient.invalidateQueries({ queryKey: ['projects', 'list'] });
      }
    },
  });

  return {
    discoveredArtifacts: discoveryQuery.data?.artifacts || [],
    discoveredCount: discoveryQuery.data?.discovered_count || 0,
    isDiscovering: discoveryQuery.isFetching,
    discoverError: discoveryQuery.error,
    refetchDiscovery: discoveryQuery.refetch,
    bulkImport: bulkImportMutation.mutateAsync,
    isImporting: bulkImportMutation.isPending,
  };
}
