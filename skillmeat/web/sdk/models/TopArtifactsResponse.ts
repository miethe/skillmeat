/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { TopArtifactItem } from './TopArtifactItem';
/**
 * Paginated response for top artifacts by usage.
 *
 * Returns artifacts sorted by usage frequency with pagination support.
 */
export type TopArtifactsResponse = {
    /**
     * List of items for this page
     */
    items: Array<TopArtifactItem>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

