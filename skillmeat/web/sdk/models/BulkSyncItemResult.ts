/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result for a single artifact sync operation.
 *
 * Provides detailed status for each artifact in a bulk sync request,
 * including success/failure status, conflicts, and error messages.
 */
export type BulkSyncItemResult = {
    /**
     * Catalog entry ID that was synced
     */
    entry_id: string;
    /**
     * Name of the artifact
     */
    artifact_name: string;
    /**
     * Whether the sync succeeded
     */
    success: boolean;
    /**
     * Human-readable result message
     */
    message: string;
    /**
     * Whether there were merge conflicts during sync
     */
    has_conflicts?: boolean;
    /**
     * File paths with merge conflicts (if any)
     */
    conflicts?: (Array<string> | null);
};

