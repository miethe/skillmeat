/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeployedArtifact } from './DeployedArtifact';
/**
 * Detailed information about a project including all deployments.
 *
 * Extends ProjectSummary with complete list of deployed artifacts
 * and aggregated statistics.
 */
export type ProjectDetail = {
  /**
   * Base64-encoded project path (unique identifier)
   */
  id: string;
  /**
   * Absolute filesystem path to project
   */
  path: string;
  /**
   * Project name (directory name)
   */
  name: string;
  /**
   * Total number of deployed artifacts
   */
  deployment_count: number;
  /**
   * Timestamp of most recent deployment
   */
  last_deployment?: string | null;
  /**
   * Complete list of deployed artifacts
   */
  deployments?: Array<DeployedArtifact>;
  /**
   * Aggregated deployment statistics
   */
  stats: Record<string, any>;
};
