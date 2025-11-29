/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Deployment information for a single project.
 *
 * Provides per-project deployment details including
 * modification status and deployment timestamp.
 */
export type ProjectDeploymentInfo = {
  /**
   * Project name (derived from path)
   */
  project_name: string;
  /**
   * Absolute project path
   */
  project_path: string;
  /**
   * Whether this deployment has local modifications
   */
  is_modified: boolean;
  /**
   * Deployment timestamp
   */
  deployed_at: string;
};
