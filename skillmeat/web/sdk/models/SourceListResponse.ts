/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { SourceResponse } from './SourceResponse';
/**
 * Paginated list of GitHub repository sources.
 *
 * Uses cursor-based pagination for efficient browsing.
 */
export type SourceListResponse = {
    /**
     * List of sources for this page
     */
    items: Array<SourceResponse>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

