/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SyncPullRequest } from '../models/SyncPullRequest';
import type { SyncPushRequest } from '../models/SyncPushRequest';
import type { SyncResolveRequest } from '../models/SyncResolveRequest';
import type { SyncResultResponse } from '../models/SyncResultResponse';
import type { SyncStatusResponse } from '../models/SyncStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ContextSyncService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Pull changes from project
   * Pull changes from project deployed files to collection entities
   * @returns SyncResultResponse Successfully pulled changes
   * @throws ApiError
   */
  public pullChangesApiV1ContextSyncPullPost({
    requestBody,
  }: {
    requestBody: SyncPullRequest;
  }): CancelablePromise<Array<SyncResultResponse>> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-sync/pull',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        404: `Project path not found`,
        422: `Validation Error`,
        500: `Sync operation failed`,
      },
    });
  }
  /**
   * Push changes to project
   * Push collection entity changes to project deployed files
   * @returns SyncResultResponse Successfully pushed changes
   * @throws ApiError
   */
  public pushChangesApiV1ContextSyncPushPost({
    requestBody,
  }: {
    requestBody: SyncPushRequest;
  }): CancelablePromise<Array<SyncResultResponse>> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-sync/push',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        404: `Project path not found`,
        409: `Conflict detected (file modified locally)`,
        422: `Validation Error`,
        500: `Sync operation failed`,
      },
    });
  }
  /**
   * Get sync status
   * Get sync status for a project (modified entities and conflicts)
   * @returns SyncStatusResponse Sync status retrieved
   * @throws ApiError
   */
  public getSyncStatusApiV1ContextSyncStatusGet({
    projectPath,
  }: {
    /**
     * Absolute path to project directory
     */
    projectPath: string;
  }): CancelablePromise<SyncStatusResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/context-sync/status',
      query: {
        project_path: projectPath,
      },
      errors: {
        404: `Project path not found`,
        422: `Validation Error`,
        500: `Status check failed`,
      },
    });
  }
  /**
   * Resolve sync conflict
   * Resolve a sync conflict using user-selected strategy
   * @returns SyncResultResponse Conflict resolved
   * @throws ApiError
   */
  public resolveConflictApiV1ContextSyncResolvePost({
    requestBody,
  }: {
    requestBody: SyncResolveRequest;
  }): CancelablePromise<SyncResultResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-sync/resolve',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request (e.g., merge without content)`,
        404: `Project path or entity not found`,
        422: `Validation Error`,
        500: `Resolution failed`,
      },
    });
  }
}
