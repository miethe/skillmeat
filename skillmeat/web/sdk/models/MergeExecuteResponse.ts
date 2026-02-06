/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConflictMetadataResponse } from './ConflictMetadataResponse';
/**
 * Response schema for merge execution.
 *
 * Provides result of merge operation including files merged and any
 * unresolved conflicts.
 */
export type MergeExecuteResponse = {
  /**
   * True if merge completed successfully
   */
  success: boolean;
  /**
   * List of file paths that were merged
   */
  files_merged?: Array<string>;
  /**
   * List of conflict metadata for unresolved conflicts
   */
  conflicts?: Array<ConflictMetadataResponse>;
  /**
   * ID of safety snapshot created before merge
   */
  pre_merge_snapshot_id?: string | null;
  /**
   * Error message if merge failed
   */
  error?: string | null;
};
