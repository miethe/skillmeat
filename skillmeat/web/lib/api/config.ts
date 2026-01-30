/**
 * Configuration API service functions
 *
 * Provides functions for fetching backend configuration data
 * including artifact detection patterns.
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
