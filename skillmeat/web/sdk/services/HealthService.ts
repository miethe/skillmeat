/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DetailedHealthStatus } from '../models/DetailedHealthStatus';
import type { HealthStatus } from '../models/HealthStatus';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class HealthService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Basic health check
   * Basic health check endpoint that returns service status.
   * Used for simple availability checks by load balancers.
   *
   * Returns HTTP 200 if service is running.
   * @returns HealthStatus Successful Response
   * @throws ApiError
   */
  public healthCheckHealthGet(): CancelablePromise<HealthStatus> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/health',
    });
  }
  /**
   * Detailed health check
   * Detailed health check endpoint that includes component status and system information.
   * Used for comprehensive monitoring and diagnostics.
   *
   * Checks the health of:
   * - Collection manager
   * - Configuration manager
   * - File system access
   *
   * Returns HTTP 200 if all components are healthy.
   * Returns HTTP 503 if any critical component is unhealthy.
   * @returns DetailedHealthStatus Successful Response
   * @throws ApiError
   */
  public detailedHealthCheckHealthDetailedGet(): CancelablePromise<DetailedHealthStatus> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/health/detailed',
    });
  }
  /**
   * Readiness check
   * Readiness check endpoint for Kubernetes and container orchestrators.
   * Indicates whether the service is ready to accept traffic.
   *
   * Returns HTTP 200 if service is ready.
   * Returns HTTP 503 if service is not ready (still initializing).
   * @returns string Successful Response
   * @throws ApiError
   */
  public readinessCheckHealthReadyGet(): CancelablePromise<Record<string, string>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/health/ready',
    });
  }
  /**
   * Liveness check
   * Liveness check endpoint for Kubernetes and container orchestrators.
   * Indicates whether the service is alive (not deadlocked/crashed).
   *
   * Returns HTTP 200 if service is alive.
   * Should never return 503 unless the service is truly unresponsive.
   * @returns string Successful Response
   * @throws ApiError
   */
  public livenessCheckHealthLiveGet(): CancelablePromise<Record<string, string>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/health/live',
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
