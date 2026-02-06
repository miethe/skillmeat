/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_import_bundle_api_v1_bundles_import_post } from '../models/Body_import_bundle_api_v1_bundles_import_post';
import type { Body_preview_bundle_api_v1_bundles_preview_post } from '../models/Body_preview_bundle_api_v1_bundles_preview_post';
import type { Body_validate_bundle_api_v1_bundles_validate_post } from '../models/Body_validate_bundle_api_v1_bundles_validate_post';
import type { BundleAnalyticsResponse } from '../models/BundleAnalyticsResponse';
import type { BundleDeleteResponse } from '../models/BundleDeleteResponse';
import type { BundleDetailResponse } from '../models/BundleDetailResponse';
import type { BundleExportRequest } from '../models/BundleExportRequest';
import type { BundleExportResponse } from '../models/BundleExportResponse';
import type { BundleImportResponse } from '../models/BundleImportResponse';
import type { BundleListResponse } from '../models/BundleListResponse';
import type { BundlePreviewResponse } from '../models/BundlePreviewResponse';
import type { BundleValidationResponse } from '../models/BundleValidationResponse';
import type { ShareLinkDeleteResponse } from '../models/ShareLinkDeleteResponse';
import type { ShareLinkResponse } from '../models/ShareLinkResponse';
import type { ShareLinkUpdateRequest } from '../models/ShareLinkUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class BundlesService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Import artifact bundle
   * Import a bundle ZIP file into collection with conflict resolution
   * @returns BundleImportResponse Bundle imported successfully
   * @throws ApiError
   */
  public importBundleApiV1BundlesImportPost({
    formData,
  }: {
    formData: Body_import_bundle_api_v1_bundles_import_post;
  }): CancelablePromise<BundleImportResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/bundles/import',
      formData: formData,
      mediaType: 'multipart/form-data',
      errors: {
        400: `Invalid bundle or parameters`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Import failed`,
      },
    });
  }
  /**
   * Validate bundle without importing
   * Check bundle integrity and validity without importing
   * @returns BundleValidationResponse Validation completed (check is_valid field)
   * @throws ApiError
   */
  public validateBundleApiV1BundlesValidatePost({
    formData,
  }: {
    formData: Body_validate_bundle_api_v1_bundles_validate_post;
  }): CancelablePromise<BundleValidationResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/bundles/validate',
      formData: formData,
      mediaType: 'multipart/form-data',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Validation failed`,
      },
    });
  }
  /**
   * Preview bundle before importing
   * Analyze bundle contents and detect conflicts without importing
   * @returns BundlePreviewResponse Preview completed successfully
   * @throws ApiError
   */
  public previewBundleApiV1BundlesPreviewPost({
    formData,
  }: {
    formData: Body_preview_bundle_api_v1_bundles_preview_post;
  }): CancelablePromise<BundlePreviewResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/bundles/preview',
      formData: formData,
      mediaType: 'multipart/form-data',
      errors: {
        400: `Invalid bundle`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Preview failed`,
      },
    });
  }
  /**
   * Export artifacts as a bundle
   * Create a bundle archive from selected artifacts with optional sharing
   * @returns BundleExportResponse Bundle exported successfully
   * @throws ApiError
   */
  public exportBundleApiV1BundlesExportPost({
    requestBody,
  }: {
    requestBody: BundleExportRequest;
  }): CancelablePromise<BundleExportResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/bundles/export',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request or artifact not found`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Export failed`,
      },
    });
  }
  /**
   * List all bundles
   * Get list of all bundles with optional filtering by source (created, imported)
   * @returns BundleListResponse List of bundles retrieved successfully
   * @throws ApiError
   */
  public listBundlesApiV1BundlesGet({
    sourceFilter,
  }: {
    sourceFilter?: string | null;
  }): CancelablePromise<BundleListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/bundles',
      query: {
        source_filter: sourceFilter,
      },
      errors: {
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Failed to retrieve bundles`,
      },
    });
  }
  /**
   * Get bundle details
   * Retrieve detailed information about a specific bundle
   * @returns BundleDetailResponse Bundle details retrieved successfully
   * @throws ApiError
   */
  public getBundleApiV1BundlesBundleIdGet({
    bundleId,
  }: {
    bundleId: string;
  }): CancelablePromise<BundleDetailResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/bundles/{bundle_id}',
      path: {
        bundle_id: bundleId,
      },
      errors: {
        401: `Unauthorized`,
        404: `Bundle not found`,
        422: `Validation Error`,
        500: `Failed to retrieve bundle`,
      },
    });
  }
  /**
   * Delete a bundle
   * Delete a bundle from the collection
   * @returns BundleDeleteResponse Bundle deleted successfully
   * @throws ApiError
   */
  public deleteBundleApiV1BundlesBundleIdDelete({
    bundleId,
  }: {
    bundleId: string;
  }): CancelablePromise<BundleDeleteResponse> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/bundles/{bundle_id}',
      path: {
        bundle_id: bundleId,
      },
      errors: {
        401: `Unauthorized`,
        404: `Bundle not found`,
        422: `Validation Error`,
        500: `Failed to delete bundle`,
      },
    });
  }
  /**
   * Get bundle analytics
   * Retrieve analytics data for a bundle including downloads and popular artifacts
   * @returns BundleAnalyticsResponse Bundle analytics retrieved successfully
   * @throws ApiError
   */
  public getBundleAnalyticsApiV1BundlesBundleIdAnalyticsGet({
    bundleId,
  }: {
    bundleId: string;
  }): CancelablePromise<BundleAnalyticsResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/bundles/{bundle_id}/analytics',
      path: {
        bundle_id: bundleId,
      },
      errors: {
        401: `Unauthorized`,
        404: `Bundle not found`,
        422: `Validation Error`,
        500: `Failed to retrieve analytics`,
      },
    });
  }
  /**
   * Create or update bundle share link
   * Generate or update a shareable link for a bundle with permissions and expiration
   * @returns ShareLinkResponse Share link created/updated successfully
   * @throws ApiError
   */
  public updateBundleShareLinkApiV1BundlesBundleIdSharePut({
    bundleId,
    requestBody,
  }: {
    bundleId: string;
    requestBody: ShareLinkUpdateRequest;
  }): CancelablePromise<ShareLinkResponse> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/api/v1/bundles/{bundle_id}/share',
      path: {
        bundle_id: bundleId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid bundle_id or request`,
        401: `Unauthorized`,
        404: `Bundle not found`,
        422: `Validation Error`,
        500: `Failed to create share link`,
      },
    });
  }
  /**
   * Revoke bundle share link
   * Delete and revoke the shareable link for a bundle
   * @returns ShareLinkDeleteResponse Share link revoked successfully
   * @throws ApiError
   */
  public deleteBundleShareLinkApiV1BundlesBundleIdShareDelete({
    bundleId,
  }: {
    bundleId: string;
  }): CancelablePromise<ShareLinkDeleteResponse> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/bundles/{bundle_id}/share',
      path: {
        bundle_id: bundleId,
      },
      errors: {
        400: `Invalid bundle_id`,
        401: `Unauthorized`,
        404: `Bundle or share link not found`,
        422: `Validation Error`,
        500: `Failed to revoke share link`,
      },
    });
  }
}
