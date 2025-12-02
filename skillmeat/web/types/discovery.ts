/**
 * Type definitions for discovery feature
 *
 * These types support artifact discovery, bulk import, GitHub metadata fetch,
 * and parameter update operations.
 */

/**
 * Discovered artifact from scanning
 */
export interface DiscoveredArtifact {
  type: string;
  name: string;
  source?: string;
  version?: string;
  scope?: string;
  tags?: string[];
  description?: string;
  path: string;
  discovered_at: string;
}

/**
 * Result from discovery scan operation
 */
export interface DiscoveryResult {
  discovered_count: number;
  artifacts: DiscoveredArtifact[];
  errors: string[];
  scan_duration_ms: number;
}

/**
 * Single artifact for bulk import
 */
export interface BulkImportArtifact {
  source: string;
  artifact_type: string;
  name?: string;
  description?: string;
  author?: string;
  tags?: string[];
  scope?: string;
  path?: string;
}

/**
 * Request payload for bulk import
 */
export interface BulkImportRequest {
  artifacts: BulkImportArtifact[];
  auto_resolve_conflicts?: boolean;
}

/**
 * Result for a single import operation
 */
export interface ImportResult {
  artifact_id: string;
  success: boolean;
  message: string;
  error?: string;
}

/**
 * Response from bulk import operation
 */
export interface BulkImportResult {
  total_requested: number;
  total_imported: number;
  total_failed: number;
  results: ImportResult[];
  duration_ms: number;
}

/**
 * GitHub metadata from API
 */
export interface GitHubMetadata {
  title?: string;
  description?: string;
  author?: string;
  license?: string;
  topics: string[];
  url: string;
  fetched_at: string;
}

/**
 * Response from GitHub metadata fetch
 */
export interface GitHubMetadataResponse {
  success: boolean;
  metadata?: GitHubMetadata;
  error?: string;
}

/**
 * Artifact parameters that can be updated
 */
export interface ArtifactParameters {
  source?: string;
  version?: string;
  scope?: string;
  tags?: string[];
  aliases?: string[];
}

/**
 * Response from parameter update operation
 */
export interface ParameterUpdateResponse {
  success: boolean;
  artifact_id: string;
  updated_fields: string[];
  message: string;
}
