/**
 * React Query hooks for similarity settings (thresholds and score-band colors).
 *
 * Reads and mutates the settings that control how similarity scores are
 * classified and displayed across the Similar Artifacts tab.
 *
 * Endpoints:
 *   GET  /api/v1/settings/similarity              → current thresholds + colors
 *   PUT  /api/v1/settings/similarity/thresholds   → partial threshold update
 *   PUT  /api/v1/settings/similarity/colors       → partial color update
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

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type {
  SimilaritySettings,
  SimilarityThresholds,
  SimilarityColors,
} from '@/types/similarity';

// Re-export types so consumers can import from the hook module directly
export type { SimilarityThresholds, SimilarityColors, SimilaritySettings };

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
// Query Key Factory
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

// ============================================================================
// API Functions
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
// Hook
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
