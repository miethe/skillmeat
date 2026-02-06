/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BulkActionResponse } from '../models/BulkActionResponse';
import type { BulkDeprecateRequest } from '../models/BulkDeprecateRequest';
import type { BulkPromoteRequest } from '../models/BulkPromoteRequest';
import type { DeprecateRequest } from '../models/DeprecateRequest';
import type { MemoryItemCreateRequest } from '../models/MemoryItemCreateRequest';
import type { MemoryItemListResponse } from '../models/MemoryItemListResponse';
import type { MemoryItemResponse } from '../models/MemoryItemResponse';
import type { MemoryItemUpdateRequest } from '../models/MemoryItemUpdateRequest';
import type { MemoryStatus } from '../models/MemoryStatus';
import type { MemoryType } from '../models/MemoryType';
import type { MergeRequest } from '../models/MergeRequest';
import type { MergeResponse } from '../models/MergeResponse';
import type { PromoteRequest } from '../models/PromoteRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MemoryItemsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Count memory items
   * Get a count of memory items for a project with optional filters.
   * @returns any Count retrieved successfully
   * @throws ApiError
   */
  public countMemoryItemsApiV1MemoryItemsCountGet({
    projectId,
    status,
    type,
  }: {
    /**
     * Project ID to scope the count
     */
    projectId: string;
    /**
     * Filter by status
     */
    status?: MemoryStatus | null;
    /**
     * Filter by memory type
     */
    type?: MemoryType | null;
  }): CancelablePromise<Record<string, any>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/memory-items/count',
      query: {
        project_id: projectId,
        status: status,
        type: type,
      },
      errors: {
        400: `Invalid query parameters`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Bulk promote memory items
   * Promote multiple memory items to their next lifecycle stage.
   * @returns BulkActionResponse Bulk promote completed (may contain partial failures)
   * @throws ApiError
   */
  public bulkPromoteMemoryItemsApiV1MemoryItemsBulkPromotePost({
    requestBody,
  }: {
    requestBody: BulkPromoteRequest;
  }): CancelablePromise<BulkActionResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/memory-items/bulk-promote',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Bulk deprecate memory items
   * Deprecate multiple memory items in a single request.
   * @returns BulkActionResponse Bulk deprecate completed (may contain partial failures)
   * @throws ApiError
   */
  public bulkDeprecateMemoryItemsApiV1MemoryItemsBulkDeprecatePost({
    requestBody,
  }: {
    requestBody: BulkDeprecateRequest;
  }): CancelablePromise<BulkActionResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/memory-items/bulk-deprecate',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Merge two memory items
   * Merge a source memory item into a target item using a specified strategy.
   *
   * Strategies:
   * - keep_target: Keep the target's content, deprecate the source.
   * - keep_source: Replace the target's content with the source's, deprecate the source.
   * - combine: Use the provided merged_content for the target, deprecate the source.
   *
   * The source item is always deprecated after a successful merge.
   * @returns MergeResponse Merge completed successfully
   * @throws ApiError
   */
  public mergeMemoryItemsApiV1MemoryItemsMergePost({
    requestBody,
  }: {
    requestBody: MergeRequest;
  }): CancelablePromise<MergeResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/memory-items/merge',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid merge request`,
        404: `Source or target item not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * List memory items
   * Retrieve a paginated list of memory items for a project.
   *
   * Supports filtering by status, type, and minimum confidence score.
   * Uses cursor-based pagination for efficient traversal of large result sets.
   * @returns MemoryItemListResponse Successfully retrieved memory items
   * @throws ApiError
   */
  public listMemoryItemsApiV1MemoryItemsGet({
    projectId,
    status,
    type,
    minConfidence,
    limit = 50,
    cursor,
    sortBy = 'created_at',
    sortOrder = 'desc',
  }: {
    /**
     * Project ID to scope the query
     */
    projectId: string;
    /**
     * Filter by status
     */
    status?: MemoryStatus | null;
    /**
     * Filter by memory type
     */
    type?: MemoryType | null;
    /**
     * Minimum confidence threshold
     */
    minConfidence?: number | null;
    /**
     * Number of items per page (max 100)
     */
    limit?: number;
    /**
     * Cursor from previous page for pagination
     */
    cursor?: string | null;
    /**
     * Field to sort by
     */
    sortBy?: string;
    /**
     * Sort direction (asc or desc)
     */
    sortOrder?: string;
  }): CancelablePromise<MemoryItemListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/memory-items',
      query: {
        project_id: projectId,
        status: status,
        type: type,
        min_confidence: minConfidence,
        limit: limit,
        cursor: cursor,
        sort_by: sortBy,
        sort_order: sortOrder,
      },
      errors: {
        400: `Invalid query parameters`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Create a new memory item
   * Create a new memory item for a project.
   *
   * Includes automatic duplicate detection via content hashing.
   * If a duplicate is detected, returns 409 Conflict with the existing item.
   * @returns MemoryItemResponse Memory item created successfully
   * @throws ApiError
   */
  public createMemoryItemApiV1MemoryItemsPost({
    projectId,
    requestBody,
  }: {
    /**
     * Project ID for the new memory item
     */
    projectId: string;
    requestBody: MemoryItemCreateRequest;
  }): CancelablePromise<MemoryItemResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/memory-items',
      query: {
        project_id: projectId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Validation error`,
        409: `Duplicate memory item detected`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get a memory item by ID
   * Retrieve a single memory item by its ID. Increments access count.
   * @returns MemoryItemResponse Successfully retrieved memory item
   * @throws ApiError
   */
  public getMemoryItemApiV1MemoryItemsItemIdGet({
    itemId,
  }: {
    itemId: string;
  }): CancelablePromise<MemoryItemResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/memory-items/{item_id}',
      path: {
        item_id: itemId,
      },
      errors: {
        404: `Memory item not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Update a memory item
   * Update an existing memory item. Only provided fields are changed.
   *
   * Updatable fields: type, content, confidence, status, provenance, anchors, ttl_policy.
   * @returns MemoryItemResponse Memory item updated successfully
   * @throws ApiError
   */
  public updateMemoryItemApiV1MemoryItemsItemIdPut({
    itemId,
    requestBody,
  }: {
    itemId: string;
    requestBody: MemoryItemUpdateRequest;
  }): CancelablePromise<MemoryItemResponse> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/api/v1/memory-items/{item_id}',
      path: {
        item_id: itemId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Validation error or disallowed field`,
        404: `Memory item not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Delete a memory item
   * Permanently delete a memory item by ID.
   * @returns void
   * @throws ApiError
   */
  public deleteMemoryItemApiV1MemoryItemsItemIdDelete({
    itemId,
  }: {
    itemId: string;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/memory-items/{item_id}',
      path: {
        item_id: itemId,
      },
      errors: {
        404: `Memory item not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Promote a memory item
   * Promote a memory item to the next lifecycle stage.
   *
   * State machine: candidate -> active -> stable.
   * Items that are already stable or deprecated cannot be promoted.
   * @returns MemoryItemResponse Memory item promoted successfully
   * @throws ApiError
   */
  public promoteMemoryItemApiV1MemoryItemsItemIdPromotePost({
    itemId,
    requestBody,
  }: {
    itemId: string;
    requestBody: PromoteRequest;
  }): CancelablePromise<MemoryItemResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/memory-items/{item_id}/promote',
      path: {
        item_id: itemId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid promotion (wrong status)`,
        404: `Memory item not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Deprecate a memory item
   * Deprecate a memory item regardless of its current lifecycle stage.
   *
   * Any non-deprecated status can transition to deprecated. The deprecated_at
   * timestamp is set automatically by the repository layer.
   * @returns MemoryItemResponse Memory item deprecated successfully
   * @throws ApiError
   */
  public deprecateMemoryItemApiV1MemoryItemsItemIdDeprecatePost({
    itemId,
    requestBody,
  }: {
    itemId: string;
    requestBody: DeprecateRequest;
  }): CancelablePromise<MemoryItemResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/memory-items/{item_id}/deprecate',
      path: {
        item_id: itemId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Item is already deprecated`,
        404: `Memory item not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
}
