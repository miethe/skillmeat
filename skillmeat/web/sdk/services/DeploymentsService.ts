/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeploymentListResponse } from '../models/DeploymentListResponse';
import type { DeployRequest } from '../models/DeployRequest';
import type { skillmeat__api__schemas__deployments__DeploymentResponse } from '../models/skillmeat__api__schemas__deployments__DeploymentResponse';
import type { UndeployRequest } from '../models/UndeployRequest';
import type { UndeployResponse } from '../models/UndeployResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class DeploymentsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Deploy artifact to project
   * Deploy an artifact from collection to a project's .claude directory
   * @returns skillmeat__api__schemas__deployments__DeploymentResponse Artifact deployed successfully
   * @throws ApiError
   */
  public deployArtifactApiV1DeployPost({
    requestBody,
  }: {
    requestBody: DeployRequest;
  }): CancelablePromise<skillmeat__api__schemas__deployments__DeploymentResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/deploy',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request or artifact not found`,
        401: `Unauthorized`,
        404: `Artifact or collection not found`,
        422: `Validation Error`,
        500: `Deployment failed`,
      },
    });
  }
  /**
   * List deployments
   * List all deployed artifacts in a project
   * @returns DeploymentListResponse Deployments retrieved successfully
   * @throws ApiError
   */
  public listDeploymentsApiV1DeployGet({
    projectPath,
  }: {
    /**
     * Path to project directory (uses CWD if not specified)
     */
    projectPath?: string | null;
  }): CancelablePromise<DeploymentListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/deploy',
      query: {
        project_path: projectPath,
      },
      errors: {
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Failed to retrieve deployments`,
      },
    });
  }
  /**
   * Remove deployed artifact
   * Remove an artifact from a project's .claude directory
   * @returns UndeployResponse Artifact removed successfully
   * @throws ApiError
   */
  public undeployArtifactApiV1DeployUndeployPost({
    requestBody,
  }: {
    requestBody: UndeployRequest;
  }): CancelablePromise<UndeployResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/deploy/undeploy',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Artifact not deployed`,
        422: `Validation Error`,
        500: `Removal failed`,
      },
    });
  }
}
