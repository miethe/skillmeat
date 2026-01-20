/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type Body_import_bundle_api_v1_bundles_import_post = {
    /**
     * Bundle ZIP file to import
     */
    bundle_file: Blob;
    /**
     * Conflict resolution strategy (merge, fork, skip, interactive)
     */
    strategy?: string;
    /**
     * Target collection (uses active if None)
     */
    collection_name?: (string | null);
    /**
     * Preview import without making changes
     */
    dry_run?: boolean;
    /**
     * Force import even with validation warnings
     */
    force?: boolean;
    /**
     * Expected SHA-256 hash for verification
     */
    expected_hash?: (string | null);
};

