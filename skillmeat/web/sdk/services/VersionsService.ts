/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RollbackRequest } from '../models/RollbackRequest';
import type { RollbackResponse } from '../models/RollbackResponse';
import type { RollbackSafetyAnalysisResponse } from '../models/RollbackSafetyAnalysisResponse';
import type { SnapshotCreateRequest } from '../models/SnapshotCreateRequest';
import type { SnapshotCreateResponse } from '../models/SnapshotCreateResponse';
import type { SnapshotListResponse } from '../models/SnapshotListResponse';
import type { SnapshotResponse } from '../models/SnapshotResponse';
import type { VersionDiffRequest } from '../models/VersionDiffRequest';
import type { VersionDiffResponse } from '../models/VersionDiffResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class VersionsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List snapshots
     * Retrieve a paginated list of collection snapshots
     * @returns SnapshotListResponse Successfully retrieved snapshots
     * @throws ApiError
     */
    public listSnapshotsApiV1VersionsSnapshotsGet({
        collectionName,
        limit = 20,
        after,
    }: {
        /**
         * Collection name (uses active collection if not specified)
         */
        collectionName?: (string | null),
        /**
         * Number of items per page (max 100)
         */
        limit?: number,
        /**
         * Cursor for pagination (next page)
         */
        after?: (string | null),
    }): CancelablePromise<SnapshotListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/versions/snapshots',
            query: {
                'collection_name': collectionName,
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
     * Create snapshot
     * Create a new snapshot of a collection
     * @returns SnapshotCreateResponse Successfully created snapshot
     * @throws ApiError
     */
    public createSnapshotApiV1VersionsSnapshotsPost({
        requestBody,
    }: {
        requestBody: SnapshotCreateRequest,
    }): CancelablePromise<SnapshotCreateResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/versions/snapshots',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Unauthorized`,
                404: `Collection not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get snapshot details
     * Retrieve detailed information about a specific snapshot
     * @returns SnapshotResponse Successfully retrieved snapshot
     * @throws ApiError
     */
    public getSnapshotApiV1VersionsSnapshotsSnapshotIdGet({
        snapshotId,
        collectionName,
    }: {
        snapshotId: string,
        /**
         * Collection name (uses active collection if not specified)
         */
        collectionName?: (string | null),
    }): CancelablePromise<SnapshotResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/versions/snapshots/{snapshot_id}',
            path: {
                'snapshot_id': snapshotId,
            },
            query: {
                'collection_name': collectionName,
            },
            errors: {
                401: `Unauthorized`,
                404: `Snapshot not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete snapshot
     * Delete a specific snapshot
     * @returns void
     * @throws ApiError
     */
    public deleteSnapshotApiV1VersionsSnapshotsSnapshotIdDelete({
        snapshotId,
        collectionName,
    }: {
        snapshotId: string,
        /**
         * Collection name (uses active collection if not specified)
         */
        collectionName?: (string | null),
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/versions/snapshots/{snapshot_id}',
            path: {
                'snapshot_id': snapshotId,
            },
            query: {
                'collection_name': collectionName,
            },
            errors: {
                401: `Unauthorized`,
                404: `Snapshot not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Analyze rollback safety
     * Analyze potential conflicts and safety before executing rollback
     * @returns RollbackSafetyAnalysisResponse Successfully analyzed rollback safety
     * @throws ApiError
     */
    public analyzeRollbackSafetyApiV1VersionsSnapshotsSnapshotIdRollbackAnalysisGet({
        snapshotId,
        collectionName,
    }: {
        snapshotId: string,
        /**
         * Collection name (uses active collection if not specified)
         */
        collectionName?: (string | null),
    }): CancelablePromise<RollbackSafetyAnalysisResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/versions/snapshots/{snapshot_id}/rollback-analysis',
            path: {
                'snapshot_id': snapshotId,
            },
            query: {
                'collection_name': collectionName,
            },
            errors: {
                401: `Unauthorized`,
                404: `Snapshot not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Execute rollback
     * Rollback to a specific snapshot with optional intelligent merge
     * @returns RollbackResponse Successfully executed rollback
     * @throws ApiError
     */
    public rollbackApiV1VersionsSnapshotsSnapshotIdRollbackPost({
        snapshotId,
        requestBody,
    }: {
        snapshotId: string,
        requestBody: RollbackRequest,
    }): CancelablePromise<RollbackResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/versions/snapshots/{snapshot_id}/rollback',
            path: {
                'snapshot_id': snapshotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Unauthorized`,
                404: `Snapshot not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Compare snapshots
     * Generate a diff showing changes between two snapshots
     * @returns VersionDiffResponse Successfully generated diff
     * @throws ApiError
     */
    public diffSnapshotsApiV1VersionsSnapshotsDiffPost({
        requestBody,
    }: {
        requestBody: VersionDiffRequest,
    }): CancelablePromise<VersionDiffResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/versions/snapshots/diff',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Unauthorized`,
                404: `Snapshot not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
