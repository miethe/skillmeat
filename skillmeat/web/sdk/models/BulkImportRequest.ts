/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BulkImportArtifact } from './BulkImportArtifact';
/**
 * Request to import multiple artifacts.
 */
export type BulkImportRequest = {
    /**
     * List of artifacts to import
     */
    artifacts: Array<BulkImportArtifact>;
    /**
     * Automatically resolve conflicts (overwrite existing artifacts)
     */
    auto_resolve_conflicts?: boolean;
    /**
     * List of artifact keys to mark as skipped (format: type:name)
     */
    skip_list?: (Array<string> | null);
};

