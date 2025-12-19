/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RefreshJobStatus } from './RefreshJobStatus';
/**
 * Cache statistics and status information.
 *
 * Attributes:
 * total_projects: Total number of cached projects
 * total_artifacts: Total number of cached artifacts
 * stale_projects: Number of projects past TTL
 * outdated_artifacts: Number of artifacts with updates available
 * cache_size_bytes: Database file size in bytes
 * oldest_entry: Datetime of oldest cached entry
 * newest_entry: Datetime of newest cached entry
 * last_refresh: When cache was last refreshed
 * refresh_job_status: Status of background refresh job
 */
export type CacheStatusResponse = {
    /**
     * Total number of cached projects
     */
    total_projects: number;
    /**
     * Total number of cached artifacts
     */
    total_artifacts: number;
    /**
     * Number of stale projects (past TTL)
     */
    stale_projects: number;
    /**
     * Number of artifacts with updates available
     */
    outdated_artifacts: number;
    /**
     * Cache database size in bytes
     */
    cache_size_bytes: number;
    /**
     * Datetime of oldest cached entry
     */
    oldest_entry?: (string | null);
    /**
     * Datetime of newest cached entry
     */
    newest_entry?: (string | null);
    /**
     * When cache was last refreshed
     */
    last_refresh?: (string | null);
    /**
     * Background refresh job status
     */
    refresh_job_status: RefreshJobStatus;
};

