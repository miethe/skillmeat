/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Cached project information.
 *
 * Attributes:
 * id: Project ID
 * name: Project name
 * path: Filesystem path to project
 * status: Project status (active, stale, error)
 * last_fetched: When project was last fetched
 * artifact_count: Number of artifacts in project
 */
export type CachedProjectResponse = {
  /**
   * Project ID
   */
  id: string;
  /**
   * Project name
   */
  name: string;
  /**
   * Filesystem path to project
   */
  path: string;
  /**
   * Project status
   */
  status: string;
  /**
   * When project was last fetched
   */
  last_fetched?: string | null;
  /**
   * Number of artifacts in project
   */
  artifact_count: number;
};
