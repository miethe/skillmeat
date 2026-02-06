/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result for a single source in bulk refresh operation.
 */
export type BulkAutoTagRefreshItemResult = {
  /**
   * Marketplace source ID
   */
  source_id: string;
  /**
   * Whether the refresh succeeded
   */
  success: boolean;
  /**
   * Number of tags found (None if failed)
   */
  tags_found?: number | null;
  /**
   * Number of new tags added (None if failed)
   */
  tags_added?: number | null;
  /**
   * Number of existing tags updated (None if failed)
   */
  tags_updated?: number | null;
  /**
   * Error message if refresh failed
   */
  error?: string | null;
};
