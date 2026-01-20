/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GitHubMetadata } from './GitHubMetadata';
/**
 * Response from GitHub metadata fetch.
 */
export type MetadataFetchResponse = {
  /**
   * Whether metadata fetch succeeded
   */
  success: boolean;
  /**
   * Fetched metadata (if successful)
   */
  metadata?: GitHubMetadata | null;
  /**
   * Error message (if failed)
   */
  error?: string | null;
};
