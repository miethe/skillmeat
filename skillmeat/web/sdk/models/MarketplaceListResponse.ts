/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MarketplaceEntryResponse } from './MarketplaceEntryResponse';
/**
 * Paginated list of marketplace entries.
 *
 * Attributes:
 * items: List of marketplace entries
 * total: Total number of entries
 * skip: Number of items skipped
 * limit: Maximum items per page
 */
export type MarketplaceListResponse = {
  /**
   * List of marketplace entries
   */
  items: Array<MarketplaceEntryResponse>;
  /**
   * Total number of marketplace entries
   */
  total: number;
  /**
   * Number of items skipped
   */
  skip: number;
  /**
   * Maximum items per page
   */
  limit: number;
};
