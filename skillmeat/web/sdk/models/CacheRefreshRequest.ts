/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to trigger cache refresh.
 *
 * Attributes:
 * project_id: If provided, only refresh this project. If None, refresh all.
 * force: If True, refresh even if cache is not stale.
 */
export type CacheRefreshRequest = {
  /**
   * Project ID to refresh (if None, refresh all projects)
   */
  project_id?: string | null;
  /**
   * Force refresh even if not stale
   */
  force?: boolean;
};
