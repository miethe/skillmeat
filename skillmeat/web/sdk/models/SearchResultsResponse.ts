/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SearchResult } from './SearchResult';
/**
 * Paginated search results.
 *
 * Attributes:
 * items: List of search results
 * total: Total number of matches (before pagination)
 * query: Original search query
 * skip: Number of items skipped
 * limit: Maximum items per page
 */
export type SearchResultsResponse = {
  /**
   * List of search results
   */
  items: Array<SearchResult>;
  /**
   * Total number of matches
   */
  total: number;
  /**
   * Search query
   */
  query: string;
  /**
   * Number of items skipped
   */
  skip: number;
  /**
   * Maximum items per page
   */
  limit: number;
};
