/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BundleMetadataResponse } from './BundleMetadataResponse';
import type { BundlePreviewCategorization } from './BundlePreviewCategorization';
import type { PreviewArtifact } from './PreviewArtifact';
import type { ValidationIssueResponse } from './ValidationIssueResponse';
/**
 * Response from bundle preview operation.
 */
export type BundlePreviewResponse = {
  /**
   * Whether bundle is valid
   */
  is_valid: boolean;
  /**
   * SHA-256 hash of bundle
   */
  bundle_hash?: string | null;
  /**
   * Bundle metadata from manifest
   */
  metadata?: BundleMetadataResponse | null;
  /**
   * List of artifacts in bundle with conflict information
   */
  artifacts?: Array<PreviewArtifact>;
  /**
   * Categorization summary of artifacts
   */
  categorization: BundlePreviewCategorization;
  /**
   * Validation issues (errors and warnings)
   */
  validation_issues?: Array<ValidationIssueResponse>;
  /**
   * Total bundle size in bytes
   */
  total_size_bytes?: number;
  /**
   * Name of collection that would receive imports
   */
  collection_name: string;
  /**
   * Human-readable summary
   */
  summary?: string;
};
