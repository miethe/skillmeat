/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeployTemplateRequest } from '../models/DeployTemplateRequest';
import type { DeployTemplateResponse } from '../models/DeployTemplateResponse';
import type { ProjectTemplateCreateRequest } from '../models/ProjectTemplateCreateRequest';
import type { ProjectTemplateListResponse } from '../models/ProjectTemplateListResponse';
import type { ProjectTemplateResponse } from '../models/ProjectTemplateResponse';
import type { ProjectTemplateUpdateRequest } from '../models/ProjectTemplateUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ProjectTemplatesService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List all project templates
     * Retrieve paginated list of project templates with entity counts
     * @returns ProjectTemplateListResponse Successful Response
     * @throws ApiError
     */
    public listTemplatesApiV1ProjectTemplatesGet({
        limit = 50,
        offset,
    }: {
        /**
         * Maximum number of templates to return
         */
        limit?: number,
        /**
         * Number of templates to skip
         */
        offset?: number,
    }): CancelablePromise<ProjectTemplateListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/project-templates',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create new project template
     * Create new template from list of entity IDs
     * @returns ProjectTemplateResponse Template created
     * @throws ApiError
     */
    public createTemplateApiV1ProjectTemplatesPost({
        requestBody,
    }: {
        requestBody: ProjectTemplateCreateRequest,
    }): CancelablePromise<ProjectTemplateResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/project-templates',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid entity IDs`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Get project template by ID
     * Retrieve full template details including entity list
     * @returns ProjectTemplateResponse Template found
     * @throws ApiError
     */
    public getTemplateApiV1ProjectTemplatesTemplateIdGet({
        templateId,
    }: {
        templateId: string,
    }): CancelablePromise<ProjectTemplateResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/project-templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                404: `Template not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update project template
     * Update template name, description, or entity list
     * @returns ProjectTemplateResponse Template updated
     * @throws ApiError
     */
    public updateTemplateApiV1ProjectTemplatesTemplateIdPut({
        templateId,
        requestBody,
    }: {
        templateId: string,
        requestBody: ProjectTemplateUpdateRequest,
    }): CancelablePromise<ProjectTemplateResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/project-templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid entity IDs`,
                404: `Template not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete project template
     * Delete template and all entity associations
     * @returns void
     * @throws ApiError
     */
    public deleteTemplateApiV1ProjectTemplatesTemplateIdDelete({
        templateId,
    }: {
        templateId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/project-templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                404: `Template not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Deploy project template to project path
     * Deploy template entities to target project with variable substitution (optimized for performance)
     * @returns DeployTemplateResponse Template deployed
     * @throws ApiError
     */
    public deployTemplateEndpointApiV1ProjectTemplatesTemplateIdDeployPost({
        templateId,
        requestBody,
    }: {
        templateId: string,
        requestBody: DeployTemplateRequest,
    }): CancelablePromise<DeployTemplateResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/project-templates/{template_id}/deploy',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid project path or deployment failed`,
                404: `Template not found`,
                422: `Validation Error`,
            },
        });
    }
}
