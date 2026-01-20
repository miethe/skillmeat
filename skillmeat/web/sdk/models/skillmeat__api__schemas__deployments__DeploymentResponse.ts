/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from a deployment operation.
 */
export type skillmeat__api__schemas__deployments__DeploymentResponse = {
  /**
   * Whether deployment succeeded
   */
  success: boolean;
  /**
   * Status message
   */
  message: string;
  /**
   * Deployment identifier (format: 'type:name')
   */
  deployment_id?: string | null;
  /**
   * SSE stream URL for progress updates (if supported)
   */
  stream_url?: string | null;
  /**
   * Deployed artifact name
   */
  artifact_name: string;
  /**
   * Deployed artifact type
   */
  artifact_type: string;
  /**
   * Target project path
   */
  project_path: string;
  /**
   * Path where artifact was deployed
   */
  deployed_path: string;
  /**
   * Timestamp of deployment
   */
  deployed_at?: string | null;
};
