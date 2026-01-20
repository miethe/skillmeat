/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to rollback to a previous snapshot.
 *
 * Supports both simple rollback and intelligent merge-based rollback
 * with selective path restoration.
 */
export type RollbackRequest = {
    /**
     * ID of snapshot to rollback to
     */
    snapshot_id: string;
    /**
     * Collection name (uses active collection if not specified)
     */
    collection_name?: (string | null);
    /**
     * Use intelligent merge to preserve local changes (recommended)
     */
    preserve_changes?: boolean;
    /**
     * Only rollback these specific paths (optional)
     */
    selective_paths?: (Array<string> | null);
};

