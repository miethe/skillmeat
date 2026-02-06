/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class RootService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * API root
   * Returns basic API information and available endpoints
   * @returns any Successful Response
   * @throws ApiError
   */
  public rootGet(): CancelablePromise<Record<string, any>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/',
    });
  }
  /**
   * API version
   * Returns detailed version information
   * @returns any Successful Response
   * @throws ApiError
   */
  public versionInfoApiV1VersionGet(): CancelablePromise<Record<string, any>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/version',
    });
  }
}
