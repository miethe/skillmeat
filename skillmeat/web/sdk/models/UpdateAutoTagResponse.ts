/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AutoTagSegment } from './AutoTagSegment';
/**
 * Response after updating an auto-tag's approval status.
 *
 * Returns the updated tag and any tags that were added to the source.
 */
export type UpdateAutoTagResponse = {
  /**
   * Marketplace source ID
   */
  source_id: string;
  /**
   * The updated auto-tag segment
   */
  updated_tag: AutoTagSegment;
  /**
   * Tags added to source.tags if approved
   */
  tags_added: Array<string>;
};
