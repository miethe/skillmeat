/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BundleMetadataResponse } from './BundleMetadataResponse';
/**
 * Response from bundle export operation.
 */
export type BundleExportResponse = {
  /**
   * Whether export succeeded
   */
  success: boolean;
  /**
   * Bundle unique identifier (SHA-256 hash)
   */
  bundle_id: string;
  /**
   * Path to exported bundle file
   */
  bundle_path: string;
  /**
   * URL to download the bundle
   */
  download_url: string;
  /**
   * Shareable link if generate_share_link was True
   */
  share_link?: string | null;
  /**
   * SSE stream URL for progress updates
   */
  stream_url?: string | null;
  /**
   * Bundle metadata
   */
  metadata: BundleMetadataResponse;
  /**
   * Number of artifacts in bundle
   */
  artifact_count: number;
  /**
   * Total bundle size in bytes
   */
  total_size_bytes: number;
  /**
   * Warning messages
   */
  warnings?: Array<string>;
  /**
   * Timestamp of export operation
   */
  export_time: string;
};
