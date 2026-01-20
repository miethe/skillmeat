/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { TagResponse } from './TagResponse';
/**
 * Paginated response for tag listings.
 */
export type TagListResponse = {
  /**
   * List of tags for this page
   */
  items: Array<TagResponse>;
  /**
   * Pagination metadata
   */
  page_info: PageInfo;
};
