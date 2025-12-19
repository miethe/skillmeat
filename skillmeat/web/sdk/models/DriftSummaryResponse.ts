/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DriftDetectionResponse } from './DriftDetectionResponse';
/**
 * Summary of drift detection results across all artifacts.
 */
export type DriftSummaryResponse = {
    /**
     * Path to the project directory
     */
    project_path: string;
    /**
     * Name of the collection being compared
     */
    collection_name: string;
    /**
     * Total number of artifacts checked
     */
    total_artifacts: number;
    /**
     * Number of artifacts with drift detected
     */
    drifted_count: number;
    /**
     * Number of artifacts modified in project only
     */
    modified_count: number;
    /**
     * Number of artifacts modified in collection only
     */
    outdated_count: number;
    /**
     * Number of artifacts with three-way conflicts
     */
    conflict_count: number;
    /**
     * Number of artifacts added to collection
     */
    added_count: number;
    /**
     * Number of artifacts removed from collection
     */
    removed_count: number;
    /**
     * Number of artifacts with version mismatches
     */
    version_mismatch_count: number;
    /**
     * Count of upstream changes (outdated, added, removed drift)
     */
    upstream_changes: number;
    /**
     * Count of local changes (modified drift)
     */
    local_changes: number;
    /**
     * Count of conflicts (conflict drift)
     */
    conflicts: number;
    /**
     * Total artifacts with any drift
     */
    total: number;
    /**
     * Detailed drift information for each drifted artifact
     */
    drift_details?: Array<DriftDetectionResponse>;
    /**
     * Timestamp when drift detection was performed
     */
    checked_at: string;
};

