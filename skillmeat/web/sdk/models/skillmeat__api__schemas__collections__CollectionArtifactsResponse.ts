/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { skillmeat__api__schemas__collections__ArtifactSummary } from './skillmeat__api__schemas__collections__ArtifactSummary';
/**
 * Paginated response for artifacts within a collection.
 *
 * Returns lightweight artifact summaries for efficient collection browsing.
 */
export type skillmeat__api__schemas__collections__CollectionArtifactsResponse = {
    /**
     * List of items for this page
     */
    items: Array<skillmeat__api__schemas__collections__ArtifactSummary>;
    /**
     * Pagination metadata
     */
    page_info: PageInfo;
};

