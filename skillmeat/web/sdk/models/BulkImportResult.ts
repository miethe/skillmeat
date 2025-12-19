/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ImportResult } from './ImportResult';
/**
 * Result of bulk import operation.
 */
export type BulkImportResult = {
    /**
     * Total number of artifacts requested for import
     */
    total_requested: number;
    /**
     * Number of artifacts successfully imported
     */
    total_imported: number;
    /**
     * Number of artifacts skipped (already exist)
     */
    total_skipped?: number;
    /**
     * Number of artifacts that failed to import
     */
    total_failed: number;
    /**
     * Number of artifacts added to Collection
     */
    imported_to_collection?: number;
    /**
     * Number of artifacts deployed to Project
     */
    added_to_project?: number;
    /**
     * Per-artifact import results
     */
    results?: Array<ImportResult>;
    /**
     * Total import duration in milliseconds
     */
    duration_ms: number;
    /**
     * Human-readable summary of import results.
     */
    readonly summary: string;
};

