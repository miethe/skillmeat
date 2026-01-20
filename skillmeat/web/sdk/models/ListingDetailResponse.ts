/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Detailed response model for a single marketplace listing.
 *
 * Includes all available metadata for a listing, including bundle URL
 * and signature information.
 */
export type ListingDetailResponse = {
  /**
   * Unique identifier for the listing
   */
  listing_id: string;
  /**
   * Human-readable name of the bundle
   */
  name: string;
  /**
   * Publisher name or organization
   */
  publisher: string;
  /**
   * License identifier
   */
  license: string;
  /**
   * Number of artifacts in the bundle
   */
  artifact_count: number;
  /**
   * Tags for categorization
   */
  tags?: Array<string>;
  /**
   * Timestamp when listing was created
   */
  created_at: string;
  /**
   * URL to listing details page
   */
  source_url: string;
  /**
   * URL to download the bundle file
   */
  bundle_url: string;
  /**
   * Base64-encoded Ed25519 signature
   */
  signature: string;
  /**
   * Optional detailed description
   */
  description?: string | null;
  /**
   * Optional version string
   */
  version?: string | null;
  /**
   * Optional URL to project homepage
   */
  homepage?: string | null;
  /**
   * Optional URL to source repository
   */
  repository?: string | null;
  /**
   * Download count
   */
  downloads?: number | null;
  /**
   * Rating from 0.0 to 5.0
   */
  rating?: number | null;
  /**
   * Price in cents (0 for free)
   */
  price?: number;
};
