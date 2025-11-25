/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ListingResponse } from './ListingResponse';
import type { PageInfo } from './PageInfo';
/**
 * Paginated response for marketplace listings.
 *
 * Uses cursor-based pagination for efficient browsing of large datasets.
 */
export type ListingsPageResponse = {
    /**
     * List of listings for this page
     */
    items: Array<ListingResponse>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

