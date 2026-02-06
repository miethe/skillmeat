/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextEntityResponse } from './ContextEntityResponse';
import type { PageInfo } from './PageInfo';
/**
 * Paginated response for context entity listings.
 *
 * Inherits pagination metadata from PaginatedResponse:
 * - items: List of context entities
 * - page_info: Cursor-based pagination information
 *
 * Example:
 * >>> response = ContextEntityListResponse(
 * ...     items=[entity1, entity2],
 * ...     page_info=PageInfo(
 * ...         has_next_page=True,
 * ...         has_previous_page=False,
 * ...         end_cursor="cursor123"
 * ...     )
 * ... )
 */
export type ContextEntityListResponse = {
  /**
   * List of items for this page
   */
  items: Array<ContextEntityResponse>;
  /**
   * Pagination metadata
   */
  page_info: PageInfo;
};
