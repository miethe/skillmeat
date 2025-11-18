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
  strategy: "merge" | "fork" | "skip";
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
  status: "pending" | "approved" | "rejected";
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
