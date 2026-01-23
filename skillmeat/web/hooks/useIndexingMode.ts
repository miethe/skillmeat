/**
 * React Query hook for fetching global indexing mode configuration
 *
 * The indexing mode controls how marketplace artifact discovery is handled:
 * - 'off': Indexing is completely disabled
 * - 'on': All artifacts are automatically indexed
 * - 'opt_in': Users must explicitly enable indexing per artifact (default)
 *
 * This hook provides graceful degradation by defaulting to 'opt_in' on error,
 * ensuring the UI remains functional even if the settings endpoint is unavailable.
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

/**
 * Valid indexing mode values
 */
export type IndexingMode = 'off' | 'on' | 'opt_in';

/**
 * Response from the indexing mode endpoint
 */
export interface IndexingModeResponse {
  indexing_mode: IndexingMode;
}

/**
 * Query key factory for settings-related queries
 */
export const settingsKeys = {
  all: ['settings'] as const,
  indexingMode: () => [...settingsKeys.all, 'indexing-mode'] as const,
};

/**
 * Default indexing mode used when fetching fails (graceful degradation)
 */
const DEFAULT_INDEXING_MODE: IndexingMode = 'opt_in';

/**
 * Hook to fetch the global indexing mode configuration
 *
 * Controls toggle visibility in the UI based on the server's indexing policy.
 * Uses a 5-minute stale time since configuration doesn't change frequently.
 *
 * @returns Query result with indexing mode data and convenience properties
 *
 * @example
 * ```tsx
 * const { indexingMode, isLoading } = useIndexingMode();
 *
 * // Only show toggle when mode is 'opt_in'
 * if (indexingMode === 'opt_in') {
 *   return <IndexingToggle />;
 * }
 *
 * // Automatic indexing when mode is 'on'
 * if (indexingMode === 'on') {
 *   return <span>Indexing enabled globally</span>;
 * }
 * ```
 */
export function useIndexingMode() {
  const query = useQuery({
    queryKey: settingsKeys.indexingMode(),
    queryFn: async () => {
      const response = await apiRequest<IndexingModeResponse>('/settings/indexing-mode');
      return response;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - config doesn't change often
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
    retry: 1, // Only retry once on failure
  });

  // Provide graceful degradation - default to 'opt_in' on error
  const indexingMode: IndexingMode = query.data?.indexing_mode ?? DEFAULT_INDEXING_MODE;

  return {
    /** Current indexing mode (defaults to 'opt_in' on error) */
    indexingMode,
    /** Raw response data from the API */
    data: query.data,
    /** Whether the initial query is loading */
    isLoading: query.isLoading,
    /** Whether data is being fetched (includes background refetch) */
    isFetching: query.isFetching,
    /** Query error if any */
    error: query.error,
    /** Whether indexing toggles should be shown (only in opt_in mode) */
    showToggle: indexingMode === 'opt_in',
    /** Whether indexing is enabled globally (no user choice needed) */
    isGloballyEnabled: indexingMode === 'on',
    /** Whether indexing is completely disabled */
    isDisabled: indexingMode === 'off',
    /** Manually refetch the indexing mode */
    refetch: query.refetch,
  };
}
