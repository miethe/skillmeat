/**
 * React Query hooks for outdated artifact detection
 *
 * Provides data fetching for artifacts with available updates
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

export interface OutdatedArtifact {
  id: string;
  name: string;
  type: string;
  project_name: string;
  project_id: string;
  deployed_version?: string;
  upstream_version?: string;
  version_difference?: string;
}

interface OutdatedArtifactsResponse {
  items: OutdatedArtifact[];
  total: number;
}

interface UseOutdatedArtifactsOptions {
  type?: string;
  sortBy?: 'name' | 'type' | 'project' | 'version_diff';
}

// Query keys
const outdatedArtifactKeys = {
  all: ['outdated-artifacts'] as const,
  lists: () => [...outdatedArtifactKeys.all, 'list'] as const,
  list: (options?: UseOutdatedArtifactsOptions) =>
    [...outdatedArtifactKeys.lists(), options] as const,
};

async function fetchOutdatedArtifacts(
  options?: UseOutdatedArtifactsOptions
): Promise<OutdatedArtifactsResponse> {
  const params = new URLSearchParams();

  if (options?.type) {
    params.set('type', options.type);
  }

  if (options?.sortBy) {
    params.set('sort_by', options.sortBy);
  }

  const queryString = params.toString();
  const url = queryString ? `/cache/stale-artifacts?${queryString}` : '/cache/stale-artifacts';

  return await apiRequest<OutdatedArtifactsResponse>(url);
}

/**
 * Hook to fetch outdated artifacts from the cache
 *
 * @param options - Optional filters and sorting
 * @returns Query result with outdated artifacts list
 */
export function useOutdatedArtifacts(options?: UseOutdatedArtifactsOptions) {
  return useQuery({
    queryKey: outdatedArtifactKeys.list(options),
    queryFn: async (): Promise<OutdatedArtifactsResponse> => {
      return await fetchOutdatedArtifacts(options);
    },
    staleTime: 2 * 60 * 1000, // Consider stale after 2 minutes
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}
