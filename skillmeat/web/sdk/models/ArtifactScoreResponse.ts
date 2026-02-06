/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for artifact scoring information.
 *
 * Provides complete scoring breakdown including individual factors
 * and composite confidence score.
 */
export type ArtifactScoreResponse = {
  /**
   * Artifact composite key (type:name)
   */
  artifact_id: string;
  /**
   * Source trust/reputation score (0-100)
   */
  trust_score: number;
  /**
   * Aggregated quality score from community ratings (0-100)
   */
  quality_score: number;
  /**
   * Query-specific relevance score (0-100), None if not query-dependent
   */
  match_score?: number | null;
  /**
   * Composite confidence score (weighted combination of factors)
   */
  confidence: number;
  /**
   * Scoring schema version
   */
  schema_version?: string;
  /**
   * Timestamp of last score calculation
   */
  last_updated?: string | null;
};
