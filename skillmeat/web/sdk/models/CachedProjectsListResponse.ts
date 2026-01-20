/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CachedProjectResponse } from './CachedProjectResponse';
/**
 * Paginated list of cached projects.
 *
 * Attributes:
 * items: List of cached projects
 * total: Total number of projects (before pagination)
 * skip: Number of items skipped
 * limit: Maximum items per page
 */
export type CachedProjectsListResponse = {
    /**
     * List of cached projects
     */
    items: Array<CachedProjectResponse>;
    /**
     * Total number of projects
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

