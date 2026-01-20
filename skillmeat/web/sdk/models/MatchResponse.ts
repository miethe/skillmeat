/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MatchedArtifact } from './MatchedArtifact';
/**
 * Response schema for artifact matching endpoint.
 *
 * Returns list of artifacts matching the query, sorted by confidence score.
 */
export type MatchResponse = {
  /**
   * Original search query
   */
  query: string;
  /**
   * Matched artifacts ordered by confidence (descending)
   */
  matches: Array<MatchedArtifact>;
  /**
   * Total number of matches before limit applied
   */
  total: number;
  /**
   * Maximum results requested
   */
  limit: number;
  /**
   * Minimum confidence threshold applied
   */
  min_confidence: number;
  /**
   * Schema version for future migrations
   */
  schema_version?: string;
  /**
   * Timestamp when scoring was performed
   */
  scored_at: string;
  /**
   * Whether semantic scoring was unavailable (degraded to keyword-only)
   */
  degraded?: boolean;
  /**
   * Reason for degradation (if degraded=true)
   */
  degradation_reason?: string | null;
};
