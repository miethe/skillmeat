/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class DiscoveryService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
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
