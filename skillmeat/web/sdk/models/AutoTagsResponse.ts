/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AutoTagSegment } from './AutoTagSegment';
/**
 * Response containing all auto-tags for a marketplace source.
 *
 * Returns extracted GitHub topics with their approval status and metadata.
 */
export type AutoTagsResponse = {
  /**
   * Marketplace source ID
   */
  source_id: string;
  /**
   * List of extracted auto-tags with status
   */
  segments: Array<AutoTagSegment>;
  /**
   * Whether any tags are still pending approval
   */
  has_pending: boolean;
};
