/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectDeploymentInfo } from './ProjectDeploymentInfo';
/**
 * Deployment statistics for an artifact.
 *
 * Aggregates deployment information across all projects
 * where this artifact is deployed.
 */
export type DeploymentStatistics = {
  /**
   * Total number of deployments across all projects
   */
  total_deployments: number;
  /**
   * Number of deployments with local modifications
   */
  modified_deployments: number;
  /**
   * Per-project deployment information
   */
  projects: Array<ProjectDeploymentInfo>;
};
