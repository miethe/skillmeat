/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CachedArtifactResponse } from './CachedArtifactResponse';
/**
 * Paginated list of cached artifacts.
 *
 * Attributes:
 * items: List of cached artifacts
 * total: Total number of artifacts (before pagination/filtering)
 * skip: Number of items skipped
 * limit: Maximum items per page
 */
export type CachedArtifactsListResponse = {
    /**
     * List of cached artifacts
     */
    items: Array<CachedArtifactResponse>;
    /**
     * Total number of artifacts
     */
    total: number;
    /**
     * Number of items skipped
     */
    skip: number;
    /**
     * Maximum items per page
     */
    limit: number;
};

