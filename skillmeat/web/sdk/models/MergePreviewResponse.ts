/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConflictMetadataResponse } from './ConflictMetadataResponse';
/**
 * Response schema for merge preview.
 *
 * Provides a preview of merge changes without executing the merge.
 */
export type MergePreviewResponse = {
    /**
     * List of file paths added in remote
     */
    files_added?: Array<string>;
    /**
     * List of file paths removed in remote
     */
    files_removed?: Array<string>;
    /**
     * List of file paths that differ between versions
     */
    files_changed?: Array<string>;
    /**
     * List of conflict metadata for potential conflicts
     */
    potential_conflicts?: Array<ConflictMetadataResponse>;
    /**
     * Whether merge can be performed automatically
     */
    can_auto_merge: boolean;
};

