/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactResponse } from './ArtifactResponse';
import type { PageInfo } from './PageInfo';
/**
 * Paginated response for artifact listings.
 */
export type ArtifactListResponse = {
  /**
   * List of items for this page
   */
  items: Array<ArtifactResponse>;
  /**
   * Pagination metadata
   */
  page_info: PageInfo;
};
