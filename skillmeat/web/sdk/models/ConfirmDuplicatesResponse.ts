/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfirmDuplicatesStatus } from './ConfirmDuplicatesStatus';
/**
 * Response from processing duplicate review decisions.
 *
 * Provides summary counts and status of all operations performed.
 */
export type ConfirmDuplicatesResponse = {
  /**
   * Overall status: 'success', 'partial', or 'failed'
   */
  status: ConfirmDuplicatesStatus;
  /**
   * Number of artifacts successfully linked to collection entries
   */
  linked_count: number;
  /**
   * Number of new artifacts successfully imported
   */
  imported_count: number;
  /**
   * Number of artifacts marked as skipped
   */
  skipped_count: number;
  /**
   * Human-readable summary message
   */
  message: string;
  /**
   * ISO 8601 timestamp of when the operation completed
   */
  timestamp: string;
  /**
   * List of error messages for failed operations
   */
  errors?: Array<string>;
};
