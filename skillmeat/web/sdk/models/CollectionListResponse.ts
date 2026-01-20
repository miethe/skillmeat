/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CollectionResponse } from './CollectionResponse';
import type { PageInfo } from './PageInfo';
/**
 * Paginated response for collection listings.
 *
 * Extends the generic paginated response with collection-specific items.
 */
export type CollectionListResponse = {
  /**
   * List of items for this page
   */
  items: Array<CollectionResponse>;
  /**
   * Pagination metadata
   */
  page_info: PageInfo;
};
