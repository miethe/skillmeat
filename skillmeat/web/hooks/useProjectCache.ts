/**
 * React Query hook for project data fetching with cache awareness
 *
 * This hook provides project fetching with backend cache integration,
 * allowing the UI to display cache status and force refresh when needed.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { ProjectSummary, ProjectsResponse } from '@/types/project';

/**
 * Cache information returned by the backend
 */
export interface CacheInfo {
  cacheHit: boolean;
  lastFetched: Date | null;
  isStale: boolean;
}

/**
 * Project with optional cache metadata
 */
export interface ProjectWithCache extends ProjectSummary {
  cache_info?: CacheInfo;
}

/**
 * Options for configuring the project cache hook
 */
export interface UseProjectCacheOptions {
  /** Whether to enable the query (default: true) */
  enabled?: boolean;
  /** How long data stays fresh in ms (default: 60000 = 1 minute) */
  staleTime?: number;
}

/**
 * Hook to fetch projects with cache awareness
 *
 * Fetches project data from the backend and exposes cache metadata
 * when available. The backend may return cache_info in response headers
 * or as part of the project data structure.
 *
 * @param options - Configuration options for the query
 * @returns Query result with projects, cache info, and refresh functions
 *
 * @example
 * ```tsx
 * const { projects, cacheInfo, forceRefresh, isLoading } = useProjectCache();
 *
 * if (cacheInfo?.isStale) {
 *   // Show stale indicator
 * }
 *
 * <Button onClick={forceRefresh}>Refresh</Button>
 * ```
 */
export function useProjectCache(options: UseProjectCacheOptions = {}) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['projects', 'cached'],
    queryFn: async () => {
      const response = await apiRequest<ProjectsResponse>('/projects');
      return response;
    },
    enabled: options.enabled ?? true,
    staleTime: options.staleTime ?? 60000, // 1 minute
    refetchOnWindowFocus: true,
  });

  // Extract cache info if present in the response
  // Note: Backend may add this metadata in future versions
  const cacheInfo: CacheInfo | null =
    query.data?.items?.[0] &&
    'cache_info' in query.data.items[0] &&
    (query.data.items[0] as ProjectWithCache).cache_info
      ? {
          cacheHit: (query.data.items[0] as ProjectWithCache).cache_info!.cacheHit,
          lastFetched: (query.data.items[0] as ProjectWithCache).cache_info!.lastFetched
            ? new Date((query.data.items[0] as ProjectWithCache).cache_info!.lastFetched!)
            : null,
          isStale: (query.data.items[0] as ProjectWithCache).cache_info!.isStale,
        }
      : null;

  /**
   * Force refresh projects, bypassing both frontend and backend cache
   *
   * @returns Promise with fresh project data
   */
  const forceRefresh = async () => {
    const response = await apiRequest<ProjectsResponse>('/projects?force_refresh=true');
    queryClient.setQueryData(['projects', 'cached'], response);
    return response;
  };

  return {
    /** Array of projects from the response */
    projects: query.data?.items ?? [],
    /** Whether the initial query is loading */
    isLoading: query.isLoading,
    /** Whether a fetch is in progress (including refetch) */
    isFetching: query.isFetching,
    /** Query error if any */
    error: query.error,
    /** Cache metadata if available from backend */
    cacheInfo,
    /** Refetch using TanStack Query's refetch (uses cache if available) */
    refetch: query.refetch,
    /** Force refresh bypassing all caches */
    forceRefresh,
  };
}
