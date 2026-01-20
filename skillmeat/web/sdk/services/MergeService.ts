/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConflictResolveRequest } from '../models/ConflictResolveRequest';
import type { ConflictResolveResponse } from '../models/ConflictResolveResponse';
import type { MergeAnalyzeRequest } from '../models/MergeAnalyzeRequest';
import type { MergeExecuteRequest } from '../models/MergeExecuteRequest';
import type { MergeExecuteResponse } from '../models/MergeExecuteResponse';
import type { MergePreviewRequest } from '../models/MergePreviewRequest';
import type { MergePreviewResponse } from '../models/MergePreviewResponse';
import type { MergeSafetyResponse } from '../models/MergeSafetyResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MergeService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Analyze merge safety
   * Analyze whether merge is safe before attempting. Performs a dry-run three-way diff to identify potential conflicts without modifying any files.
   * @returns MergeSafetyResponse Successfully analyzed merge safety
   * @throws ApiError
   */
  public analyzeMergeApiV1MergeAnalyzePost({
    requestBody,
  }: {
    requestBody: MergeAnalyzeRequest;
  }): CancelablePromise<MergeSafetyResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/merge/analyze',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request parameters`,
        401: `Unauthorized`,
        404: `Snapshot or collection not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Preview merge changes
   * Get preview of merge changes without executing the merge. Shows what files will be added, removed, or changed.
   * @returns MergePreviewResponse Successfully generated merge preview
   * @throws ApiError
   */
  public previewMergeApiV1MergePreviewPost({
    requestBody,
  }: {
    requestBody: MergePreviewRequest;
  }): CancelablePromise<MergePreviewResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/merge/preview',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request parameters`,
        401: `Unauthorized`,
        404: `Snapshot or collection not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Execute merge operation
   * Execute merge with full conflict detection. Automatically creates safety snapshot before merge for rollback capability.
   * @returns MergeExecuteResponse Merge executed successfully or with conflicts
   * @throws ApiError
   */
  public executeMergeApiV1MergeExecutePost({
    requestBody,
  }: {
    requestBody: MergeExecuteRequest;
  }): CancelablePromise<MergeExecuteResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/merge/execute',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request parameters`,
        401: `Unauthorized`,
        404: `Snapshot or collection not found`,
        409: `Merge cannot be completed due to unresolved conflicts`,
        422: `Validation errors`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Resolve merge conflict
   * Resolve a single merge conflict by specifying which version to use or providing custom content.
   * @returns ConflictResolveResponse Conflict resolved successfully
   * @throws ApiError
   */
  public resolveConflictApiV1MergeResolvePost({
    requestBody,
  }: {
    requestBody: ConflictResolveRequest;
  }): CancelablePromise<ConflictResolveResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/merge/resolve',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid resolution parameters`,
        401: `Unauthorized`,
        404: `Conflict or file not found`,
        422: `Validation errors`,
        500: `Internal server error`,
      },
    });
  }
}
