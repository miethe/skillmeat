/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { UserCollectionResponse } from './UserCollectionResponse';
/**
 * Paginated response for user collection listings.
 *
 * Extends the generic paginated response with collection-specific items.
 */
export type UserCollectionListResponse = {
    /**
     * List of items for this page
     */
    items: Array<UserCollectionResponse>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

