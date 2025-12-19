/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for resolving a single conflict.
 *
 * Allows manual resolution of merge conflicts by specifying which
 * version to use or providing custom content.
 */
export type ConflictResolveRequest = {
    /**
     * Relative path to the conflicting file
     */
    file_path: string;
    /**
     * Resolution strategy to apply
     */
    resolution: 'use_local' | 'use_remote' | 'use_base' | 'custom';
    /**
     * Custom content to use (required if resolution='custom')
     */
    custom_content?: (string | null);
};

