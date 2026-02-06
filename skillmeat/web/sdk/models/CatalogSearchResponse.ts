/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogSearchResult } from './CatalogSearchResult';
/**
 * Response model for cross-source catalog search.
 *
 * Returns paginated search results with cursor-based pagination support.
 */
export type CatalogSearchResponse = {
  /**
   * List of matching catalog entries
   */
  items: Array<CatalogSearchResult>;
  /**
   * Cursor for fetching next page (None if no more results)
   */
  next_cursor?: string | null;
  /**
   * True if more results exist beyond this page
   */
  has_more: boolean;
};
