/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DetectionPatternsResponse } from '../models/DetectionPatternsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ConfigService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Get artifact detection patterns
   * Returns the detection patterns used by the backend for identifying artifact types
   * from directory structures. This includes:
   *
   * - **container_aliases**: Maps each artifact type to all valid container directory names
   * - **leaf_containers**: Flattened list of all valid container names for quick lookups
   * - **canonical_containers**: Maps each artifact type to its preferred container name
   *
   * Frontend applications can use this data to replicate the same detection logic
   * for consistent artifact type inference across the stack.
   * @returns DetectionPatternsResponse Successful Response
   * @throws ApiError
   */
  public getDetectionPatternsApiV1ConfigDetectionPatternsGet(): CancelablePromise<DetectionPatternsResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/config/detection-patterns',
    });
  }
}
