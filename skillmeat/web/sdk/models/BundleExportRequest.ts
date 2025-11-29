/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BundleExportMetadata } from './BundleExportMetadata';
import type { BundleExportOptions } from './BundleExportOptions';
/**
 * Request to export artifacts as a bundle.
 */
export type BundleExportRequest = {
  /**
   * List of artifact IDs to include (format: 'type::name')
   */
  artifact_ids: Array<string>;
  /**
   * Bundle metadata
   */
  metadata: BundleExportMetadata;
  /**
   * Export options
   */
  options?: BundleExportOptions;
  /**
   * Source collection (uses active if None)
   */
  collection_name?: string | null;
};
