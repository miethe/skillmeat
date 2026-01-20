/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for executing a merge.
 *
 * Performs the actual merge operation with automatic snapshot creation
 * for safety.
 */
export type MergeExecuteRequest = {
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
  /**
   * Whether to automatically create a safety snapshot before merge
   */
  auto_snapshot?: boolean;
};
