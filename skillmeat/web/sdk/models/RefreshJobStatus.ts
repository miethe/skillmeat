/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Status of the background refresh job.
 *
 * Attributes:
 * is_running: Whether scheduler is currently running
 * next_run_time: When next refresh will run (if scheduled)
 * last_run_time: When last refresh completed
 */
export type RefreshJobStatus = {
  /**
   * Whether refresh scheduler is running
   */
  is_running: boolean;
  /**
   * Next scheduled refresh time
   */
  next_run_time?: string | null;
  /**
   * Last refresh completion time
   */
  last_run_time?: string | null;
};
