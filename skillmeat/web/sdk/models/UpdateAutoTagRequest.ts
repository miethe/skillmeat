/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to update the approval status of an auto-tag.
 *
 * Used to approve or reject a GitHub topic for inclusion in source tags.
 */
export type UpdateAutoTagRequest = {
  /**
   * The tag value to update (matches value or normalized)
   */
  value: string;
  /**
   * New status for the tag
   */
  status: 'approved' | 'rejected';
};
