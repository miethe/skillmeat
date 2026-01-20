/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to create a new snapshot.
 *
 * Creates a point-in-time snapshot of a collection for later rollback.
 */
export type SnapshotCreateRequest = {
    /**
     * Collection name (uses active collection if not specified)
     */
    collection_name?: (string | null);
    /**
     * Snapshot description or commit message
     */
    message?: string;
};

