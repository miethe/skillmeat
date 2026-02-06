/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to sync multiple imported artifacts from a marketplace source.
 *
 * Used to update imported artifacts with their upstream versions when
 * changes are detected during a rescan.
 */
export type BulkSyncRequest = {
  /**
   * Catalog entry IDs to sync with upstream
   */
  artifact_ids: Array<string>;
};
