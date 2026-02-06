/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogEntryResponse } from './CatalogEntryResponse';
import type { PageInfo } from './PageInfo';
/**
 * Paginated list of catalog entries with statistics.
 *
 * Includes aggregated counts by status and artifact type.
 */
export type CatalogListResponse = {
  /**
   * List of catalog entries for this page
   */
  items: Array<CatalogEntryResponse>;
  /**
   * Pagination metadata
   */
  page_info: PageInfo;
  /**
   * Count of entries by status
   */
  counts_by_status?: Record<string, number>;
  /**
   * Count of entries by artifact type
   */
  counts_by_type?: Record<string, number>;
};
