/**
 * Marketplace Types for SkillMeat
 *
 * These types represent marketplace listings, filters, and operations
 */

export type ArtifactCategory = "skill" | "command" | "agent" | "hook" | "mcp-server" | "bundle";

export type ListingSortOrder = "newest" | "popular" | "updated" | "name" | "downloads";

export interface Publisher {
  name: string;
  email?: string;
  website?: string;
  verified: boolean;
  avatar_url?: string;
}

export interface Listing {
  listing_id: string;
  name: string;
  description: string;
  category: ArtifactCategory;
  version: string;
  publisher: Publisher;
  license: string;
  tags: string[];
  artifact_count: number;
  downloads: number;
  created_at: string;
  updated_at: string;
  homepage?: string;
  repository?: string;
}

export interface ListingDetail extends Listing {
  source_url: string;
  bundle_url: string;
  price: number;
  signature?: string;
}

export interface MarketplaceFilters {
  tags?: string[];
  license?: string;
  publisher?: string;
  artifact_type?: ArtifactCategory;
  search?: string;
  free_only?: boolean;
  verified_only?: boolean;
}

export interface PageInfo {
  has_next_page: boolean;
  has_previous_page: boolean;
  start_cursor?: string | null;
  end_cursor?: string | null;
  total_count: number;
}

export interface ListingsResponse {
  items: Listing[];
  page_info: PageInfo;
}

export interface InstallRequest {
  listing_id: string;
  collection_name?: string;
  verify_signature?: boolean;
}

export interface InstallResponse {
  success: boolean;
  listing_id: string;
  artifacts_installed: number;
  collection_name: string;
  message: string;
  errors?: string[];
  warnings?: string[];
}

export interface PublishRequest {
  bundle_path: string;
  name: string;
  description: string;
  category: ArtifactCategory;
  version: string;
  license: string;
  tags: string[];
  homepage?: string;
  repository?: string;
  price?: number;
  sign_bundle?: boolean;
  publisher_key_id?: string;
}

export interface PublishResponse {
  success: boolean;
  listing_id?: string;
  listing_url?: string;
  message: string;
  errors?: string[];
  warnings?: string[];
}
