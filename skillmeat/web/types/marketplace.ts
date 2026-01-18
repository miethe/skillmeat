/**
 * Marketplace Types for SkillMeat
 *
 * Types for browsing, installing, and publishing marketplace listings
 */

export interface MarketplaceListing {
  listing_id: string;
  name: string;
  publisher: string;
  license: string;
  artifact_count: number;
  tags: string[];
  created_at: string;
  source_url: string;
  description?: string;
  version?: string;
  downloads?: number;
  rating?: number;
  price: number; // 0 for free, otherwise price in cents
}

export interface MarketplaceListingDetail extends MarketplaceListing {
  bundle_url: string;
  signature: string;
  homepage?: string;
  repository?: string;
}

export interface MarketplaceFilters {
  broker?: string;
  query?: string;
  tags?: string[];
  license?: string;
  publisher?: string;
}

export interface PageInfo {
  has_next_page: boolean;
  has_previous_page: boolean;
  start_cursor?: string;
  end_cursor?: string;
  total_count: number;
}

export interface ListingsPageResponse {
  items: MarketplaceListing[];
  page_info: PageInfo;
}

export interface BrokerInfo {
  name: string;
  enabled: boolean;
  endpoint: string;
  supports_publish: boolean;
  description?: string;
}

export interface InstallRequest {
  listing_id: string;
  broker?: string;
  strategy: 'merge' | 'fork' | 'skip';
}

export interface InstallResponse {
  success: boolean;
  artifacts_imported: string[];
  message: string;
  listing_id: string;
  broker: string;
}

export interface PublishRequest {
  bundle_path: string;
  broker: string;
  metadata: {
    description?: string;
    tags?: string[];
    homepage?: string;
    repository?: string;
  };
}

export interface PublishResponse {
  submission_id: string;
  status: 'pending' | 'approved' | 'rejected';
  message: string;
  broker: string;
  listing_url?: string;
}

export interface PublishWizardStep {
  id: number;
  title: string;
  description: string;
}

export interface PublishFormData {
  bundle_id?: string;
  bundle_path?: string;
  broker?: string;
  description?: string;
  tags?: string[];
  homepage?: string;
  repository?: string;
}

// ============================================================================
// GitHub Source Management Types
// ============================================================================

export type TrustLevel = 'untrusted' | 'basic' | 'verified' | 'official';
export type ScanStatus = 'pending' | 'scanning' | 'success' | 'error';
export type CatalogStatus = 'new' | 'updated' | 'removed' | 'imported' | 'excluded';
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'mcp_server' | 'hook';

export interface GitHubSource {
  id: string;
  repo_url: string;
  owner: string;
  repo_name: string;
  ref: string;
  root_hint?: string;
  trust_level: TrustLevel;
  visibility: 'public' | 'private';
  scan_status: ScanStatus;
  artifact_count: number;
  last_sync_at?: string;
  last_error?: string;
  created_at: string;
  updated_at: string;
  description?: string;
  repo_description?: string; // GitHub repository description (fallback)
  notes?: string;
  enable_frontmatter_detection?: boolean;
  manual_map?: Record<string, string>; // Directory path -> artifact type
  tags?: string[]; // User-assigned tags for filtering
  counts_by_type?: Record<string, number>; // Artifact counts by type
}

export interface GitHubSourceListResponse {
  items: GitHubSource[];
  page_info: PageInfo;
}

export interface CreateSourceRequest {
  repo_url: string;
  ref?: string;
  root_hint?: string;
  access_token?: string;
  manual_map?: Record<string, string[]>;
  trust_level?: TrustLevel;
  description?: string;
  notes?: string;
  enable_frontmatter_detection?: boolean;
  import_repo_description?: boolean;
  import_repo_readme?: boolean;
  tags?: string[];
}

export interface UpdateSourceRequest {
  ref?: string;
  root_hint?: string;
  trust_level?: TrustLevel;
  manual_map?: Record<string, string[]>;
  description?: string;
  notes?: string;
  enable_frontmatter_detection?: boolean;
  import_repo_description?: boolean;
  import_repo_readme?: boolean;
  tags?: string[];
}

export interface CatalogEntry {
  id: string;
  source_id: string;
  artifact_type: ArtifactType;
  name: string;
  path: string;
  upstream_url: string;
  detected_version?: string;
  detected_sha?: string;
  detected_at: string;
  confidence_score: number;
  status: CatalogStatus;
  import_date?: string;
  import_id?: string;
  excluded_at?: string | null;
  excluded_reason?: string | null;
  raw_score?: number;
  score_breakdown?: {
    dir_name_score: number;
    manifest_score: number;
    extensions_score: number;
    parent_hint_score: number;
    frontmatter_score: number;
    skill_manifest_bonus: number;
    container_hint_score: number;
    frontmatter_type_score: number;
    depth_penalty: number;
    raw_total: number;
    normalized_score: number;
  };
  // Deduplication fields (Phase 3)
  is_duplicate?: boolean;
  duplicate_reason?: 'within_source' | 'cross_source';
  duplicate_of?: string; // Path of original artifact
  // Collection match field
  in_collection?: boolean;
}

export interface UpdateCatalogEntryNameRequest {
  name: string;
}

export interface CatalogListResponse {
  items: CatalogEntry[];
  page_info: PageInfo;
  counts_by_status: Record<string, number>;
  counts_by_type: Record<string, number>;
}

export interface CatalogFilters {
  artifact_type?: ArtifactType;
  status?: CatalogStatus;
  min_confidence?: number;
  max_confidence?: number;
  include_below_threshold?: boolean;
  search?: string;
  sort_by?: 'confidence' | 'name' | 'date';
  sort_order?: 'asc' | 'desc';
}

export interface ScanRequest {
  force?: boolean;
  manual_map?: Record<string, string>;
}

export interface ScanResult {
  source_id: string;
  status: 'success' | 'error' | 'partial';
  artifacts_found: number;
  new_count: number;
  updated_count: number;
  removed_count: number;
  unchanged_count: number;
  scan_duration_ms: number;
  errors: string[];
  scanned_at: string;
  // Deduplication statistics (Phase 3)
  duplicates_within_source?: number;
  duplicates_cross_source?: number;
  total_detected?: number;
  total_unique?: number;
  // Updated imports tracking
  updated_imports?: string[];
  preserved_count?: number;
}

export interface ImportRequest {
  entry_ids: string[];
  conflict_strategy: 'skip' | 'overwrite' | 'rename';
}

export interface ImportResult {
  imported_count: number;
  skipped_count: number;
  error_count: number;
  imported_ids: string[];
  skipped_ids: string[];
  errors: Array<{ entry_id: string; error: string }>;
}

export interface InferUrlResponse {
  success: boolean;
  repo_url: string | null;
  ref: string | null;
  root_hint: string | null;
  error: string | null;
}
