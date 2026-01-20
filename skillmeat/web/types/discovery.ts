/**
 * Type definitions for discovery feature
 *
 * These types support artifact discovery, bulk import, GitHub metadata fetch,
 * and parameter update operations.
 */

/**
 * Match type for collection membership check
 */
export type MatchType = 'exact' | 'hash' | 'name_type' | 'none';

/**
 * Collection membership status for a discovered artifact
 */
export interface CollectionStatus {
  /** Whether the artifact exists in the collection */
  in_collection: boolean;
  /** How the artifact was matched: exact, hash, name_type, or none */
  match_type: MatchType;
  /** ID of the matched artifact in collection (format: type:name) */
  matched_artifact_id: string | null;
}

/**
 * Hash-based collection matching result for a discovered artifact.
 *
 * Provides detailed information about how an artifact matches against
 * the collection using content hash and name+type matching.
 */
export interface CollectionMatch {
  /**
   * Match type:
   * - "exact": Content hash exact match (confidence: 1.0)
   * - "hash": Legacy alias for exact hash match (confidence: 1.0)
   * - "name_type": Name and type match but different content (confidence: 0.85)
   * - "none": No match found (confidence: 0.0)
   */
  type: MatchType;
  /** ID of matched artifact in collection (format: type:name) */
  matched_artifact_id: string | null;
  /** Name of the matched artifact */
  matched_name: string | null;
  /** Confidence score from 0.0 (no match) to 1.0 (exact hash match) */
  confidence: number;
}

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
  /** ISO 8601 timestamp when artifact was discovered */
  discovered_at: string;
  /** SHA256 content hash of the artifact for deduplication */
  content_hash?: string;
  /** Collection membership status (null if not checked) */
  collection_status?: CollectionStatus | null;
  /** Hash-based collection matching result (populated when collection context is provided) */
  collection_match?: CollectionMatch | null;
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
export type ImportStatus = 'success' | 'skipped' | 'failed';

/**
 * Error reason codes matching backend ErrorReasonCode enum
 */
export type ErrorReasonCode =
  | 'invalid_structure'
  | 'yaml_parse_error'
  | 'missing_metadata'
  | 'invalid_type'
  | 'invalid_source'
  | 'import_error'
  | 'network_error'
  | 'permission_error'
  | 'io_error'
  | 'already_exists'
  | 'in_skip_list'
  | 'duplicate';

/**
 * Result for a single import operation
 * Updated to match backend schema with status-based approach
 */
export interface ImportResult {
  /** Artifact ID (format: type:name) */
  artifact_id: string;
  /** Path to the artifact (for local imports) */
  path?: string;
  /** Import status: success, skipped, or failed */
  status: ImportStatus;
  /** Human-readable result message */
  message: string;
  /** Error message (if status=failed) */
  error?: string;
  /** Machine-readable reason code for failures/skips */
  reason_code?: ErrorReasonCode | null;
  /** Reason artifact was skipped (if status=skipped) */
  skip_reason?: string;
  /** Additional error details (e.g., line numbers for YAML errors) */
  details?: string | null;
  /** Number of path-based tags applied during import */
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
  artifact_key: string; // Format: "type:name" e.g., "skill:canvas-design"
  skip_reason: string;
  added_date: string; // ISO 8601 datetime string
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

/**
 * Map error reason codes to user-friendly messages
 */
export function getReasonCodeMessage(reasonCode: ErrorReasonCode | null | undefined): string {
  if (!reasonCode) return 'Unknown reason';

  const messages: Record<ErrorReasonCode, string> = {
    invalid_structure: 'Invalid artifact structure',
    yaml_parse_error: 'Invalid YAML syntax',
    missing_metadata: 'Missing required metadata',
    invalid_type: 'Invalid artifact type',
    invalid_source: 'Invalid source format',
    import_error: 'Import failed',
    network_error: 'Network error',
    permission_error: 'Permission denied',
    io_error: 'File I/O error',
    already_exists: 'Already exists in collection',
    in_skip_list: 'Marked to skip',
    duplicate: 'Duplicate in batch',
  };

  return messages[reasonCode] || 'Unknown error';
}

// ===========================
// Duplicate Confirmation Types (P2)
// ===========================

/**
 * Action to take for a duplicate match
 */
export type DuplicateDecisionAction = 'link' | 'skip';

/**
 * A single duplicate match decision from the user
 */
export interface DuplicateMatch {
  /** Full filesystem path to the discovered artifact */
  discovered_path: string;
  /** ID of the matching collection artifact (format: type:name) */
  collection_artifact_id: string;
  /** Action to take: 'link' to create association, 'skip' to ignore */
  action: DuplicateDecisionAction;
}

/**
 * Request to process duplicate review decisions
 */
export interface ConfirmDuplicatesRequest {
  /** Absolute path to the project being scanned */
  project_path: string;
  /** Duplicate artifacts to link to collection entries */
  matches: DuplicateMatch[];
  /** Filesystem paths of artifacts to import as new */
  new_artifacts: string[];
  /** Filesystem paths of artifacts the user chose to skip */
  skipped: string[];
}

/**
 * Status of duplicate confirmation operation
 */
export type ConfirmDuplicatesStatus = 'success' | 'partial' | 'failed';

/**
 * Response from processing duplicate review decisions
 */
export interface ConfirmDuplicatesResponse {
  /** Overall status: 'success', 'partial', or 'failed' */
  status: ConfirmDuplicatesStatus;
  /** Number of artifacts successfully linked to collection entries */
  linked_count: number;
  /** Number of new artifacts successfully imported */
  imported_count: number;
  /** Number of artifacts marked as skipped */
  skipped_count: number;
  /** Human-readable summary message */
  message: string;
  /** ISO 8601 timestamp of when the operation completed */
  timestamp: string;
  /** List of error messages for failed operations */
  errors: string[];
}
