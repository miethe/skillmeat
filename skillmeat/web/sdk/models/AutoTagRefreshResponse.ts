/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AutoTagSegment } from './AutoTagSegment';
/**
 * Response from auto-tag refresh operation.
 *
 * Returns statistics about tags found and updated from GitHub topics.
 */
export type AutoTagRefreshResponse = {
  /**
   * Marketplace source ID
   */
  source_id: string;
  /**
   * Total number of GitHub topics found
   */
  tags_found: number;
  /**
   * Number of new tags added
   */
  tags_added: number;
  /**
   * Number of existing tags updated (status preserved)
   */
  tags_updated: number;
  /**
   * All auto-tags after refresh
   */
  segments: Array<AutoTagSegment>;
};
