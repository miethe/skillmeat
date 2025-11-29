/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeploymentModificationStatus } from './DeploymentModificationStatus';
/**
 * Response from modification check operation.
 *
 * Provides comprehensive status of all deployments in a project,
 * identifying which artifacts have been modified.
 */
export type ModificationCheckResponse = {
  /**
   * Base64-encoded project path
   */
  project_id: string;
  /**
   * Timestamp when check was performed
   */
  checked_at: string;
  /**
   * Number of modified artifacts detected
   */
  modifications_detected: number;
  /**
   * Status of each deployment in the project
   */
  deployments: Array<DeploymentModificationStatus>;
};
