/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactCreateRequest } from '../models/ArtifactCreateRequest';
import type { ArtifactCreateResponse } from '../models/ArtifactCreateResponse';
import type { ArtifactDeployRequest } from '../models/ArtifactDeployRequest';
import type { ArtifactDeployResponse } from '../models/ArtifactDeployResponse';
import type { ArtifactDiffResponse } from '../models/ArtifactDiffResponse';
import type { ArtifactListResponse } from '../models/ArtifactListResponse';
import type { ArtifactResponse } from '../models/ArtifactResponse';
import type { ArtifactSyncRequest } from '../models/ArtifactSyncRequest';
import type { ArtifactSyncResponse } from '../models/ArtifactSyncResponse';
import type { ArtifactUpdateRequest } from '../models/ArtifactUpdateRequest';
import type { ArtifactUpstreamResponse } from '../models/ArtifactUpstreamResponse';
import type { Body_undeploy_artifact_api_v1_artifacts__artifact_id__undeploy_post } from '../models/Body_undeploy_artifact_api_v1_artifacts__artifact_id__undeploy_post';
import type { VersionGraphResponse } from '../models/VersionGraphResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ArtifactsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Create new artifact
     * Create a new artifact from GitHub URL or local path
     * @returns ArtifactCreateResponse Artifact created successfully
     * @throws ApiError
     */
    public createArtifactApiV1ArtifactsPost({
        requestBody,
    }: {
        requestBody: ArtifactCreateRequest,
    }): CancelablePromise<ArtifactCreateResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/artifacts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Source not found`,
                409: `Artifact already exists`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * List all artifacts
     * Retrieve a paginated list of artifacts across all collections
     * @returns ArtifactListResponse Successfully retrieved artifacts
     * @throws ApiError
     */
    public listArtifactsApiV1ArtifactsGet({
        limit = 20,
        after,
        artifactType,
        collection,
        tags,
        checkDrift = false,
        projectPath,
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
        /**
         * Filter by collection name
         */
        collection?: (string | null),
        /**
         * Filter by tags (comma-separated)
         */
        tags?: (string | null),
        /**
         * Check for local modifications and drift status (may impact performance)
         */
        checkDrift?: boolean,
        /**
         * Project path for drift detection (required if check_drift=true)
         */
        projectPath?: (string | null),
    }): CancelablePromise<ArtifactListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/artifacts',
            query: {
                'limit': limit,
                'after': after,
                'artifact_type': artifactType,
                'collection': collection,
                'tags': tags,
                'check_drift': checkDrift,
                'project_path': projectPath,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get artifact details
     * Retrieve detailed information about a specific artifact
     * @returns ArtifactResponse Successfully retrieved artifact
     * @throws ApiError
     */
    public getArtifactApiV1ArtifactsArtifactIdGet({
        artifactId,
        collection,
        includeDeployments = false,
    }: {
        artifactId: string,
        /**
         * Collection name (searches all if not specified)
         */
        collection?: (string | null),
        /**
         * Include deployment statistics across all projects
         */
        includeDeployments?: boolean,
    }): CancelablePromise<ArtifactResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/artifacts/{artifact_id}',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
                'include_deployments': includeDeployments,
            },
            errors: {
                401: `Unauthorized`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Update artifact
     * Update artifact metadata, tags, and aliases
     * @returns ArtifactResponse Successfully updated artifact
     * @throws ApiError
     */
    public updateArtifactApiV1ArtifactsArtifactIdPut({
        artifactId,
        requestBody,
        collection,
    }: {
        artifactId: string,
        requestBody: ArtifactUpdateRequest,
        /**
         * Collection name (searches all if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<ArtifactResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/artifacts/{artifact_id}',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete artifact
     * Remove an artifact from the collection
     * @returns void
     * @throws ApiError
     */
    public deleteArtifactApiV1ArtifactsArtifactIdDelete({
        artifactId,
        collection,
    }: {
        artifactId: string,
        /**
         * Collection name (searches all if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/artifacts/{artifact_id}',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
            },
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Check upstream status
     * Check for updates and upstream status for an artifact
     * @returns ArtifactUpstreamResponse Successfully checked upstream status
     * @throws ApiError
     */
    public checkArtifactUpstreamApiV1ArtifactsArtifactIdUpstreamGet({
        artifactId,
        collection,
    }: {
        artifactId: string,
        /**
         * Collection name (searches all if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<ArtifactUpstreamResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/artifacts/{artifact_id}/upstream',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
            },
            errors: {
                401: `Unauthorized`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Deploy artifact to project
     * Deploy artifact from collection to project's .claude/ directory
     * @returns ArtifactDeployResponse Artifact deployed successfully
     * @throws ApiError
     */
    public deployArtifactApiV1ArtifactsArtifactIdDeployPost({
        artifactId,
        requestBody,
        collection,
    }: {
        artifactId: string,
        requestBody: ArtifactDeployRequest,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<ArtifactDeployResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/artifacts/{artifact_id}/deploy',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Sync artifact from project to collection
     * Pull changes from project back to collection, with conflict resolution
     * @returns ArtifactSyncResponse Artifact synced successfully
     * @throws ApiError
     */
    public syncArtifactApiV1ArtifactsArtifactIdSyncPost({
        artifactId,
        requestBody,
        collection,
    }: {
        artifactId: string,
        requestBody: ArtifactSyncRequest,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<ArtifactSyncResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/artifacts/{artifact_id}/sync',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Undeploy artifact from project
     * Remove deployed artifact from project's .claude/ directory
     * @returns ArtifactDeployResponse Artifact undeployed successfully
     * @throws ApiError
     */
    public undeployArtifactApiV1ArtifactsArtifactIdUndeployPost({
        artifactId,
        requestBody,
        collection,
    }: {
        artifactId: string,
        requestBody: Body_undeploy_artifact_api_v1_artifacts__artifact_id__undeploy_post,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<ArtifactDeployResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/artifacts/{artifact_id}/undeploy',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                '_collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get artifact version graph
     * Build and return version graph showing deployment hierarchy across all projects
     * @returns VersionGraphResponse Successfully retrieved version graph
     * @throws ApiError
     */
    public getVersionGraphApiV1ArtifactsArtifactIdVersionGraphGet({
        artifactId,
        collection,
    }: {
        artifactId: string,
        /**
         * Filter to specific collection
         */
        collection?: (string | null),
    }): CancelablePromise<VersionGraphResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/artifacts/{artifact_id}/version-graph',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'collection': collection,
            },
            errors: {
                401: `Unauthorized`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get artifact diff
     * Compare artifact versions between collection and deployed project
     * @returns ArtifactDiffResponse Successfully retrieved diff
     * @throws ApiError
     */
    public getArtifactDiffApiV1ArtifactsArtifactIdDiffGet({
        artifactId,
        projectPath,
        collection,
    }: {
        artifactId: string,
        /**
         * Path to project for comparison
         */
        projectPath: string,
        /**
         * Collection name (searches all if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<ArtifactDiffResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/artifacts/{artifact_id}/diff',
            path: {
                'artifact_id': artifactId,
            },
            query: {
                'project_path': projectPath,
                'collection': collection,
            },
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Artifact not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
