/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BulkSyncItemResult } from './BulkSyncItemResult';
/**
 * Response from bulk sync operation.
 *
 * Provides summary statistics and per-artifact results for a bulk
 * sync operation on imported marketplace artifacts.
 */
export type BulkSyncResponse = {
  /**
   * Total number of artifacts requested for sync
   */
  total: number;
  /**
   * Number of artifacts successfully synced
   */
  synced: number;
  /**
   * Number of artifacts skipped (not imported or no changes)
   */
  skipped: number;
  /**
   * Number of artifacts that failed to sync
   */
  failed: number;
  /**
   * Per-artifact sync results
   */
  results?: Array<BulkSyncItemResult>;
};
