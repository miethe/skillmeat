/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TagCreateRequest } from '../models/TagCreateRequest';
import type { TagListResponse } from '../models/TagListResponse';
import type { TagResponse } from '../models/TagResponse';
import type { TagUpdateRequest } from '../models/TagUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class TagsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Create new tag
     * Create a new tag for organizing artifacts.
     *
     * Tag names and slugs must be unique across the system. The slug should be
     * a URL-friendly kebab-case identifier. Colors are optional hex codes for
     * visual customization.
     * @returns TagResponse Tag created successfully
     * @throws ApiError
     */
    public createTagApiV1TagsPost({
        requestBody,
    }: {
        requestBody: TagCreateRequest,
    }): CancelablePromise<TagResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/tags',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request data`,
                409: `Tag name or slug already exists`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * List all tags
     * Retrieve a paginated list of all tags with artifact counts.
     *
     * Results are ordered by name (ascending) and support cursor-based pagination.
     * @returns TagListResponse Tags retrieved successfully
     * @throws ApiError
     */
    public listTagsApiV1TagsGet({
        limit = 50,
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
    }): CancelablePromise<TagListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/tags',
            query: {
                'limit': limit,
                'after': after,
            },
            errors: {
                400: `Invalid pagination cursor`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get tag by ID
     * Retrieve detailed information about a specific tag by its ID.
     * @returns TagResponse Tag retrieved successfully
     * @throws ApiError
     */
    public getTagApiV1TagsTagIdGet({
        tagId,
    }: {
        tagId: string,
    }): CancelablePromise<TagResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/tags/{tag_id}',
            path: {
                'tag_id': tagId,
            },
            errors: {
                404: `Tag not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Update tag
     * Update tag metadata. All fields are optional for partial updates.
     *
     * If slug is updated, it must remain unique across the system.
     * @returns TagResponse Tag updated successfully
     * @throws ApiError
     */
    public updateTagApiV1TagsTagIdPut({
        tagId,
        requestBody,
    }: {
        tagId: string,
        requestBody: TagUpdateRequest,
    }): CancelablePromise<TagResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/tags/{tag_id}',
            path: {
                'tag_id': tagId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request data`,
                404: `Tag not found`,
                409: `Updated slug already exists`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete tag
     * Delete a tag by ID.
     *
     * This removes the tag and all associations with artifacts. Artifacts
     * themselves are not affected.
     * @returns void
     * @throws ApiError
     */
    public deleteTagApiV1TagsTagIdDelete({
        tagId,
    }: {
        tagId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/tags/{tag_id}',
            path: {
                'tag_id': tagId,
            },
            errors: {
                404: `Tag not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get tag by slug
     * Retrieve detailed information about a specific tag by its URL slug.
     * @returns TagResponse Tag retrieved successfully
     * @throws ApiError
     */
    public getTagBySlugApiV1TagsSlugSlugGet({
        slug,
    }: {
        slug: string,
    }): CancelablePromise<TagResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/tags/slug/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                404: `Tag not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Search tags by name
     * Search for tags by name (case-insensitive substring match).
     *
     * Results are limited to 50 tags and ordered by name.
     * @returns TagResponse Search completed successfully
     * @throws ApiError
     */
    public searchTagsApiV1TagsSearchGet({
        q,
        limit = 50,
    }: {
        /**
         * Search query (case-insensitive)
         */
        q: string,
        /**
         * Maximum number of results
         */
        limit?: number,
    }): CancelablePromise<Array<TagResponse>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/tags/search',
            query: {
                'q': q,
                'limit': limit,
            },
            errors: {
                400: `Invalid search query`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
