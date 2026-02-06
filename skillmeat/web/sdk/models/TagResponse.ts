/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for a single tag.
 *
 * Provides complete tag information including metadata
 * and optional artifact count for list views.
 */
export type TagResponse = {
  /**
   * Tag unique identifier
   */
  id: string;
  /**
   * Tag name
   */
  name: string;
  /**
   * URL-friendly slug
   */
  slug: string;
  /**
   * Hex color code
   */
  color?: string | null;
  /**
   * Timestamp when tag was created
   */
  created_at: string;
  /**
   * Timestamp of last update
   */
  updated_at: string;
  /**
   * Number of artifacts with this tag (included when fetching list)
   */
  artifact_count?: number | null;
};
