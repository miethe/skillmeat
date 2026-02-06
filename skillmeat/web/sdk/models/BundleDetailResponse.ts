/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BundleArtifactSummary } from './BundleArtifactSummary';
import type { BundleMetadataResponse } from './BundleMetadataResponse';
/**
 * Detailed bundle information response.
 */
export type BundleDetailResponse = {
  /**
   * Bundle unique identifier (hash)
   */
  bundle_id: string;
  /**
   * Bundle metadata
   */
  metadata: BundleMetadataResponse;
  /**
   * List of artifacts in bundle
   */
  artifacts: Array<BundleArtifactSummary>;
  /**
   * List of bundle dependencies
   */
  dependencies?: Array<string>;
  /**
   * SHA-256 hash of bundle
   */
  bundle_hash: string;
  /**
   * Total bundle size in bytes
   */
  total_size_bytes: number;
  /**
   * Total number of files in bundle
   */
  total_files: number;
  /**
   * Bundle source (created, imported, or marketplace)
   */
  source: string;
  /**
   * ISO 8601 timestamp when bundle was imported
   */
  imported_at?: string | null;
  /**
   * Local path to bundle file if available
   */
  bundle_path?: string | null;
};
