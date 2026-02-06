/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Information about a stale artifact.
 *
 * Attributes:
 * id: Artifact ID
 * name: Artifact name
 * type: Artifact type
 * project_name: Name of project this artifact belongs to
 * project_id: Project ID this artifact belongs to
 * deployed_version: Currently deployed version
 * upstream_version: Available upstream version
 * version_difference: Human-readable description of version difference
 */
export type StaleArtifactResponse = {
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
   * Project name
   */
  project_name: string;
  /**
   * Project ID
   */
  project_id: string;
  /**
   * Currently deployed version
   */
  deployed_version?: string | null;
  /**
   * Available upstream version
   */
  upstream_version?: string | null;
  /**
   * Human-readable description of version difference
   */
  version_difference?: string | null;
};
