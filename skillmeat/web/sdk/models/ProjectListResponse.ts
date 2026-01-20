/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { ProjectSummary } from './ProjectSummary';
/**
 * Paginated response for project listings.
 *
 * Extends the generic paginated response with project-specific items.
 */
export type ProjectListResponse = {
    /**
     * List of items for this page
     */
    items: Array<ProjectSummary>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

