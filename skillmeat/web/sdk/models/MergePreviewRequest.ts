/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for previewing merge changes.
 *
 * Shows what files will be added, removed, or changed by the merge
 * without executing it.
 */
export type MergePreviewRequest = {
  /**
   * Snapshot ID of base/ancestor version
   */
  base_snapshot_id: string;
  /**
   * Name of the local collection
   */
  local_collection: string;
  /**
   * Snapshot ID of remote version to merge
   */
  remote_snapshot_id: string;
  /**
   * Name of remote collection (defaults to local_collection)
   */
  remote_collection?: string | null;
};
