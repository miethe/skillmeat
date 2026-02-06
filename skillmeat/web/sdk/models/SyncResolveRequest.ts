/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for resolving sync conflicts.
 *
 * Attributes:
 * project_path: Absolute path to project directory
 * entity_id: Entity identifier to resolve
 * resolution: Resolution strategy (keep_local, keep_remote, merge)
 * merged_content: Required if resolution is "merge"
 */
export type SyncResolveRequest = {
  /**
   * Absolute path to project directory
   */
  project_path: string;
  /**
   * Entity identifier to resolve
   */
  entity_id: string;
  /**
   * Resolution strategy
   */
  resolution: 'keep_local' | 'keep_remote' | 'merge';
  /**
   * Required if resolution is 'merge'
   */
  merged_content?: string | null;
};
