/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SyncConflictResponse } from './SyncConflictResponse';
/**
 * Response schema for sync status information.
 *
 * Attributes:
 * modified_in_project: Entity IDs modified in project
 * modified_in_collection: Entity IDs modified in collection
 * conflicts: List of sync conflicts
 */
export type SyncStatusResponse = {
  /**
   * Entity IDs modified in project
   */
  modified_in_project: Array<string>;
  /**
   * Entity IDs modified in collection
   */
  modified_in_collection: Array<string>;
  /**
   * List of sync conflicts
   */
  conflicts: Array<SyncConflictResponse>;
};
