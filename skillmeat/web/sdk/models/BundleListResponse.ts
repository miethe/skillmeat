/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BundleListItem } from './BundleListItem';
/**
 * Response for listing bundles.
 */
export type BundleListResponse = {
  /**
   * List of bundles
   */
  bundles?: Array<BundleListItem>;
  /**
   * Total number of bundles
   */
  total: number;
  /**
   * Filter applied (created, imported, or None for all)
   */
  filtered_by?: string | null;
};
