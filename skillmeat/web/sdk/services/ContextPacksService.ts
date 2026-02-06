/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextPackGenerateRequest } from '../models/ContextPackGenerateRequest';
import type { ContextPackGenerateResponse } from '../models/ContextPackGenerateResponse';
import type { ContextPackPreviewRequest } from '../models/ContextPackPreviewRequest';
import type { ContextPackPreviewResponse } from '../models/ContextPackPreviewResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ContextPacksService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Preview a context pack (read-only)
   * Preview what a context pack would contain without generating markdown.
   *
   * Performs read-only selection of memory items based on module selectors,
   * additional filters, and token budget constraints. Items are selected by
   * confidence (descending) then recency (descending).
   *
   * Use this to estimate token usage and see which items would be included
   * before committing to a full generation.
   * @returns ContextPackPreviewResponse Successfully generated pack preview
   * @throws ApiError
   */
  public previewContextPackApiV1ContextPacksPreviewPost({
    projectId,
    requestBody,
  }: {
    /**
     * Project ID to build pack for
     */
    projectId: string;
    requestBody: ContextPackPreviewRequest;
  }): CancelablePromise<ContextPackPreviewResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-packs/preview',
      query: {
        project_id: projectId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request parameters`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Generate a context pack with markdown
   * Generate a full context pack with structured markdown output.
   *
   * Performs the same selection as preview, then generates markdown grouped
   * by memory type with confidence annotations. The generated markdown is
   * suitable for direct injection into agent prompts or CLAUDE.md files.
   *
   * Confidence tiers in output:
   * - High (>= 0.85): no label
   * - Medium (0.60 - 0.84): [medium confidence]
   * - Low (< 0.60): [low confidence]
   * @returns ContextPackGenerateResponse Successfully generated context pack
   * @throws ApiError
   */
  public generateContextPackApiV1ContextPacksGeneratePost({
    projectId,
    requestBody,
  }: {
    /**
     * Project ID to build pack for
     */
    projectId: string;
    requestBody: ContextPackGenerateRequest;
  }): CancelablePromise<ContextPackGenerateResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/context-packs/generate',
      query: {
        project_id: projectId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request parameters`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
}
