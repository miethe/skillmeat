/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactScoreResponse } from '../models/ArtifactScoreResponse';
import type { UserRatingRequest } from '../models/UserRatingRequest';
import type { UserRatingResponse } from '../models/UserRatingResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class RatingsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Submit artifact rating
     * Submit a rating for an artifact (1-5 scale).
     *
     * Rate limits apply: maximum 5 ratings per artifact per user per day.
     * Ratings can optionally be shared with the community for aggregate scoring.
     * @returns UserRatingResponse Rating submitted successfully
     * @throws ApiError
     */
    public submitRatingApiV1RatingsArtifactsArtifactIdRatingsPost({
        artifactId,
        requestBody,
    }: {
        artifactId: string,
        requestBody: UserRatingRequest,
    }): CancelablePromise<UserRatingResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/ratings/artifacts/{artifact_id}/ratings',
            path: {
                'artifact_id': artifactId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid rating value`,
                422: `Validation Error`,
                429: `Rate limit exceeded`,
            },
        });
    }
    /**
     * List artifact ratings
     * Get all ratings for an artifact, ordered by most recent first.
     * @returns any Ratings retrieved successfully
     * @throws ApiError
     */
    public listArtifactRatingsApiV1RatingsArtifactsArtifactIdRatingsGet({
        artifactId,
        limit = 50,
    }: {
        artifactId: string,
        /**
         * Maximum ratings to return
         */
        limit?: number,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/ratings/artifacts/{artifact_id}/ratings',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get artifact scores
     * Get confidence scores for an artifact.
     *
     * Returns trust score, quality score, and composite confidence.
     * Match score is only included when querying with a search context.
     * @returns ArtifactScoreResponse Scores retrieved successfully
     * @throws ApiError
     */
    public getArtifactScoresApiV1RatingsArtifactsArtifactIdScoresGet({
        artifactId,
        sourceType,
        matchScore,
    }: {
        artifactId: string,
        /**
         * Source type for trust scoring (official, verified, github, local, unknown)
         */
        sourceType?: (string | null),
        /**
         * Query match score from search context (0-100)
         */
        matchScore?: (number | null),
    }): CancelablePromise<ArtifactScoreResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/ratings/artifacts/{artifact_id}/scores',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'source_type': sourceType,
                'match_score': matchScore,
            },
            errors: {
                404: `Artifact not found`,
                422: `Validation Error`,
            },
        });
    }
}
