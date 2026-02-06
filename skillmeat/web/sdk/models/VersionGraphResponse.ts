/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { VersionGraphNodeResponse } from './VersionGraphNodeResponse';
/**
 * Complete version graph for an artifact.
 *
 * Provides hierarchical view of artifact versions across
 * collection and all project deployments, with aggregated
 * statistics.
 */
export type VersionGraphResponse = {
  /**
   * Artifact name
   */
  artifact_name: string;
  /**
   * Artifact type
   */
  artifact_type: string;
  /**
   * Root node (typically the collection version)
   */
  root?: VersionGraphNodeResponse | null;
  /**
   * Aggregated statistics about version graph
   */
  statistics: Record<string, any>;
  /**
   * Timestamp when graph was last computed
   */
  last_updated: string;
};
