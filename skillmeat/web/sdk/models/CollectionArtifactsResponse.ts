/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactSummary } from './ArtifactSummary';
import type { PageInfo } from './PageInfo';
/**
 * Paginated response for artifacts within a collection.
 *
 * Returns lightweight artifact summaries for efficient collection browsing.
 */
export type CollectionArtifactsResponse = {
  /**
   * List of items for this page
   */
  items: Array<ArtifactSummary>;
  /**
   * Pagination metadata
   */
  page_info: PageInfo;
};
