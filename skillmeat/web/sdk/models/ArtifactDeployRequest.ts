/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for deploying an artifact.
 */
export type ArtifactDeployRequest = {
  /**
   * Path to target project directory
   */
  project_path: string;
  /**
   * Overwrite existing artifact if already deployed
   */
  overwrite?: boolean;
  /**
   * Deployment strategy. 'overwrite' replaces existing files entirely (default, existing behavior). 'merge' performs file-level merge: new files are copied, project-only files are preserved, and conflicts (files modified on both sides) are reported.
   */
  strategy?: 'overwrite' | 'merge';
};
