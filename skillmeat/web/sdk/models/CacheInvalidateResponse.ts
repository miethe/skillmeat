/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from cache invalidation.
 *
 * Attributes:
 * success: Whether invalidation succeeded
 * invalidated_count: Number of projects invalidated
 * message: Human-readable status message
 */
export type CacheInvalidateResponse = {
    /**
     * Whether invalidation succeeded
     */
    success: boolean;
    /**
     * Number of projects invalidated
     */
    invalidated_count: number;
    /**
     * Human-readable status message
     */
    message: string;
};

