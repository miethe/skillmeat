/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Detailed breakdown of scoring components.
 *
 * Provides transparency into how the confidence score was calculated.
 */
export type ScoreBreakdown = {
  /**
   * Source trust/reputation score (0-100)
   */
  trust_score: number;
  /**
   * Aggregated quality score from community ratings (0-100)
   */
  quality_score: number;
  /**
   * Query-specific relevance score (0-100)
   */
  match_score: number;
  /**
   * Whether semantic embeddings were used for matching
   */
  semantic_used?: boolean;
  /**
   * Whether contextual boost was applied to score
   */
  context_boost_applied?: boolean;
};
