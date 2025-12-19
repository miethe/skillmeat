/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result of scanning a GitHub repository.
 *
 * Contains scan statistics, duration, and any errors encountered.
 */
export type ScanResultDTO = {
    /**
     * ID of the source that was scanned
     */
    source_id: string;
    /**
     * Scan result status
     */
    status: 'success' | 'error' | 'partial';
    /**
     * Total number of artifacts detected
     */
    artifacts_found: number;
    /**
     * Number of new artifacts detected
     */
    new_count: number;
    /**
     * Number of artifacts with changes detected
     */
    updated_count: number;
    /**
     * Number of artifacts no longer present
     */
    removed_count: number;
    /**
     * Number of artifacts with no changes
     */
    unchanged_count: number;
    /**
     * Scan duration in milliseconds
     */
    scan_duration_ms: number;
    /**
     * List of error messages encountered during scan
     */
    errors?: Array<string>;
    /**
     * Timestamp when scan completed
     */
    scanned_at: string;
};

