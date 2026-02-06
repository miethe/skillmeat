/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to refresh auto-tags for multiple sources.
 *
 * Allows batch refresh of GitHub topics for specified sources.
 */
export type BulkAutoTagRefreshRequest = {
  /**
   * List of source IDs to refresh (max 50)
   */
  source_ids: Array<string>;
};
