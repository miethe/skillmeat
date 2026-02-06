/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Lightweight deployment summary for collection artifact responses.
 *
 * This schema matches the structure stored in CollectionArtifact.deployments_json
 * and is used for efficient display of deployment counts and basic info.
 */
export type DeploymentSummary = {
  /**
   * Absolute path to the project directory
   */
  project_path: string;
  /**
   * Display name of the project
   */
  project_name: string;
  /**
   * Deployment timestamp
   */
  deployed_at: string;
};
