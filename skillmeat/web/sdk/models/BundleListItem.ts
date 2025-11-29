/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single bundle in list response.
 */
export type BundleListItem = {
  /**
   * Bundle unique identifier (hash)
   */
  bundle_id: string;
  /**
   * Bundle name
   */
  name: string;
  /**
   * Bundle description
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
   * Number of artifacts in bundle
   */
  artifact_count: number;
  /**
   * Total bundle size in bytes
   */
  total_size_bytes: number;
  /**
   * Bundle source (created, imported, or marketplace)
   */
  source: string;
  /**
   * ISO 8601 timestamp when bundle was imported (if applicable)
   */
  imported_at?: string | null;
  /**
   * Categorization tags
   */
  tags?: Array<string>;
};
