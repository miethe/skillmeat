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
  importable_count: number;
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
  skip_list?: string[];
  apply_path_tags?: boolean;
}

/**
 * Import status enum matching backend
 */
export type ImportStatus = "success" | "skipped" | "failed";

/**
 * Result for a single import operation
 * Updated to match backend schema with status-based approach
 */
export interface ImportResult {
  artifact_id: string;
  status: ImportStatus;
  message: string;
  error?: string;
  skip_reason?: string;
  tags_applied?: number;
}

/**
 * Response from bulk import operation
 * Updated to match backend schema with detailed counters
 */
export interface BulkImportResult {
  total_requested: number;
  total_imported: number;
  total_skipped: number;
  total_failed: number;
  imported_to_collection: number;
  added_to_project: number;
  results: ImportResult[];
  duration_ms: number;
  summary?: string;
  total_tags_applied?: number;
}

/**
 * Skip preference for artifacts that should not be imported
 * Used to persist user's decision to skip certain artifacts
 */
export interface SkipPreference {
  artifact_key: string;  // Format: "type:name" e.g., "skill:canvas-design"
  skip_reason: string;
  added_date: string;  // ISO 8601 datetime string
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
