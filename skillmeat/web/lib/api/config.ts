/**
 * Configuration API service functions
 *
 * Provides functions for fetching backend configuration data
 * including artifact detection patterns and feature flags.
 */

import { apiRequest } from '@/lib/api';

/**
 * Detection patterns response from the API
 *
 * Contains all the configuration needed for frontend artifact detection:
 * - container_aliases: Maps artifact types to valid container directory names
 * - leaf_containers: Flattened list of all container names for quick lookups
 * - canonical_containers: Maps artifact types to preferred container names
 */
export interface DetectionPatternsResponse {
  /** Maps artifact type (e.g., 'skill') to valid container names (e.g., ['skills', 'skill']) */
  container_aliases: Record<string, string[]>;
  /** Flattened list of all valid container directory names */
  leaf_containers: string[];
  /** Maps artifact type to its canonical/preferred container name */
  canonical_containers: Record<string, string>;
}

/**
 * Feature flags response from the API
 *
 * Reflects current backend feature flag state so the frontend can
 * conditionally render features that depend on backend capabilities.
 */
export interface FeatureFlagsResponse {
  /** Whether composite artifact detection is enabled */
  composite_artifacts_enabled: boolean;
  /**
   * Whether the deployment sets feature is enabled.
   * When false, all /api/v1/deployment-sets endpoints return 404.
   */
  deployment_sets_enabled: boolean;
  /** Whether the Memory & Context Intelligence System is enabled */
  memory_context_enabled: boolean;
}

/**
 * Fetch artifact detection patterns from the backend
 *
 * Returns the centralized detection patterns used by the Python backend,
 * allowing frontend applications to perform consistent artifact detection.
 *
 * @returns Detection patterns including container aliases and leaf containers
 * @throws ApiError if the request fails
 *
 * @example
 * ```typescript
 * const patterns = await getDetectionPatterns();
 * const isLeafContainer = patterns.leaf_containers.includes('skills');
 * ```
 */
export async function getDetectionPatterns(): Promise<DetectionPatternsResponse> {
  return apiRequest<DetectionPatternsResponse>('/config/detection-patterns');
}

/**
 * Fetch current backend feature flags
 *
 * Returns boolean flag values for each toggleable backend feature.
 * The frontend uses these flags to conditionally show/hide nav items,
 * pages, and UI elements that depend on backend feature availability.
 *
 * @returns Feature flags object with boolean values
 * @throws ApiError if the request fails
 *
 * @example
 * ```typescript
 * const flags = await getFeatureFlags();
 * if (flags.deployment_sets_enabled) {
 *   // render deployment sets UI
 * }
 * ```
 */
export async function getFeatureFlags(): Promise<FeatureFlagsResponse> {
  return apiRequest<FeatureFlagsResponse>('/config/feature-flags');
}
