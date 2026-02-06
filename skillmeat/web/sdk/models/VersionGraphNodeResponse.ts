/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactVersionInfo } from './ArtifactVersionInfo';
/**
 * Node in version graph visualization.
 *
 * Recursive structure representing the version tree,
 * where each node can have multiple children representing
 * deployments or forks.
 */
export type VersionGraphNodeResponse = {
  /**
   * Unique node identifier (e.g., 'collection:default:abc123' or 'project:/path/to/project')
   */
  id: string;
  /**
   * Artifact name
   */
  artifact_name: string;
  /**
   * Artifact type
   */
  artifact_type: string;
  /**
   * Version information for this node
   */
  version_info: ArtifactVersionInfo;
  /**
   * Child nodes (deployments/forks from this version)
   */
  children?: Array<VersionGraphNodeResponse>;
  /**
   * Additional node metadata
   */
  metadata?: Record<string, any>;
};
