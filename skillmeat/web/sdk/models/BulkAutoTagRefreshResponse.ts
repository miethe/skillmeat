/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BulkAutoTagRefreshItemResult } from './BulkAutoTagRefreshItemResult';
/**
 * Response from bulk auto-tag refresh operation.
 *
 * Returns individual results for each source and summary statistics.
 */
export type BulkAutoTagRefreshResponse = {
  /**
   * Individual results for each source
   */
  results: Array<BulkAutoTagRefreshItemResult>;
  /**
   * Total number of sources requested
   */
  total_requested: number;
  /**
   * Number of sources successfully refreshed
   */
  total_succeeded: number;
  /**
   * Number of sources that failed to refresh
   */
  total_failed: number;
};
