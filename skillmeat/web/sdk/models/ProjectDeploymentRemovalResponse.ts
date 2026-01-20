/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for removing a deployed artifact from a project.
 */
export type ProjectDeploymentRemovalResponse = {
  /**
   * Whether the removal was successful
   */
  success: boolean;
  /**
   * Human-readable status message
   */
  message: string;
  /**
   * Name of the removed artifact
   */
  artifact_name: string;
  /**
   * Type of the removed artifact
   */
  artifact_type: string;
  /**
   * Path to the project
   */
  project_path: string;
  /**
   * Whether files were removed from filesystem
   */
  files_removed: boolean;
};
