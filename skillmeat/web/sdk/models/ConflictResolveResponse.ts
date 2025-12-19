/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for conflict resolution.
 *
 * Indicates whether the conflict was successfully resolved.
 */
export type ConflictResolveResponse = {
    /**
     * True if conflict was resolved successfully
     */
    success: boolean;
    /**
     * Path to the file that was resolved
     */
    file_path: string;
    /**
     * Resolution strategy that was applied
     */
    resolution_applied: string;
};

