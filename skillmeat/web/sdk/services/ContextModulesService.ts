/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AddMemoryToModuleRequest } from '../models/AddMemoryToModuleRequest';
import type { ContextModuleCreateRequest } from '../models/ContextModuleCreateRequest';
import type { ContextModuleListResponse } from '../models/ContextModuleListResponse';
import type { ContextModuleResponse } from '../models/ContextModuleResponse';
import type { ContextModuleUpdateRequest } from '../models/ContextModuleUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ContextModulesService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * List context modules for a project
   * Retrieve a paginated list of context modules scoped to a project.
   *
   * Results are ordered by module ID and support cursor-based pagination.
   * @returns ContextModuleListResponse Successfully retrieved context modules
   * @throws ApiError
   */
  public listContextModulesApiV1ContextModulesGet({
    projectId,
    limit = 50,
    cursor,
  }: {
    /**
     * Project ID to list modules for
     */
    projectId: string;
    /**
     * Number of items per page (max 100)
     */
    limit?: number;
    /**
     * Cursor from previous page for pagination
     */
    cursor?: string | null;
  }): CancelablePromise<ContextModuleListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/context-modules',
      query: {
        project_id: projectId,
        limit: limit,
        cursor: cursor,
      },
      errors: {
        400: `Invalid query parameters`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Create a new context module
   * Create a new context module for a project with optional selector criteria.
   *
   * Selectors define how memory items are filtered when the module is used
   * for context packing. Allowed selector keys: memory_types, min_confidence,
   * file_patterns, workflow_stages.
   * @returns ContextModuleResponse Context module created successfully
   * @throws ApiError
   */
  public createContextModuleApiV1ContextModulesPost({
    projectId,
    requestBody,
  }: {
    /**
     * Project ID to create module in
     */
    projectId: string;
    requestBody: ContextModuleCreateRequest;
  }): CancelablePromise<ContextModuleResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-modules',
      query: {
        project_id: projectId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Validation error`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get a context module by ID
   * Retrieve detailed information about a specific context module.
   *
   * Use include_items=true to also retrieve associated memory items.
   * @returns ContextModuleResponse Successfully retrieved context module
   * @throws ApiError
   */
  public getContextModuleApiV1ContextModulesModuleIdGet({
    moduleId,
    includeItems = false,
  }: {
    moduleId: string;
    /**
     * Include associated memory items in response
     */
    includeItems?: boolean;
  }): CancelablePromise<ContextModuleResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/context-modules/{module_id}',
      path: {
        module_id: moduleId,
      },
      query: {
        include_items: includeItems,
      },
      errors: {
        404: `Context module not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Update a context module
   * Update an existing context module. All fields are optional — only
   * provided fields will be updated. Updated selectors are validated.
   * @returns ContextModuleResponse Context module updated successfully
   * @throws ApiError
   */
  public updateContextModuleApiV1ContextModulesModuleIdPut({
    moduleId,
    requestBody,
  }: {
    moduleId: string;
    requestBody: ContextModuleUpdateRequest;
  }): CancelablePromise<ContextModuleResponse> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/api/v1/context-modules/{module_id}',
      path: {
        module_id: moduleId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Validation error`,
        404: `Context module not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Delete a context module
   * Delete a context module and its memory item associations.
   * This is a permanent operation.
   * @returns void
   * @throws ApiError
   */
  public deleteContextModuleApiV1ContextModulesModuleIdDelete({
    moduleId,
  }: {
    moduleId: string;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/context-modules/{module_id}',
      path: {
        module_id: moduleId,
      },
      errors: {
        404: `Context module not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Add a memory item to a context module
   * Associate a memory item with a context module. If the memory is already
   * linked, the operation is idempotent and returns the current state.
   * @returns ContextModuleResponse Memory item added (or already linked)
   * @throws ApiError
   */
  public addMemoryToModuleApiV1ContextModulesModuleIdMemoriesPost({
    moduleId,
    requestBody,
  }: {
    moduleId: string;
    requestBody: AddMemoryToModuleRequest;
  }): CancelablePromise<ContextModuleResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-modules/{module_id}/memories',
      path: {
        module_id: moduleId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Validation error (module or memory not found)`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * List memory items in a context module
   * Retrieve all memory items associated with a context module, ordered
   * by their position within the module.
   * @returns any Successfully retrieved module's memory items
   * @throws ApiError
   */
  public listModuleMemoriesApiV1ContextModulesModuleIdMemoriesGet({
    moduleId,
    limit = 100,
  }: {
    moduleId: string;
    /**
     * Maximum number of items to return
     */
    limit?: number;
  }): CancelablePromise<Array<Record<string, any>>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/context-modules/{module_id}/memories',
      path: {
        module_id: moduleId,
      },
      query: {
        limit: limit,
      },
      errors: {
        400: `Invalid request`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Remove a memory item from a context module
   * Remove the association between a memory item and a context module.
   * The memory item itself is not deleted.
   * @returns void
   * @throws ApiError
   */
  public removeMemoryFromModuleApiV1ContextModulesModuleIdMemoriesMemoryIdDelete({
    moduleId,
    memoryId,
  }: {
    moduleId: string;
    memoryId: string;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/context-modules/{module_id}/memories/{memory_id}',
      path: {
        module_id: moduleId,
        memory_id: memoryId,
      },
      errors: {
        404: `Association not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
}
