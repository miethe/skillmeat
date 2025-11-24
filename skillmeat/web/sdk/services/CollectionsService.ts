/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CollectionArtifactsResponse } from '../models/CollectionArtifactsResponse';
import type { CollectionListResponse } from '../models/CollectionListResponse';
import type { CollectionResponse } from '../models/CollectionResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class CollectionsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List all collections
     * Retrieve a paginated list of all collections with metadata
     * @returns CollectionListResponse Successfully retrieved collections
     * @throws ApiError
     */
    public listCollectionsApiV1CollectionsGet({
        limit = 20,
        after,
    }: {
        /**
         * Number of items per page (max 100)
         */
        limit?: number,
        /**
         * Cursor for pagination (next page)
         */
        after?: (string | null),
    }): CancelablePromise<CollectionListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/collections',
            query: {
                'limit': limit,
                'after': after,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get collection details
     * Retrieve detailed information about a specific collection
     * @returns CollectionResponse Successfully retrieved collection
     * @throws ApiError
     */
    public getCollectionApiV1CollectionsCollectionIdGet({
        collectionId,
    }: {
        collectionId: string,
    }): CancelablePromise<CollectionResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/collections/{collection_id}',
            path: {
                'collection_id': collectionId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * List artifacts in collection
     * Retrieve a paginated list of artifacts within a specific collection
     * @returns CollectionArtifactsResponse Successfully retrieved artifacts
     * @throws ApiError
     */
    public listCollectionArtifactsApiV1CollectionsCollectionIdArtifactsGet({
        collectionId,
        limit = 20,
        after,
        artifactType,
    }: {
        collectionId: string,
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
    }): CancelablePromise<CollectionArtifactsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/collections/{collection_id}/artifacts',
            path: {
                'collection_id': collectionId,
            },
            query: {
                'limit': limit,
                'after': after,
                'artifact_type': artifactType,
            },
            errors: {
                401: `Unauthorized`,
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
