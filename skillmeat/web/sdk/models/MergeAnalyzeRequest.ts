/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for analyzing merge safety.
 *
 * Performs safety analysis without executing the merge to identify
 * potential conflicts and auto-mergeable files.
 */
export type MergeAnalyzeRequest = {
    /**
     * Snapshot ID of base/ancestor version
     */
    base_snapshot_id: string;
    /**
     * Name of the local collection
     */
    local_collection: string;
    /**
     * Snapshot ID of remote version to merge
     */
    remote_snapshot_id: string;
    /**
     * Name of remote collection (defaults to local_collection)
     */
    remote_collection?: (string | null);
};

