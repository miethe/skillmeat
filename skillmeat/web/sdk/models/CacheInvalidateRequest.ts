/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to invalidate cache.
 *
 * Attributes:
 * project_id: If provided, only invalidate this project. If None, invalidate all.
 */
export type CacheInvalidateRequest = {
    /**
     * Project ID to invalidate (if None, invalidate all)
     */
    project_id?: (string | null);
};

