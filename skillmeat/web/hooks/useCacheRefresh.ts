/**
 * React Query mutation hook for cache refresh operations
 *
 * Provides a mutation to trigger backend cache refresh and automatically
 * invalidates related queries to ensure UI consistency.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

/**
 * Result of a cache refresh operation
 */
export interface RefreshResult {
  /** Whether the refresh succeeded */
  success: boolean;
  /** Human-readable message about the refresh operation */
  message: string;
  /** Optional statistics about the refreshed cache */
  stats?: {
    /** Number of entries in the refreshed cache */
    entries: number;
  };
}

/**
 * Hook to trigger cache refresh operations
 *
 * Provides a mutation to force-refresh the backend cache and automatically
 * invalidates all project and cache-related queries to ensure the UI
 * displays fresh data.
 *
 * @returns Mutation function, loading state, and result data
 *
 * @example
 * ```tsx
 * const { refresh, isRefreshing, lastRefreshResult } = useCacheRefresh();
 *
 * const handleRefresh = async () => {
 *   try {
 *     const result = await refresh();
 *     toast.success(result.message);
 *   } catch (error) {
 *     toast.error('Failed to refresh cache');
 *   }
 * };
 *
 * <Button onClick={handleRefresh} disabled={isRefreshing}>
 *   {isRefreshing ? 'Refreshing...' : 'Refresh Cache'}
 * </Button>
 * ```
 */
export function useCacheRefresh() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest<RefreshResult>('/projects/cache/refresh', {
        method: 'POST',
      });
      return response;
    },
    onSuccess: () => {
      // Invalidate all project-related queries to trigger refetch with fresh data
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      // Invalidate cache status to show updated stats
      queryClient.invalidateQueries({ queryKey: ['cache'] });
    },
  });

  return {
    /**
     * Trigger a cache refresh
     * @returns Promise with refresh result
     */
    refresh: mutation.mutateAsync,
    /** Whether a refresh is currently in progress */
    isRefreshing: mutation.isPending,
    /** Mutation error if refresh failed */
    error: mutation.error,
    /** Result of the last refresh operation */
    lastRefreshResult: mutation.data ?? null,
  };
}
