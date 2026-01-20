/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { SnapshotResponse } from './SnapshotResponse';
/**
 * Paginated response for snapshot listings.
 *
 * Returns list of snapshots with pagination metadata following
 * cursor-based pagination pattern.
 */
export type SnapshotListResponse = {
    /**
     * List of items for this page
     */
    items: Array<SnapshotResponse>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

