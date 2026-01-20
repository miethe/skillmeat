/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for a single user collection.
 *
 * Provides complete collection metadata including counts.
 */
export type UserCollectionResponse = {
  /**
   * Collection unique identifier
   */
  id: string;
  /**
   * Collection name
   */
  name: string;
  /**
   * Collection description
   */
  description?: string | null;
  /**
   * User identifier (for future multi-user support)
   */
  created_by?: string | null;
  /**
   * Collection type
   */
  collection_type?: string | null;
  /**
   * Context category
   */
  context_category?: string | null;
  /**
   * Collection creation timestamp
   */
  created_at: string;
  /**
   * Last update timestamp
   */
  updated_at: string;
  /**
   * Number of groups in collection
   */
  group_count: number;
  /**
   * Total number of artifacts in collection
   */
  artifact_count: number;
};
