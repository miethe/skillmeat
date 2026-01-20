/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Cached artifact information.
 *
 * Attributes:
 * id: Artifact ID
 * name: Artifact name
 * type: Artifact type (skill, command, etc.)
 * project_id: Project ID this artifact belongs to
 * deployed_version: Version deployed to project
 * upstream_version: Latest available version
 * is_outdated: Whether deployed version is behind upstream
 */
export type CachedArtifactResponse = {
  /**
   * Artifact ID
   */
  id: string;
  /**
   * Artifact name
   */
  name: string;
  /**
   * Artifact type
   */
  type: string;
  /**
   * Project ID
   */
  project_id: string;
  /**
   * Version deployed to project
   */
  deployed_version?: string | null;
  /**
   * Latest available version
   */
  upstream_version?: string | null;
  /**
   * Whether artifact is outdated
   */
  is_outdated: boolean;
};
