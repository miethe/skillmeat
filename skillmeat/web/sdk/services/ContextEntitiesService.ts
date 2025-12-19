/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextEntityCreateRequest } from '../models/ContextEntityCreateRequest';
import type { ContextEntityListResponse } from '../models/ContextEntityListResponse';
import type { ContextEntityResponse } from '../models/ContextEntityResponse';
import type { ContextEntityType } from '../models/ContextEntityType';
import type { ContextEntityUpdateRequest } from '../models/ContextEntityUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ContextEntitiesService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List all context entities
     * Retrieve a paginated list of all context entities with optional filtering.
     *
     * Query parameters allow filtering by:
     * - entity_type: Filter by type (project_config, spec_file, etc.)
     * - category: Filter by category (api, web, debugging, etc.)
     * - auto_load: Filter by auto-load setting (true/false)
     * - search: Search in name, description, or path_pattern
     *
     * Results are returned with cursor-based pagination for efficient large-scale queries.
     * @returns ContextEntityListResponse Successfully retrieved context entities
     * @throws ApiError
     */
    public listContextEntitiesApiV1ContextEntitiesGet({
        entityType,
        category,
        autoLoad,
        search,
        limit = 20,
        after,
    }: {
        /**
         * Filter by entity type
         */
        entityType?: (ContextEntityType | null),
        /**
         * Filter by category
         */
        category?: (string | null),
        /**
         * Filter by auto-load setting
         */
        autoLoad?: (boolean | null),
        /**
         * Search in name, description, or path_pattern
         */
        search?: (string | null),
        /**
         * Number of items per page (max 100)
         */
        limit?: number,
        /**
         * Cursor for pagination (next page)
         */
        after?: (string | null),
    }): CancelablePromise<ContextEntityListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/context-entities',
            query: {
                'entity_type': entityType,
                'category': category,
                'auto_load': autoLoad,
                'search': search,
                'limit': limit,
                'after': after,
            },
            errors: {
                400: `Invalid query parameters`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Create new context entity
     * Create a new context entity with validation.
     *
     * The content will be validated according to the entity type:
     * - ProjectConfig: Markdown with optional frontmatter
     * - SpecFile: YAML frontmatter (with 'title') + markdown
     * - RuleFile: Markdown with optional path scope comment
     * - ContextFile: YAML frontmatter (with 'references') + markdown
     * - ProgressTemplate: YAML frontmatter (with 'type: progress') + markdown
     *
     * Path pattern must start with '.claude/' and cannot contain '..' for security.
     * Content hash is computed automatically for change detection.
     * @returns ContextEntityResponse Context entity created successfully
     * @throws ApiError
     */
    public createContextEntityApiV1ContextEntitiesPost({
        requestBody,
    }: {
        requestBody: ContextEntityCreateRequest,
    }): CancelablePromise<ContextEntityResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/context-entities',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation error`,
                422: `Unprocessable entity (schema validation failed)`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get context entity details
     * Retrieve detailed information about a specific context entity by ID.
     *
     * Returns full entity metadata including:
     * - Name, type, and description
     * - Path pattern and auto-load settings
     * - Category for progressive disclosure
     * - Version and content hash
     * - Created/updated timestamps
     * @returns ContextEntityResponse Successfully retrieved context entity
     * @throws ApiError
     */
    public getContextEntityApiV1ContextEntitiesEntityIdGet({
        entityId,
    }: {
        entityId: string,
    }): CancelablePromise<ContextEntityResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/context-entities/{entity_id}',
            path: {
                'entity_id': entityId,
            },
            errors: {
                404: `Context entity not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Update context entity
     * Update an existing context entity.
     *
     * All fields are optional - only provided fields will be updated.
     * If content is updated, the content_hash will be recomputed automatically.
     * Updated content is validated according to the entity type (or new type if changed).
     * @returns ContextEntityResponse Context entity updated successfully
     * @throws ApiError
     */
    public updateContextEntityApiV1ContextEntitiesEntityIdPut({
        entityId,
        requestBody,
    }: {
        entityId: string,
        requestBody: ContextEntityUpdateRequest,
    }): CancelablePromise<ContextEntityResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/context-entities/{entity_id}',
            path: {
                'entity_id': entityId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation error`,
                404: `Context entity not found`,
                422: `Unprocessable entity (schema validation failed)`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete context entity
     * Delete a context entity from the database.
     *
     * This is a permanent operation and cannot be undone.
     * The entity's content will be lost unless backed up elsewhere.
     * @returns void
     * @throws ApiError
     */
    public deleteContextEntityApiV1ContextEntitiesEntityIdDelete({
        entityId,
    }: {
        entityId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/context-entities/{entity_id}',
            path: {
                'entity_id': entityId,
            },
            errors: {
                404: `Context entity not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get raw markdown content
     * Retrieve the raw markdown content of a context entity.
     *
     * Returns the content as text/plain for easy downloading or previewing.
     * Useful for:
     * - Downloading entity content
     * - Previewing in raw format
     * - Integration with external tools
     * @returns any Raw markdown content
     * @throws ApiError
     */
    public getContextEntityContentApiV1ContextEntitiesEntityIdContentGet({
        entityId,
    }: {
        entityId: string,
    }): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/context-entities/{entity_id}/content',
            path: {
                'entity_id': entityId,
            },
            errors: {
                404: `Context entity not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
