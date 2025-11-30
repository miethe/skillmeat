/**
 * React Query hooks for artifact discovery operations
 *
 * These hooks provide data fetching and mutation capabilities for:
 * - Discovery: Scanning for artifacts
 * - Bulk Import: Importing multiple artifacts at once
 * - GitHub Metadata: Fetching metadata from GitHub sources
 * - Parameter Updates: Editing artifact parameters
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type {
  DiscoveryResult,
  BulkImportRequest,
  BulkImportResult,
  GitHubMetadata,
  GitHubMetadataResponse,
  ArtifactParameters,
  ParameterUpdateResponse,
} from '@/types/discovery';

/**
 * Hook for artifact discovery and bulk import operations
 *
 * @returns Discovery state and mutation functions
 */
export function useDiscovery() {
  const queryClient = useQueryClient();

  // Discovery query - scan for artifacts
  // Using enabled: false for manual trigger with refetch
  const discoverQuery = useQuery({
    queryKey: ['artifacts', 'discover'],
    queryFn: async (): Promise<DiscoveryResult> => {
      return await apiRequest<DiscoveryResult>('/artifacts/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
    },
    enabled: false, // Manual trigger with refetch
    staleTime: 0, // Always refetch when triggered
  });

  // Bulk import mutation
  const bulkImportMutation = useMutation({
    mutationFn: async (request: BulkImportRequest): Promise<BulkImportResult> => {
      return await apiRequest<BulkImportResult>('/artifacts/discover/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
    },
    onSuccess: () => {
      // Invalidate artifact list queries to refresh UI
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });

  return {
    // Discovery state
    discoveredArtifacts: discoverQuery.data?.artifacts ?? [],
    discoveredCount: discoverQuery.data?.discovered_count ?? 0,
    scanErrors: discoverQuery.data?.errors ?? [],
    scanDuration: discoverQuery.data?.scan_duration_ms,
    isDiscovering: discoverQuery.isLoading || discoverQuery.isFetching,
    discoverError: discoverQuery.error,
    refetchDiscovery: discoverQuery.refetch,

    // Import state
    bulkImport: bulkImportMutation.mutateAsync,
    isImporting: bulkImportMutation.isPending,
    importError: bulkImportMutation.error,
    importResult: bulkImportMutation.data,
  };
}

/**
 * Hook for fetching GitHub metadata for an artifact source
 *
 * @returns Mutation function and state for GitHub metadata fetch
 */
export function useGitHubMetadata() {
  return useMutation({
    mutationFn: async (source: string): Promise<GitHubMetadata> => {
      const encodedSource = encodeURIComponent(source);
      const response = await apiRequest<GitHubMetadataResponse>(
        `/artifacts/metadata/github?source=${encodedSource}`
      );

      if (!response.success) {
        throw new Error(response.error || 'Metadata fetch failed');
      }

      if (!response.metadata) {
        throw new Error('No metadata returned from API');
      }

      return response.metadata;
    },
  });
}

/**
 * Hook for editing artifact parameters
 *
 * @returns Mutation function and state for parameter updates
 */
export function useEditArtifactParameters() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      artifactId,
      parameters,
    }: {
      artifactId: string;
      parameters: ArtifactParameters;
    }): Promise<ParameterUpdateResponse> => {
      const encodedId = encodeURIComponent(artifactId);
      return await apiRequest<ParameterUpdateResponse>(`/artifacts/${encodedId}/parameters`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parameters }),
      });
    },
    onSuccess: (_, { artifactId }) => {
      // Invalidate specific artifact and list queries to refresh UI
      queryClient.invalidateQueries({ queryKey: ['artifacts', 'detail', artifactId] });
      queryClient.invalidateQueries({ queryKey: ['artifacts', 'list'] });
    },
  });
}
