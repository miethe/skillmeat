/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CachedArtifactsListResponse } from '../models/CachedArtifactsListResponse';
import type { CachedProjectsListResponse } from '../models/CachedProjectsListResponse';
import type { CacheInvalidateRequest } from '../models/CacheInvalidateRequest';
import type { CacheInvalidateResponse } from '../models/CacheInvalidateResponse';
import type { CacheRefreshRequest } from '../models/CacheRefreshRequest';
import type { CacheRefreshResponse } from '../models/CacheRefreshResponse';
import type { CacheStatusResponse } from '../models/CacheStatusResponse';
import type { MarketplaceListResponse } from '../models/MarketplaceListResponse';
import type { SearchResultsResponse } from '../models/SearchResultsResponse';
import type { StaleArtifactsListResponse } from '../models/StaleArtifactsListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class CacheService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Trigger cache refresh
     * Manually trigger cache refresh for all projects or a specific project. By default, only refreshes stale projects (past TTL). Use force=true to refresh regardless of staleness.
     * @returns CacheRefreshResponse Successful Response
     * @throws ApiError
     */
    public refreshCacheApiV1CacheRefreshPost({
        requestBody,
    }: {
        requestBody: CacheRefreshRequest,
    }): CancelablePromise<CacheRefreshResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/cache/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get cache status
     * Get comprehensive cache statistics including project/artifact counts, staleness information, and refresh job status.
     * @returns CacheStatusResponse Successful Response
     * @throws ApiError
     */
    public getCacheStatusApiV1CacheStatusGet(): CancelablePromise<CacheStatusResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/cache/status',
        });
    }
    /**
     * List cached projects
     * Get list of cached projects with optional filtering by status.
     * @returns CachedProjectsListResponse Successful Response
     * @throws ApiError
     */
    public listCachedProjectsApiV1CacheProjectsGet({
        status,
        skip,
        limit = 100,
    }: {
        /**
         * Filter by status (active, stale, error)
         */
        status?: (string | null),
        /**
         * Number of items to skip
         */
        skip?: number,
        /**
         * Maximum items to return
         */
        limit?: number,
    }): CancelablePromise<CachedProjectsListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/cache/projects',
            query: {
                'status': status,
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List cached artifacts
     * Get list of cached artifacts with optional filtering by project, type, or outdated status.
     * @returns CachedArtifactsListResponse Successful Response
     * @throws ApiError
     */
    public listCachedArtifactsApiV1CacheArtifactsGet({
        projectId,
        type,
        isOutdated,
        skip,
        limit = 100,
    }: {
        /**
         * Filter by project ID
         */
        projectId?: (string | null),
        /**
         * Filter by artifact type
         */
        type?: (string | null),
        /**
         * Filter by outdated status
         */
        isOutdated?: (boolean | null),
        /**
         * Number of items to skip
         */
        skip?: number,
        /**
         * Maximum items to return
         */
        limit?: number,
    }): CancelablePromise<CachedArtifactsListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/cache/artifacts',
            query: {
                'project_id': projectId,
                'type': type,
                'is_outdated': isOutdated,
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List outdated artifacts
     * Get list of artifacts that have newer upstream versions available with sorting and filtering.
     * @returns StaleArtifactsListResponse Successful Response
     * @throws ApiError
     */
    public listStaleArtifactsApiV1CacheStaleArtifactsGet({
        type,
        projectId,
        sortBy = 'name',
        sortOrder = 'asc',
        skip,
        limit = 100,
    }: {
        /**
         * Filter by artifact type
         */
        type?: (string | null),
        /**
         * Filter by project ID
         */
        projectId?: (string | null),
        /**
         * Sort field (name, type, project, version_diff)
         */
        sortBy?: string,
        /**
         * Sort order (asc, desc)
         */
        sortOrder?: string,
        /**
         * Number of items to skip
         */
        skip?: number,
        /**
         * Maximum items to return
         */
        limit?: number,
    }): CancelablePromise<StaleArtifactsListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/cache/stale-artifacts',
            query: {
                'type': type,
                'project_id': projectId,
                'sort_by': sortBy,
                'sort_order': sortOrder,
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search cached artifacts
     * Search artifacts by name with pagination and sorting. Supports relevance scoring (exact > prefix > contains).
     * @returns SearchResultsResponse Successful Response
     * @throws ApiError
     */
    public searchCacheApiV1CacheSearchGet({
        query,
        projectId,
        type,
        skip,
        limit = 50,
        sortBy = 'relevance',
    }: {
        /**
         * Search query string
         */
        query: string,
        /**
         * Filter by project ID
         */
        projectId?: (string | null),
        /**
         * Filter by artifact type
         */
        type?: (string | null),
        /**
         * Number of items to skip
         */
        skip?: number,
        /**
         * Maximum items to return
         */
        limit?: number,
        /**
         * Sort order (relevance, name, type, updated)
         */
        sortBy?: string,
    }): CancelablePromise<SearchResultsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/cache/search',
            query: {
                'query': query,
                'project_id': projectId,
                'type': type,
                'skip': skip,
                'limit': limit,
                'sort_by': sortBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Invalidate cache
     * Mark cache as stale to force refresh on next access. Can invalidate entire cache or specific project.
     * @returns CacheInvalidateResponse Successful Response
     * @throws ApiError
     */
    public invalidateCacheApiV1CacheInvalidatePost({
        requestBody,
    }: {
        requestBody: CacheInvalidateRequest,
    }): CancelablePromise<CacheInvalidateResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/cache/invalidate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get cached marketplace entries
     * Get list of cached marketplace artifact entries with optional filtering by artifact type. Returns cached data with 24-hour TTL.
     * @returns MarketplaceListResponse Successful Response
     * @throws ApiError
     */
    public getMarketplaceCacheApiV1CacheMarketplaceGet({
        type,
        skip,
        limit = 100,
    }: {
        /**
         * Filter by artifact type
         */
        type?: (string | null),
        /**
         * Number of items to skip
         */
        skip?: number,
        /**
         * Maximum items to return
         */
        limit?: number,
    }): CancelablePromise<MarketplaceListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/cache/marketplace',
            query: {
                'type': type,
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
