/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Diff information for a single file.
 */
export type FileDiff = {
    /**
     * Relative path to file within artifact
     */
    file_path: string;
    /**
     * Change status of file
     */
    status: 'added' | 'modified' | 'deleted' | 'unchanged';
    /**
     * SHA-256 hash in collection
     */
    collection_hash?: (string | null);
    /**
     * SHA-256 hash in project
     */
    project_hash?: (string | null);
    /**
     * Unified diff content (for modified files)
     */
    unified_diff?: (string | null);
};

