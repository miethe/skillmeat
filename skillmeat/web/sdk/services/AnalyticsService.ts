/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AnalyticsSummaryResponse } from '../models/AnalyticsSummaryResponse';
import type { TopArtifactsResponse } from '../models/TopArtifactsResponse';
import type { TrendsResponse } from '../models/TrendsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class AnalyticsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Get analytics summary
     * Retrieve overall statistics and analytics summary
     * @returns AnalyticsSummaryResponse Successfully retrieved analytics summary
     * @throws ApiError
     */
    public getAnalyticsSummaryApiV1AnalyticsSummaryGet(): CancelablePromise<AnalyticsSummaryResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/analytics/summary',
            errors: {
                401: `Unauthorized`,
                503: `Analytics disabled`,
            },
        });
    }
    /**
     * Get top artifacts by usage
     * Retrieve most used artifacts sorted by usage frequency
     * @returns TopArtifactsResponse Successfully retrieved top artifacts
     * @throws ApiError
     */
    public getTopArtifactsApiV1AnalyticsTopArtifactsGet({
        limit = 20,
        after,
        artifactType,
    }: {
        /**
         * Number of items per page (max 100)
         */
        limit?: number,
        /**
         * Cursor for pagination (next page)
         */
        after?: (string | null),
        /**
         * Filter by artifact type (skill, command, agent)
         */
        artifactType?: (string | null),
    }): CancelablePromise<TopArtifactsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/analytics/top-artifacts',
            query: {
                'limit': limit,
                'after': after,
                'artifact_type': artifactType,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                503: `Analytics disabled`,
            },
        });
    }
    /**
     * Get usage trends over time
     * Retrieve time-series usage data for trend analysis
     * @returns TrendsResponse Successfully retrieved usage trends
     * @throws ApiError
     */
    public getUsageTrendsApiV1AnalyticsTrendsGet({
        period = 'day',
        days = 30,
    }: {
        /**
         * Aggregation period (hour, day, week, month)
         */
        period?: string,
        /**
         * Number of days of history (max 365)
         */
        days?: number,
    }): CancelablePromise<TrendsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/analytics/trends',
            query: {
                'period': period,
                'days': days,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                503: `Analytics disabled`,
            },
        });
    }
}
