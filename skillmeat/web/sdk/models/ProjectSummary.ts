/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CacheInfo } from './CacheInfo';
/**
 * Summary information about a project with deployments.
 *
 * Provides high-level project metadata including deployment counts
 * and last deployment time.
 */
export type ProjectSummary = {
  /**
   * Base64-encoded project path (unique identifier)
   */
  id: string;
  /**
   * Absolute filesystem path to project
   */
  path: string;
  /**
   * Project name (directory name)
   */
  name: string;
  /**
   * Total number of deployed artifacts
   */
  deployment_count: number;
  /**
   * Timestamp of most recent deployment
   */
  last_deployment?: string | null;
  /**
   * Cache metadata (only present when served from cache)
   */
  cache_info?: CacheInfo | null;
};
