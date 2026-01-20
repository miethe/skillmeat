/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextMapResponse } from '../models/ContextMapResponse';
import type { DriftSummaryResponse } from '../models/DriftSummaryResponse';
import type { ModificationCheckResponse } from '../models/ModificationCheckResponse';
import type { ModifiedArtifactsResponse } from '../models/ModifiedArtifactsResponse';
import type { ProjectCreateRequest } from '../models/ProjectCreateRequest';
import type { ProjectCreateResponse } from '../models/ProjectCreateResponse';
import type { ProjectDeleteResponse } from '../models/ProjectDeleteResponse';
import type { ProjectDeploymentRemovalResponse } from '../models/ProjectDeploymentRemovalResponse';
import type { ProjectDetail } from '../models/ProjectDetail';
import type { ProjectListResponse } from '../models/ProjectListResponse';
import type { ProjectUpdateRequest } from '../models/ProjectUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ProjectsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List all projects
     * Discover and list all projects with deployed artifacts
     * @returns ProjectListResponse Successfully retrieved projects
     * @throws ApiError
     */
    public listProjectsApiV1ProjectsGet({
        limit = 20,
        after,
        refresh = false,
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
         * Force cache refresh (bypass cached results)
         */
        refresh?: boolean,
    }): CancelablePromise<ProjectListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects',
            query: {
                'limit': limit,
                'after': after,
                'refresh': refresh,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Create new project
     * Create a new project by initializing the directory structure and metadata
     * @returns ProjectCreateResponse Project created successfully
     * @throws ApiError
     */
    public createProjectApiV1ProjectsPost({
        requestBody,
    }: {
        requestBody: ProjectCreateRequest,
    }): CancelablePromise<ProjectCreateResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/projects',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request or project already exists`,
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get project details
     * Retrieve detailed information about a specific project including all deployments
     * @returns ProjectDetail Successfully retrieved project
     * @throws ApiError
     */
    public getProjectApiV1ProjectsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ProjectDetail> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Update project metadata
     * Update project name and/or description
     * @returns ProjectDetail Project updated successfully
     * @throws ApiError
     */
    public updateProjectApiV1ProjectsProjectIdPut({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ProjectUpdateRequest,
    }): CancelablePromise<ProjectDetail> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete project
     * Remove project from tracking and optionally delete files from disk
     * @returns ProjectDeleteResponse Project deleted successfully
     * @throws ApiError
     */
    public deleteProjectApiV1ProjectsProjectIdDelete({
        projectId,
        deleteFiles = false,
    }: {
        projectId: string,
        /**
         * If true, delete project files from disk (WARNING: destructive operation)
         */
        deleteFiles?: boolean,
    }): CancelablePromise<ProjectDeleteResponse> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            query: {
                'delete_files': deleteFiles,
            },
            errors: {
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Remove deployment from project
     * Remove a specific artifact deployment from a project
     * @returns ProjectDeploymentRemovalResponse Deployment removed successfully
     * @throws ApiError
     */
    public removeProjectDeploymentApiV1ProjectsProjectIdDeploymentsArtifactNameDelete({
        projectId,
        artifactName,
        artifactType,
        removeFiles = true,
    }: {
        projectId: string,
        artifactName: string,
        /**
         * Type of the artifact to remove
         */
        artifactType: string,
        /**
         * Whether to remove files from filesystem (default: True)
         */
        removeFiles?: boolean,
    }): CancelablePromise<ProjectDeploymentRemovalResponse> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/projects/{project_id}/deployments/{artifact_name}',
            path: {
                'project_id': projectId,
                'artifact_name': artifactName,
            },
            query: {
                'artifact_type': artifactType,
                'remove_files': removeFiles,
            },
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Project or deployment not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Check for artifact modifications
     * Scan all deployments in a project and detect local modifications by comparing content hashes
     * @returns ModificationCheckResponse Successfully checked for modifications
     * @throws ApiError
     */
    public checkProjectModificationsApiV1ProjectsProjectIdCheckModificationsPost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ModificationCheckResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/projects/{project_id}/check-modifications',
            path: {
                'project_id': projectId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get modified artifacts
     * List all artifacts in a project that have been modified since deployment
     * @returns ModifiedArtifactsResponse Successfully retrieved modified artifacts
     * @throws ApiError
     */
    public getModifiedArtifactsApiV1ProjectsProjectIdModifiedArtifactsGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ModifiedArtifactsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects/{project_id}/modified-artifacts',
            path: {
                'project_id': projectId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Discover context entities in project
     * Scan a project's .claude/ directory to discover context entities (specs, rules, context files) with token estimates for progressive disclosure
     * @returns ContextMapResponse Successfully discovered context entities
     * @throws ApiError
     */
    public getProjectContextMapApiV1ProjectsProjectIdContextMapGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ContextMapResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects/{project_id}/context-map',
            path: {
                'project_id': projectId,
            },
            errors: {
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get drift detection summary
     * Detect drift between project and collection with summary counts
     * @returns DriftSummaryResponse Successfully detected drift
     * @throws ApiError
     */
    public getProjectDriftSummaryApiV1ProjectsProjectIdDriftSummaryGet({
        projectId,
        collectionName,
    }: {
        projectId: string,
        /**
         * Collection name to compare against (defaults to deployed collection)
         */
        collectionName?: (string | null),
    }): CancelablePromise<DriftSummaryResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects/{project_id}/drift/summary',
            path: {
                'project_id': projectId,
            },
            query: {
                'collection_name': collectionName,
            },
            errors: {
                401: `Unauthorized`,
                404: `Project not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Clear project cache
     * Clear the persistent SQLite cache and force full project rediscovery
     * @returns any Cache cleared successfully
     * @throws ApiError
     */
    public clearProjectCacheApiV1ProjectsCacheClearPost(): CancelablePromise<Record<string, any>> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/projects/cache/clear',
            errors: {
                500: `Cache manager not available`,
            },
        });
    }
    /**
     * Refresh project cache
     * Force a full refresh of the project discovery cache
     * @returns any Cache refreshed successfully
     * @throws ApiError
     */
    public refreshCacheApiV1ProjectsCacheRefreshPost(): CancelablePromise<Record<string, any>> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/projects/cache/refresh',
            errors: {
                401: `Unauthorized`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get cache statistics
     * Get statistics about the project discovery cache
     * @returns any Cache statistics
     * @throws ApiError
     */
    public getCacheStatsApiV1ProjectsCacheStatsGet(): CancelablePromise<Record<string, any>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects/cache/stats',
            errors: {
                401: `Unauthorized`,
            },
        });
    }
}
