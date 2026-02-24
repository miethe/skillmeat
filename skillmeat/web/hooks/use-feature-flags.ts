/**
 * React Query hook for fetching backend feature flags
 *
 * Feature flags control which UI sections are visible when the corresponding
 * backend feature is disabled. This hook fetches the canonical flag state from
 * the backend so the frontend stays in sync with server configuration.
 *
 * Caching strategy:
 * - 5-minute stale time (flags rarely change between deploys)
 * - 10-minute garbage collection time
 * - Single retry on failure
 * - Falls back to all-enabled defaults on error so the UI is never blocked
 *   when the config endpoint is temporarily unreachable
 */

import { useQuery } from '@tanstack/react-query';
import { getFeatureFlags, type FeatureFlagsResponse } from '@/lib/api/config';

// =============================================================================
// Defaults
// =============================================================================

/**
 * Default feature flag values used when the API is unreachable.
 *
 * All features default to enabled so the UI degrades gracefully — a missing
 * config endpoint should not hide features that are otherwise functional.
 */
export const DEFAULT_FEATURE_FLAGS: FeatureFlagsResponse = {
  composite_artifacts_enabled: true,
  deployment_sets_enabled: true,
  memory_context_enabled: true,
};

// =============================================================================
// Query Key Factory
// =============================================================================

export const featureFlagKeys = {
  all: ['feature-flags'] as const,
  flags: () => [...featureFlagKeys.all, 'flags'] as const,
};

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to fetch current backend feature flags
 *
 * Returns boolean flag values for each toggleable backend feature.
 * Components use these flags to conditionally render nav items, pages,
 * and UI elements that depend on backend feature availability.
 *
 * Falls back to all-enabled defaults on error to avoid blocking the UI.
 *
 * @returns Feature flags with convenience accessors and query state
 *
 * @example
 * ```tsx
 * const { deploymentSetsEnabled } = useFeatureFlags();
 *
 * if (!deploymentSetsEnabled) {
 *   return <FeatureDisabledMessage feature="Deployment Sets" />;
 * }
 * ```
 */
export function useFeatureFlags() {
  const query = useQuery({
    queryKey: featureFlagKeys.flags(),
    queryFn: getFeatureFlags,
    staleTime: 5 * 60 * 1000, // 5 minutes — flags are stable between deploys
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
    retry: 1, // Only retry once on failure
  });

  // Use API response if available, fall back to defaults for graceful degradation
  const flags = query.data ?? DEFAULT_FEATURE_FLAGS;

  return {
    /** Whether composite artifact detection is enabled */
    compositeArtifactsEnabled: flags.composite_artifacts_enabled,
    /**
     * Whether the deployment sets feature is enabled.
     * When false, /api/v1/deployment-sets endpoints return 404.
     */
    deploymentSetsEnabled: flags.deployment_sets_enabled,
    /** Whether the Memory & Context Intelligence System is enabled */
    memoryContextEnabled: flags.memory_context_enabled,
    /** Raw flags object from the API */
    flags,
    /** Whether the initial query is loading */
    isLoading: query.isLoading,
    /** Query error if any */
    error: query.error,
    /** Whether flag values were loaded from the API (vs defaults) */
    isFromApi: !!query.data,
  };
}

export type { FeatureFlagsResponse };
