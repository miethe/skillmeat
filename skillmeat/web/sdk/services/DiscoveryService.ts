/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfirmDuplicatesRequest } from '../models/ConfirmDuplicatesRequest';
import type { ConfirmDuplicatesResponse } from '../models/ConfirmDuplicatesResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class DiscoveryService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Process duplicate review decisions
   * Process user decisions from the duplicate review modal.
   *
   * Handles three types of decisions:
   * 1. **matches**: Link discovered duplicates to existing collection artifacts
   * 2. **new_artifacts**: Import selected paths as new artifacts
   * 3. **skipped**: Acknowledge paths the user chose to skip (logged for audit)
   *
   * All operations are atomic - if any operation fails, the response will
   * indicate partial success with error details.
   *
   * This endpoint is idempotent for link operations - calling multiple times
   * with the same matches will not create duplicate links.
   * @returns ConfirmDuplicatesResponse Duplicate decisions processed successfully
   * @throws ApiError
   */
  public confirmDuplicatesApiV1ArtifactsConfirmDuplicatesPost({
    requestBody,
    collection,
  }: {
    requestBody: ConfirmDuplicatesRequest;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ConfirmDuplicatesResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/confirm-duplicates',
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get discovery feature metrics
   * Get metrics and statistics for discovery features including:
   * - Total discovery scans performed
   * - Total artifacts discovered
   * - Total bulk imports
   * - GitHub metadata fetch statistics
   * - Cache hit/miss rates
   * - Error counts
   * - Last scan information
   *
   * This endpoint provides simple metrics without requiring Prometheus infrastructure.
   * For production monitoring, use the /metrics endpoint exposed by the Prometheus client.
   * @returns any Discovery metrics and statistics
   * @throws ApiError
   */
  public getDiscoveryMetricsApiV1ArtifactsMetricsDiscoveryGet(): CancelablePromise<any> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/metrics/discovery',
    });
  }
  /**
   * Discovery feature health check
   * Check the health status of discovery features including:
   * - Discovery service availability
   * - Auto-population feature status
   * - Cache configuration
   * - Current metrics
   *
   * Returns 200 OK if all discovery features are operational.
   * @returns any Discovery health status
   * @throws ApiError
   */
  public discoveryHealthCheckApiV1ArtifactsHealthDiscoveryGet(): CancelablePromise<any> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/health/discovery',
    });
  }
}
