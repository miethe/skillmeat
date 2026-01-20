/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Marketplace entry information.
 *
 * Attributes:
 * id: Entry ID
 * name: Artifact name
 * type: Artifact type
 * url: URL to artifact
 * description: Entry description
 * cached_at: When entry was cached
 * data: Additional marketplace data (publisher, license, tags, etc.)
 */
export type MarketplaceEntryResponse = {
  /**
   * Marketplace entry ID
   */
  id: string;
  /**
   * Artifact name
   */
  name: string;
  /**
   * Artifact type
   */
  type: string;
  /**
   * URL to artifact
   */
  url: string;
  /**
   * Entry description
   */
  description?: string | null;
  /**
   * When entry was cached
   */
  cached_at: string;
  /**
   * Additional marketplace data
   */
  data?: Record<string, any> | null;
};
