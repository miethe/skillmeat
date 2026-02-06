/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from cache refresh operation.
 *
 * Attributes:
 * success: Whether the refresh completed successfully
 * projects_refreshed: Number of projects refreshed
 * changes_detected: Whether any changes were detected
 * errors: List of error messages (if any)
 * duration_seconds: Time taken for refresh operation
 * message: Human-readable status message
 */
export type CacheRefreshResponse = {
  /**
   * Overall success status
   */
  success: boolean;
  /**
   * Number of projects successfully refreshed
   */
  projects_refreshed: number;
  /**
   * Whether any changes were detected during refresh
   */
  changes_detected: boolean;
  /**
   * List of error messages encountered
   */
  errors?: Array<string>;
  /**
   * Total operation duration in seconds
   */
  duration_seconds: number;
  /**
   * Human-readable status message
   */
  message: string;
};
