/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ImportedArtifactResponse } from './ImportedArtifactResponse';
/**
 * Response from bundle import operation.
 */
export type BundleImportResponse = {
    /**
     * Whether import succeeded
     */
    success: boolean;
    /**
     * Number of new artifacts imported
     */
    imported_count?: number;
    /**
     * Number of artifacts skipped
     */
    skipped_count?: number;
    /**
     * Number of artifacts forked
     */
    forked_count?: number;
    /**
     * Number of artifacts merged (overwritten)
     */
    merged_count?: number;
    /**
     * Details of imported artifacts
     */
    artifacts?: Array<ImportedArtifactResponse>;
    /**
     * Error messages if import failed
     */
    errors?: Array<string>;
    /**
     * Warning messages
     */
    warnings?: Array<string>;
    /**
     * SHA-256 hash of imported bundle
     */
    bundle_hash?: (string | null);
    /**
     * Timestamp of import operation
     */
    import_time?: (string | null);
    /**
     * Human-readable summary
     */
    summary?: string;
};

