/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ModifiedArtifactInfo } from './ModifiedArtifactInfo';
/**
 * Response for modified artifacts in a project.
 *
 * Lists all artifacts in a project that have been modified
 * since deployment.
 */
export type ModifiedArtifactsResponse = {
  /**
   * Base64-encoded project path
   */
  project_id: string;
  /**
   * List of modified artifacts
   */
  modified_artifacts: Array<ModifiedArtifactInfo>;
  /**
   * Total number of modified artifacts
   */
  total_count: number;
  /**
   * Timestamp when modifications were last checked
   */
  last_checked: string;
};
