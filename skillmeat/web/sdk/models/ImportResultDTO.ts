/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result of importing artifacts from catalog.
 *
 * Contains import statistics and details of any errors.
 */
export type ImportResultDTO = {
    /**
     * Number of artifacts successfully imported
     */
    imported_count: number;
    /**
     * Number of artifacts skipped due to conflicts or other reasons
     */
    skipped_count: number;
    /**
     * Number of artifacts that failed to import
     */
    error_count: number;
    /**
     * List of entry IDs that were successfully imported
     */
    imported_ids: Array<string>;
    /**
     * List of entry IDs that were skipped
     */
    skipped_ids: Array<string>;
    /**
     * List of {entry_id, error} for failed imports
     */
    errors?: Array<Record<string, string>>;
};

