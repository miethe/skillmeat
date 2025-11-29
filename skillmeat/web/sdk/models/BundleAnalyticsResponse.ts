/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactPopularity } from './ArtifactPopularity';
/**
 * Bundle analytics response.
 */
export type BundleAnalyticsResponse = {
  /**
   * Bundle unique identifier
   */
  bundle_id: string;
  /**
   * Bundle name
   */
  bundle_name: string;
  /**
   * Total number of times bundle was downloaded/imported
   */
  total_downloads?: number;
  /**
   * Total deployments of artifacts from this bundle
   */
  total_deploys?: number;
  /**
   * Most deployed artifacts from this bundle (top 10)
   */
  popular_artifacts?: Array<ArtifactPopularity>;
  /**
   * ISO 8601 timestamp of first import
   */
  first_imported?: string | null;
  /**
   * ISO 8601 timestamp of last artifact deployment
   */
  last_used?: string | null;
  /**
   * Number of projects using artifacts from this bundle
   */
  active_projects?: number;
};
