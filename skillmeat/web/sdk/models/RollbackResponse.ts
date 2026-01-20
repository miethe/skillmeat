/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConflictMetadataResponse } from './ConflictMetadataResponse';
/**
 * Rollback operation result.
 *
 * Contains detailed information about files restored, merged, and
 * any conflicts encountered during rollback.
 */
export type RollbackResponse = {
    /**
     * Whether rollback operation completed successfully
     */
    success: boolean;
    /**
     * Files that were successfully merged
     */
    files_merged?: Array<string>;
    /**
     * Files that were restored from snapshot
     */
    files_restored?: Array<string>;
    /**
     * Conflicts that require manual resolution
     */
    conflicts?: Array<ConflictMetadataResponse>;
    /**
     * ID of safety snapshot created before rollback
     */
    safety_snapshot_id?: (string | null);
};

