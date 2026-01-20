/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MatchResponse } from '../models/MatchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MatchService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Match artifacts against query
   * Search for artifacts matching a query using confidence scoring.
   *
   * This endpoint uses semantic embeddings when available, with graceful
   * degradation to keyword-only matching. Results are sorted by confidence
   * score (descending).
   *
   * The confidence score combines:
   * - Trust score: Source reputation/verification
   * - Quality score: Community ratings and metrics
   * - Match score: Semantic + keyword relevance to query
   *
   * Semantic matching provides better results but requires API key.
   * Keyword-only mode works without configuration.
   * @returns MatchResponse Matches found (may be empty list)
   * @throws ApiError
   */
  public matchArtifactsApiV1MatchGet({
    q,
    limit = 10,
    minConfidence,
    includeBreakdown = false,
  }: {
    /**
     * Search query
     */
    q: string;
    /**
     * Maximum results to return
     */
    limit?: number;
    /**
     * Minimum confidence score threshold
     */
    minConfidence?: number;
    /**
     * Include detailed score breakdown for each match
     */
    includeBreakdown?: boolean;
  }): CancelablePromise<MatchResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/match/',
      query: {
        q: q,
        limit: limit,
        min_confidence: minConfidence,
        include_breakdown: includeBreakdown,
      },
      errors: {
        400: `Invalid query (empty or too short)`,
        422: `Validation Error`,
        500: `Scoring service error`,
      },
    });
  }
}
