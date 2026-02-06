/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeploymentInfo } from './DeploymentInfo';
/**
 * Response listing all deployments in a project.
 */
export type DeploymentListResponse = {
  /**
   * Project directory path
   */
  project_path: string;
  /**
   * List of deployments
   */
  deployments?: Array<DeploymentInfo>;
  /**
   * Total number of deployments
   */
  total: number;
};
