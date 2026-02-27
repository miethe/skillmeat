/**
 * React Query hooks for similarity settings and consolidation clusters.
 *
 * Sections:
 *   1. useSimilaritySettings — reads/mutates threshold + color settings
 *   2. useConsolidationClusters — infinite-scroll list of similarity clusters
 *   3. useIgnorePair / useUnignorePair — ignore/unignore a specific pair
 *
 * Endpoints:
 *   GET  /api/v1/settings/similarity              → current thresholds + colors
 *   PUT  /api/v1/settings/similarity/thresholds   → partial threshold update
 *   PUT  /api/v1/settings/similarity/colors       → partial color update
 *   GET  /api/v1/artifacts/consolidation/clusters → paginated cluster list
 *   POST /api/v1/artifacts/consolidation/pairs/{pairId}/ignore
 *   DELETE /api/v1/artifacts/consolidation/pairs/{pairId}/ignore
 *
 * @example
 * ```tsx
 * const { thresholds, colors, isLoading, updateThresholds } = useSimilaritySettings();
 *
 * if (isLoading) return <Spinner />;
 *
 * // Apply a stricter "high" threshold
 * await updateThresholds({ high: 0.90 });
 * ```
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type {
  SimilaritySettings,
  SimilarityThresholds,
  SimilarityColors,
  ConsolidationCluster,
  ConsolidationClustersResponse,
  ConsolidationClustersOptions,
} from '@/types/similarity';

// Re-export types so consumers can import from the hook module directly
export type {
  SimilarityThresholds,
  SimilarityColors,
  SimilaritySettings,
  ConsolidationCluster,
  ConsolidationClustersResponse,
  ConsolidationClustersOptions,
};

// ============================================================================
// Defaults
// ============================================================================

/**
 * Fallback threshold values used when the settings endpoint is unavailable.
 * These must stay in sync with the backend's DEFAULT_SIMILARITY_THRESHOLDS.
 */
const DEFAULT_THRESHOLDS: SimilarityThresholds = {
  high: 0.80,
  partial: 0.55,
  low: 0.35,
  floor: 0.20,
};

/**
 * Fallback color values used when the settings endpoint is unavailable.
 * These must stay in sync with the backend's DEFAULT_SIMILARITY_COLORS.
 */
const DEFAULT_COLORS: SimilarityColors = {
  high: '#22c55e',    // green-500
  partial: '#eab308', // yellow-500
  low: '#f97316',     // orange-500
};

// ============================================================================
// Query Key Factories
// ============================================================================

/**
 * Query key factory for similarity settings.
 *
 * Extends the existing `settingsKeys` namespace without importing it to
 * avoid a circular dependency between hook files.  The `['settings']` root
 * key ensures that a broad `invalidateQueries({ queryKey: ['settings'] })`
 * from any sibling hook will also sweep these entries.
 */
export const similaritySettingsKeys = {
  all: ['settings', 'similarity'] as const,
  settings: () => [...similaritySettingsKeys.all] as const,
  thresholds: () => [...similaritySettingsKeys.all, 'thresholds'] as const,
  colors: () => [...similaritySettingsKeys.all, 'colors'] as const,
};

/**
 * Query key factory for consolidation cluster queries.
 *
 * Scoped under `['artifacts', 'consolidation']` so broad artifact invalidations
 * naturally sweep cluster data too.
 */
export const consolidationKeys = {
  all: ['artifacts', 'consolidation'] as const,
  clusters: (minScore?: number) =>
    [...consolidationKeys.all, 'clusters', { minScore }] as const,
};

// ============================================================================
// API Functions — Settings
// ============================================================================

/**
 * Fetch the full similarity settings bundle from the API.
 *
 * Returns both thresholds and colors in a single request to minimize
 * round-trips; components that only need one half still benefit from the
 * shared cache entry.
 */
async function fetchSimilaritySettings(): Promise<SimilaritySettings> {
  return apiRequest<SimilaritySettings>('/settings/similarity');
}

/**
 * Perform a partial update on the similarity thresholds.
 *
 * Only the provided fields are sent; the backend merges them with the
 * current stored values.  The full updated thresholds object is returned.
 */
async function patchSimilarityThresholds(
  values: Partial<SimilarityThresholds>
): Promise<SimilarityThresholds> {
  return apiRequest<SimilarityThresholds>('/settings/similarity/thresholds', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  });
}

/**
 * Perform a partial update on the similarity score-band colors.
 *
 * Only the provided fields are sent; the backend merges them with the
 * current stored values.  The full updated colors object is returned.
 */
async function patchSimilarityColors(
  values: Partial<SimilarityColors>
): Promise<SimilarityColors> {
  return apiRequest<SimilarityColors>('/settings/similarity/colors', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  });
}

// ============================================================================
// API Functions — Consolidation
// ============================================================================

/**
 * Fetch a single page of consolidation clusters.
 *
 * @param minScore - Minimum pairwise score a pair must exceed
 * @param limit    - Page size (default 20)
 * @param cursor   - Opaque continuation cursor from a previous response
 */
async function fetchConsolidationClusters(
  minScore: number | undefined,
  limit: number,
  cursor: string | undefined
): Promise<ConsolidationClustersResponse> {
  const params = new URLSearchParams();
  if (minScore !== undefined) params.set('min_score', String(minScore));
  params.set('limit', String(limit));
  if (cursor) params.set('cursor', cursor);

  const qs = params.toString();
  return apiRequest<ConsolidationClustersResponse>(
    `/artifacts/consolidation/clusters${qs ? `?${qs}` : ''}`
  );
}

/**
 * Mark an artifact pair as ignored.
 *
 * The backend records this preference and will exclude the pair from future
 * cluster results unless the caller explicitly requests ignored pairs.
 */
async function postIgnorePair(pairId: string): Promise<void> {
  return apiRequest<void>(`/artifacts/consolidation/pairs/${encodeURIComponent(pairId)}/ignore`, {
    method: 'POST',
  });
}

/**
 * Remove an ignore record from an artifact pair.
 *
 * After this call the pair will re-appear in cluster results once the cache
 * expires (or is invalidated).
 */
async function deleteIgnorePair(pairId: string): Promise<void> {
  return apiRequest<void>(`/artifacts/consolidation/pairs/${encodeURIComponent(pairId)}/ignore`, {
    method: 'DELETE',
  });
}

// ============================================================================
// Hook: useSimilaritySettings
// ============================================================================

/**
 * Read and mutate similarity threshold and color settings.
 *
 * Provides graceful degradation: when the API is unavailable the hook
 * returns the built-in defaults so the UI renders correctly without errors.
 *
 * Stale time: 5 minutes (standard browsing tier — settings change rarely).
 * Cache time: 10 minutes (keep entries warm between navigations).
 *
 * Mutations apply optimistic updates immediately, then reconcile with the
 * server response (or roll back on error).
 *
 * @returns An object with resolved thresholds, colors, loading state, and
 *          async mutation functions for each settings group.
 *
 * @example
 * ```tsx
 * function SimilaritySettingsPanel() {
 *   const {
 *     thresholds,
 *     colors,
 *     isLoading,
 *     updateThresholds,
 *     updateColors,
 *   } = useSimilaritySettings();
 *
 *   return (
 *     <form>
 *       <input
 *         type="range" min={0} max={1} step={0.01}
 *         value={thresholds.high}
 *         onChange={e => updateThresholds({ high: Number(e.target.value) })}
 *       />
 *       <input
 *         type="color"
 *         value={colors.high}
 *         onChange={e => updateColors({ high: e.target.value })}
 *       />
 *     </form>
 *   );
 * }
 * ```
 */
export function useSimilaritySettings() {
  const queryClient = useQueryClient();

  // ------------------------------------------------------------------
  // Base query
  // ------------------------------------------------------------------

  const query = useQuery<SimilaritySettings, Error>({
    queryKey: similaritySettingsKeys.settings(),
    queryFn: fetchSimilaritySettings,
    staleTime: 5 * 60 * 1000,   // 5 minutes — config browsing tier
    gcTime: 10 * 60 * 1000,     // 10 minutes — keep warm between navigations
    retry: 1,                   // single retry on transient failure
    // Provide built-in defaults so the UI is always functional
    placeholderData: {
      thresholds: DEFAULT_THRESHOLDS,
      colors: DEFAULT_COLORS,
    },
  });

  // Resolved values — fall back to defaults when the query errors or is empty
  const thresholds: SimilarityThresholds =
    query.data?.thresholds ?? DEFAULT_THRESHOLDS;
  const colors: SimilarityColors =
    query.data?.colors ?? DEFAULT_COLORS;

  // ------------------------------------------------------------------
  // Threshold mutation
  // ------------------------------------------------------------------

  const thresholdsMutation = useMutation<
    SimilarityThresholds,
    Error,
    Partial<SimilarityThresholds>
  >({
    mutationFn: patchSimilarityThresholds,

    // Optimistic update: merge the incoming partial into the cached settings
    onMutate: async (incoming) => {
      // Cancel any in-flight reads to prevent them overwriting the optimistic state
      await queryClient.cancelQueries({
        queryKey: similaritySettingsKeys.settings(),
      });

      // Snapshot the current cache value for rollback
      const previous = queryClient.getQueryData<SimilaritySettings>(
        similaritySettingsKeys.settings()
      );

      // Apply optimistic merge
      queryClient.setQueryData<SimilaritySettings>(
        similaritySettingsKeys.settings(),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            thresholds: { ...old.thresholds, ...incoming },
          };
        }
      );

      return { previous };
    },

    // On success, sync the server-confirmed value into the cache
    onSuccess: (updatedThresholds) => {
      queryClient.setQueryData<SimilaritySettings>(
        similaritySettingsKeys.settings(),
        (old) => {
          if (!old) return old;
          return { ...old, thresholds: updatedThresholds };
        }
      );
    },

    // On error, roll back to the snapshot
    onError: (_err, _incoming, context) => {
      const ctx = context as { previous?: SimilaritySettings } | undefined;
      if (ctx?.previous !== undefined) {
        queryClient.setQueryData(similaritySettingsKeys.settings(), ctx.previous);
      }
    },

    // Always re-sync from the server to guarantee consistency
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: similaritySettingsKeys.settings(),
      });
    },
  });

  // ------------------------------------------------------------------
  // Colors mutation
  // ------------------------------------------------------------------

  const colorsMutation = useMutation<
    SimilarityColors,
    Error,
    Partial<SimilarityColors>
  >({
    mutationFn: patchSimilarityColors,

    onMutate: async (incoming) => {
      await queryClient.cancelQueries({
        queryKey: similaritySettingsKeys.settings(),
      });

      const previous = queryClient.getQueryData<SimilaritySettings>(
        similaritySettingsKeys.settings()
      );

      queryClient.setQueryData<SimilaritySettings>(
        similaritySettingsKeys.settings(),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            colors: { ...old.colors, ...incoming },
          };
        }
      );

      return { previous };
    },

    onSuccess: (updatedColors) => {
      queryClient.setQueryData<SimilaritySettings>(
        similaritySettingsKeys.settings(),
        (old) => {
          if (!old) return old;
          return { ...old, colors: updatedColors };
        }
      );
    },

    onError: (_err, _incoming, context) => {
      const ctx = context as { previous?: SimilaritySettings } | undefined;
      if (ctx?.previous !== undefined) {
        queryClient.setQueryData(similaritySettingsKeys.settings(), ctx.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: similaritySettingsKeys.settings(),
      });
    },
  });

  // ------------------------------------------------------------------
  // Public surface
  // ------------------------------------------------------------------

  return {
    /** Current similarity score thresholds (falls back to defaults on error) */
    thresholds,
    /** Current score-band colors (falls back to defaults on error) */
    colors,
    /** True while the initial settings fetch is in flight */
    isLoading: query.isLoading,
    /** True during any background refetch */
    isFetching: query.isFetching,
    /** Query error, if any */
    error: query.error,
    /**
     * Partially update similarity thresholds.
     *
     * Applies an optimistic update immediately and reconciles with the
     * server response.  Rolls back on error.
     *
     * @param values - Subset of threshold fields to update
     */
    updateThresholds: (values: Partial<SimilarityThresholds>): Promise<void> =>
      thresholdsMutation.mutateAsync(values).then(() => undefined),
    /**
     * Partially update similarity score-band colors.
     *
     * Applies an optimistic update immediately and reconciles with the
     * server response.  Rolls back on error.
     *
     * @param values - Subset of color fields to update
     */
    updateColors: (values: Partial<SimilarityColors>): Promise<void> =>
      colorsMutation.mutateAsync(values).then(() => undefined),
    /** Whether a threshold update is in progress */
    isUpdatingThresholds: thresholdsMutation.isPending,
    /** Whether a color update is in progress */
    isUpdatingColors: colorsMutation.isPending,
    /** Manually trigger a fresh fetch */
    refetch: query.refetch,
  };
}

// ============================================================================
// Hook: useConsolidationClusters
// ============================================================================

/** Default page size for cluster pagination */
const CLUSTERS_PAGE_SIZE = 20;

/**
 * Fetch consolidation clusters with cursor-based infinite scroll pagination.
 *
 * Clusters group similar artifacts that exceed the configured `minScore`
 * threshold.  Each page returns up to 20 clusters; call `fetchNextPage()`
 * when the user scrolls to the bottom of the list.
 *
 * Stale time: 30 seconds (interactive/monitoring tier — cluster data changes
 * as pairs are ignored and new artifacts are added).
 * Cache time: 5 minutes (keep entries warm while the panel is open).
 *
 * @param options.minScore - Minimum pairwise score to include (0.0–1.0)
 *
 * @example
 * ```tsx
 * function ConsolidationPanel() {
 *   const {
 *     clusters,
 *     fetchNextPage,
 *     hasNextPage,
 *     isFetchingNextPage,
 *     isLoading,
 *   } = useConsolidationClusters({ minScore: 0.75 });
 *
 *   return (
 *     <div>
 *       {clusters.map(cluster => (
 *         <ClusterCard key={cluster.cluster_id} cluster={cluster} />
 *       ))}
 *       {hasNextPage && (
 *         <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
 *           {isFetchingNextPage ? 'Loading…' : 'Load more'}
 *         </button>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useConsolidationClusters(options?: ConsolidationClustersOptions) {
  const { minScore } = options ?? {};

  const query = useInfiniteQuery({
    queryKey: consolidationKeys.clusters(minScore),
    queryFn: async ({ pageParam }): Promise<ConsolidationClustersResponse> => {
      return fetchConsolidationClusters(minScore, CLUSTERS_PAGE_SIZE, pageParam as string | undefined);
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: ConsolidationClustersResponse) =>
      lastPage.next_cursor ?? undefined,
    staleTime: 30 * 1000,        // 30s — interactive/monitoring tier
    gcTime: 5 * 60 * 1000,       // 5 minutes
    retry: 1,
  });

  // Flatten all pages into a single cluster array for convenient consumption
  const clusters: ConsolidationCluster[] =
    query.data?.pages.flatMap((page) => page.items) ?? [];

  // Total count from the first page (stable across page loads)
  const total: number = query.data?.pages[0]?.total ?? 0;

  return {
    /** All clusters fetched so far (flattened across pages) */
    clusters,
    /** Total cluster count reported by the server */
    total,
    /** Raw pages data for consumers that need per-page access */
    pages: query.data?.pages,
    /** True while the initial page fetch is in flight */
    isLoading: query.isLoading,
    /** True during any background refetch (including subsequent pages) */
    isFetching: query.isFetching,
    /** True while an additional page is being fetched */
    isFetchingNextPage: query.isFetchingNextPage,
    /** True when another page is available to fetch */
    hasNextPage: query.hasNextPage,
    /** Fetch the next page of clusters */
    fetchNextPage: query.fetchNextPage,
    /** Query error, if any */
    error: query.error,
    /** Manually trigger a fresh fetch starting from the first page */
    refetch: query.refetch,
  };
}

// ============================================================================
// Hook: useIgnorePair
// ============================================================================

/**
 * Mutation to mark an artifact pair as ignored.
 *
 * Applies an optimistic update immediately: the targeted pair's `ignored`
 * flag is set to `true` in the cache before the network request completes.
 * On error the optimistic change is rolled back.
 *
 * Invalidates the full consolidation clusters query on settled so stale
 * cluster memberships are re-fetched.
 *
 * @example
 * ```tsx
 * const { mutate: ignorePair, isPending } = useIgnorePair();
 *
 * <button
 *   disabled={isPending}
 *   onClick={() => ignorePair({ pairId: pair.pair_id, minScore })}
 * >
 *   Ignore
 * </button>
 * ```
 */
export function useIgnorePair() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { pairId: string; minScore?: number }>({
    mutationFn: ({ pairId }) => postIgnorePair(pairId),

    onMutate: async ({ pairId, minScore }) => {
      // Cancel in-flight cluster fetches to avoid overwriting the optimistic state
      await queryClient.cancelQueries({
        queryKey: consolidationKeys.clusters(minScore),
      });

      // Snapshot for rollback
      const previousData = queryClient.getQueryData(
        consolidationKeys.clusters(minScore)
      );

      // Optimistically flip the pair's ignored flag to true
      queryClient.setQueryData(
        consolidationKeys.clusters(minScore),
        (old: { pages: ConsolidationClustersResponse[]; pageParams: unknown[] } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((cluster) => ({
                ...cluster,
                pairs: cluster.pairs.map((pair) =>
                  pair.pair_id === pairId ? { ...pair, ignored: true } : pair
                ),
              })),
            })),
          };
        }
      );

      return { previousData, minScore };
    },

    onError: (_err, _vars, context) => {
      const ctx = context as { previousData?: unknown; minScore?: number } | undefined;
      if (ctx?.previousData !== undefined) {
        queryClient.setQueryData(
          consolidationKeys.clusters(ctx.minScore),
          ctx.previousData
        );
      }
    },

    onSettled: (_data, _err, vars) => {
      queryClient.invalidateQueries({
        queryKey: consolidationKeys.clusters(vars.minScore),
      });
    },
  });
}

// ============================================================================
// Hook: useUnignorePair
// ============================================================================

/**
 * Mutation to remove an ignore record from an artifact pair.
 *
 * Applies an optimistic update immediately: the targeted pair's `ignored`
 * flag is set to `false` in the cache before the network request completes.
 * On error the optimistic change is rolled back.
 *
 * Invalidates the full consolidation clusters query on settled so the
 * pair re-appears in cluster results.
 *
 * @example
 * ```tsx
 * const { mutate: unignorePair, isPending } = useUnignorePair();
 *
 * <button
 *   disabled={isPending}
 *   onClick={() => unignorePair({ pairId: pair.pair_id, minScore })}
 * >
 *   Restore
 * </button>
 * ```
 */
export function useUnignorePair() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { pairId: string; minScore?: number }>({
    mutationFn: ({ pairId }) => deleteIgnorePair(pairId),

    onMutate: async ({ pairId, minScore }) => {
      await queryClient.cancelQueries({
        queryKey: consolidationKeys.clusters(minScore),
      });

      const previousData = queryClient.getQueryData(
        consolidationKeys.clusters(minScore)
      );

      // Optimistically flip the pair's ignored flag to false
      queryClient.setQueryData(
        consolidationKeys.clusters(minScore),
        (old: { pages: ConsolidationClustersResponse[]; pageParams: unknown[] } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((cluster) => ({
                ...cluster,
                pairs: cluster.pairs.map((pair) =>
                  pair.pair_id === pairId ? { ...pair, ignored: false } : pair
                ),
              })),
            })),
          };
        }
      );

      return { previousData, minScore };
    },

    onError: (_err, _vars, context) => {
      const ctx = context as { previousData?: unknown; minScore?: number } | undefined;
      if (ctx?.previousData !== undefined) {
        queryClient.setQueryData(
          consolidationKeys.clusters(ctx.minScore),
          ctx.previousData
        );
      }
    },

    onSettled: (_data, _err, vars) => {
      queryClient.invalidateQueries({
        queryKey: consolidationKeys.clusters(vars.minScore),
      });
    },
  });
}
