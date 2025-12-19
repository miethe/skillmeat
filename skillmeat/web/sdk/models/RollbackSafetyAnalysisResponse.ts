/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Pre-flight rollback safety analysis.
 *
 * Provides analysis of potential conflicts and safety information
 * before executing a rollback operation.
 */
export type RollbackSafetyAnalysisResponse = {
    /**
     * Whether rollback can proceed without data loss
     */
    is_safe: boolean;
    /**
     * Files that have conflicts requiring manual resolution
     */
    files_with_conflicts?: Array<string>;
    /**
     * Files that can be safely restored without conflicts
     */
    files_safe_to_restore?: Array<string>;
    /**
     * Warning messages about potential issues
     */
    warnings?: Array<string>;
};

