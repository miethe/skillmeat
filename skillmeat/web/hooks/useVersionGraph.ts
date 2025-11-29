/**
 * React Query hook for fetching artifact version graphs
 *
 * Provides data fetching, caching, and state management for version tracking.
 */

import { useQuery } from '@tanstack/react-query';
import type { VersionGraph } from '@/types/version';
import { apiRequest } from '@/lib/api';

// Query keys
export const versionKeys = {
  all: ['versions'] as const,
  graphs: () => [...versionKeys.all, 'graphs'] as const,
  graph: (artifactId: string, collection?: string) =>
    [...versionKeys.graphs(), artifactId, collection] as const,
};

/**
 * Fetch version graph from API
 */
async function fetchVersionGraph(artifactId: string, collection?: string): Promise<VersionGraph> {
  const params = new URLSearchParams();
  if (collection) {
    params.set('collection', collection);
  }

  const queryString = params.toString();
  const path = `/artifacts/${artifactId}/version-graph${queryString ? `?${queryString}` : ''}`;

  return apiRequest<VersionGraph>(path);
}

/**
 * Hook to fetch version graph for an artifact
 *
 * @param artifactId - Artifact ID in format "type:name" (e.g., "skill:pdf-processor")
 * @param collection - Optional collection filter
 * @returns React Query result with version graph data
 */
export function useVersionGraph(artifactId: string, collection?: string) {
  return useQuery({
    queryKey: versionKeys.graph(artifactId, collection),
    queryFn: () => fetchVersionGraph(artifactId, collection),
    staleTime: 5 * 60 * 1000, // 5 minutes (matching backend Cache-Control)
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    enabled: !!artifactId,
  });
}
