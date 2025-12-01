/**
 * React Query hook for monitoring cache status
 *
 * Provides real-time cache statistics and health information,
 * allowing the UI to display cache age, staleness, and entry counts.
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

/**
 * Cache statistics response from the backend
 */
export interface CacheStatsResponse {
  /** Number of cached entries */
  entries: number;
  /** Age of the cache in seconds */
  age_seconds: number;
  /** Whether the cache is considered valid/fresh */
  is_valid: boolean;
  /** ISO timestamp of last cache update */
  last_update: string | null;
}

/**
 * Processed cache status for UI consumption
 */
export interface CacheStatus {
  /** Last time cache was refreshed */
  lastRefetch: Date | null;
  /** Age of cache in seconds */
  cacheAge: number;
  /** Whether cache is stale and should be refreshed */
  isStale: boolean;
  /** Total number of projects in cache */
  totalProjects: number;
  /** Number of stale projects (if backend provides this) */
  staleProjects: number;
}

/**
 * Hook to monitor cache status and statistics
 *
 * Polls the backend cache stats endpoint to provide real-time
 * information about cache health, age, and entry counts.
 *
 * @returns Cache status data, loading state, and refresh function
 *
 * @example
 * ```tsx
 * const { status, isLoading } = useCacheStatus();
 *
 * if (status) {
 *   console.log(`Cache has ${status.totalProjects} projects`);
 *   console.log(`Cache age: ${status.cacheAge}s`);
 *   if (status.isStale) {
 *     // Show warning
 *   }
 * }
 * ```
 */
export function useCacheStatus() {
  const query = useQuery({
    queryKey: ['cache', 'status'],
    queryFn: async () => {
      const response = await apiRequest<CacheStatsResponse>('/projects/cache/stats');
      return response;
    },
    staleTime: 30000, // 30 seconds - status data ages quickly
    refetchInterval: 60000, // Refresh every minute for live updates
  });

  // Transform backend response into UI-friendly status
  const status: CacheStatus | null = query.data
    ? {
        lastRefetch: query.data.last_update ? new Date(query.data.last_update) : null,
        cacheAge: query.data.age_seconds,
        isStale: !query.data.is_valid,
        totalProjects: query.data.entries,
        staleProjects: 0, // Backend doesn't currently provide this metric
      }
    : null;

  return {
    /** Processed cache status data */
    status,
    /** Whether the initial query is loading */
    isLoading: query.isLoading,
    /** Query error if any */
    error: query.error,
    /** Manually refresh cache status */
    refresh: query.refetch,
  };
}
