/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RefreshModeEnum } from './RefreshModeEnum';
/**
 * Request schema for refreshing collection artifact metadata.
 *
 * Supports dry-run preview mode and selective artifact filtering.
 */
export type RefreshRequest = {
  /**
   * Refresh mode: 'metadata_only' updates metadata fields only, 'check_only' previews changes without applying, 'sync' performs full synchronization including version updates
   */
  mode?: RefreshModeEnum;
  /**
   * Optional filter to target specific artifacts. Supports 'type' (artifact type) and 'name' (glob pattern) keys.
   */
  artifact_filter?: Record<string, any> | null;
  /**
   * Preview changes without applying them (overrides mode)
   */
  dry_run?: boolean;
  /**
   * Optional list of specific fields to refresh. Valid fields: description, tags, author, license, origin_source. If not provided, all fields will be refreshed.
   */
  fields?: Array<string> | null;
};
