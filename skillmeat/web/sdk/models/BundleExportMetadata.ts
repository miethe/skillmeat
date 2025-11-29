/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Metadata for bundle export.
 */
export type BundleExportMetadata = {
  /**
   * Bundle name (identifier, alphanumeric + dash/underscore)
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
   * Bundle version (semver recommended)
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
