/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AddArtifactsRequest } from '../models/AddArtifactsRequest';
import type { skillmeat__api__schemas__user_collections__CollectionArtifactsResponse } from '../models/skillmeat__api__schemas__user_collections__CollectionArtifactsResponse';
import type { UserCollectionCreateRequest } from '../models/UserCollectionCreateRequest';
import type { UserCollectionListResponse } from '../models/UserCollectionListResponse';
import type { UserCollectionResponse } from '../models/UserCollectionResponse';
import type { UserCollectionUpdateRequest } from '../models/UserCollectionUpdateRequest';
import type { UserCollectionWithGroupsResponse } from '../models/UserCollectionWithGroupsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class UserCollectionsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List all user collections
     * Retrieve a paginated list of all user-defined collections
     * @returns UserCollectionListResponse Successfully retrieved collections
     * @throws ApiError
     */
    public listUserCollectionsApiV1UserCollectionsGet({
        limit = 20,
        after,
        search,
        collectionType,
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
         * Filter by collection name (case-insensitive)
         */
        search?: (string | null),
        /**
         * Filter by collection type (e.g., 'context')
         */
        collectionType?: (string | null),
    }): CancelablePromise<UserCollectionListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/user-collections',
            query: {
                'limit': limit,
                'after': after,
                'search': search,
                'collection_type': collectionType,
            },
            errors: {
                400: `Invalid parameters`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Create new user collection
     * Create a new user-defined collection
     * @returns UserCollectionResponse Successfully created collection
     * @throws ApiError
     */
    public createUserCollectionApiV1UserCollectionsPost({
        requestBody,
    }: {
        requestBody: UserCollectionCreateRequest,
    }): CancelablePromise<UserCollectionResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/user-collections',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                409: `Collection name already exists`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get user collection details
     * Retrieve detailed information about a specific collection including groups
     * @returns UserCollectionWithGroupsResponse Successfully retrieved collection
     * @throws ApiError
     */
    public getUserCollectionApiV1UserCollectionsCollectionIdGet({
        collectionId,
    }: {
        collectionId: string,
    }): CancelablePromise<UserCollectionWithGroupsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/user-collections/{collection_id}',
            path: {
                'collection_id': collectionId,
            },
            errors: {
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Update user collection
     * Update collection metadata (partial update supported)
     * @returns UserCollectionResponse Successfully updated collection
     * @throws ApiError
     */
    public updateUserCollectionApiV1UserCollectionsCollectionIdPut({
        collectionId,
        requestBody,
    }: {
        collectionId: string,
        requestBody: UserCollectionUpdateRequest,
    }): CancelablePromise<UserCollectionResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/user-collections/{collection_id}',
            path: {
                'collection_id': collectionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                404: `Collection not found`,
                409: `Collection name already exists`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete user collection
     * Delete a collection and all its groups and artifact associations
     * @returns void
     * @throws ApiError
     */
    public deleteUserCollectionApiV1UserCollectionsCollectionIdDelete({
        collectionId,
    }: {
        collectionId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/user-collections/{collection_id}',
            path: {
                'collection_id': collectionId,
            },
            errors: {
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * List artifacts in collection
     * Retrieve paginated list of artifacts in a collection with optional type filtering
     * @returns skillmeat__api__schemas__user_collections__CollectionArtifactsResponse Successfully retrieved artifacts
     * @throws ApiError
     */
    public listCollectionArtifactsApiV1UserCollectionsCollectionIdArtifactsGet({
        collectionId,
        limit = 20,
        after,
        artifactType,
    }: {
        collectionId: string,
        limit?: number,
        after?: (string | null),
        /**
         * Filter by artifact type
         */
        artifactType?: (string | null),
    }): CancelablePromise<skillmeat__api__schemas__user_collections__CollectionArtifactsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/user-collections/{collection_id}/artifacts',
            path: {
                'collection_id': collectionId,
            },
            query: {
                'limit': limit,
                'after': after,
                'artifact_type': artifactType,
            },
            errors: {
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Add artifacts to collection
     * Add one or more artifacts to a collection (idempotent)
     * @returns any Artifacts already in collection (idempotent)
     * @throws ApiError
     */
    public addArtifactsToCollectionApiV1UserCollectionsCollectionIdArtifactsPost({
        collectionId,
        requestBody,
    }: {
        collectionId: string,
        requestBody: AddArtifactsRequest,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/user-collections/{collection_id}/artifacts',
            path: {
                'collection_id': collectionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Remove artifact from collection
     * Remove an artifact from a collection (idempotent)
     * @returns void
     * @throws ApiError
     */
    public removeArtifactFromCollectionApiV1UserCollectionsCollectionIdArtifactsArtifactIdDelete({
        collectionId,
        artifactId,
    }: {
        collectionId: string,
        artifactId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/user-collections/{collection_id}/artifacts/{artifact_id}',
            path: {
                'collection_id': collectionId,
                'artifact_id': artifactId,
            },
            errors: {
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Add entity to collection
     * Add a context entity to a collection (idempotent)
     * @returns any Entity already in collection (idempotent)
     * @throws ApiError
     */
    public addEntityToCollectionApiV1UserCollectionsCollectionIdEntitiesEntityIdPost({
        collectionId,
        entityId,
    }: {
        collectionId: string,
        entityId: string,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/user-collections/{collection_id}/entities/{entity_id}',
            path: {
                'collection_id': collectionId,
                'entity_id': entityId,
            },
            errors: {
                404: `Collection or entity not found`,
                409: `Entity already exists in collection`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Remove entity from collection
     * Remove a context entity from a collection (idempotent)
     * @returns void
     * @throws ApiError
     */
    public removeEntityFromCollectionApiV1UserCollectionsCollectionIdEntitiesEntityIdDelete({
        collectionId,
        entityId,
    }: {
        collectionId: string,
        entityId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/user-collections/{collection_id}/entities/{entity_id}',
            path: {
                'collection_id': collectionId,
                'entity_id': entityId,
            },
            errors: {
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * List entities in collection
     * Retrieve paginated list of context entities in a collection
     * @returns skillmeat__api__schemas__user_collections__CollectionArtifactsResponse Successfully retrieved entities
     * @throws ApiError
     */
    public listCollectionEntitiesApiV1UserCollectionsCollectionIdEntitiesGet({
        collectionId,
        limit = 20,
        after,
    }: {
        collectionId: string,
        limit?: number,
        after?: (string | null),
    }): CancelablePromise<skillmeat__api__schemas__user_collections__CollectionArtifactsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/user-collections/{collection_id}/entities',
            path: {
                'collection_id': collectionId,
            },
            query: {
                'limit': limit,
                'after': after,
            },
            errors: {
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
