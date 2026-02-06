/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Overall analytics summary.
 *
 * Provides high-level statistics about the collection and usage patterns.
 */
export type AnalyticsSummaryResponse = {
  /**
   * Total number of collections
   */
  total_collections: number;
  /**
   * Total number of artifacts across all collections
   */
  total_artifacts: number;
  /**
   * Total number of deployments
   */
  total_deployments: number;
  /**
   * Total number of tracked events
   */
  total_events: number;
  /**
   * Count of artifacts by type
   */
  artifacts_by_type: Record<string, number>;
  /**
   * Number of events in the last 24 hours
   */
  recent_activity_count: number;
  /**
   * Name of the most frequently deployed artifact
   */
  most_deployed_artifact: string;
  /**
   * Timestamp of most recent activity
   */
  last_activity: string;
};
