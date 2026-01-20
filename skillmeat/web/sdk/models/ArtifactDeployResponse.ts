/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for artifact deployment.
 */
export type ArtifactDeployResponse = {
  /**
   * Whether deployment succeeded
   */
  success: boolean;
  /**
   * Human-readable result message
   */
  message: string;
  /**
   * Name of deployed artifact
   */
  artifact_name: string;
  /**
   * Type of artifact (skill/command/agent)
   */
  artifact_type: string;
  /**
   * Path where artifact was deployed
   */
  deployed_path?: string | null;
  /**
   * Error details if deployment failed
   */
  error_message?: string | null;
};
