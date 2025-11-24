/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ModificationCheckResponse } from '../models/ModificationCheckResponse';
import type { ModifiedArtifactsResponse } from '../models/ModifiedArtifactsResponse';
import type { ProjectCreateRequest } from '../models/ProjectCreateRequest';
import type { ProjectCreateResponse } from '../models/ProjectCreateResponse';
import type { ProjectDeleteResponse } from '../models/ProjectDeleteResponse';
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
    }: {
        /**
         * Number of items per page (max 100)
         */
        limit?: number,
        /**
         * Cursor for pagination (next page)
         */
        after?: (string | null),
    }): CancelablePromise<ProjectListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/projects',
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
}
