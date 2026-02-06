/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Bundle metadata response.
 */
export type BundleMetadataResponse = {
  /**
   * Bundle name (identifier)
   */
  name: string;
  /**
   * Human-readable description
   */
  description: string;
  /**
   * Author name or email
   */
  author: string;
  /**
   * ISO 8601 timestamp of bundle creation
   */
  created_at: string;
  /**
   * Bundle version
   */
  version?: string;
  /**
   * License identifier
   */
  license?: string;
  /**
   * Categorization tags
   */
  tags?: Array<string>;
  /**
   * Project homepage URL
   */
  homepage?: string | null;
  /**
   * Source repository URL
   */
  repository?: string | null;
};
