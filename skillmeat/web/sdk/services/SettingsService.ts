/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GitHubTokenRequest } from '../models/GitHubTokenRequest';
import type { GitHubTokenStatusResponse } from '../models/GitHubTokenStatusResponse';
import type { GitHubTokenValidationResponse } from '../models/GitHubTokenValidationResponse';
import type { IndexingModeResponse } from '../models/IndexingModeResponse';
import type { MessageResponse } from '../models/MessageResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class SettingsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Set GitHub Personal Access Token
   * Configure a GitHub Personal Access Token for improved API rate limits.
   *
   * Without a token: 60 requests/hour
   * With a token: 5,000 requests/hour
   *
   * The token must:
   * - Start with 'ghp_' (classic PAT) or 'github_pat_' (fine-grained PAT)
   * - Be valid and able to authenticate with GitHub API
   *
   * The token is validated against GitHub before being stored.
   * @returns MessageResponse Successful Response
   * @throws ApiError
   */
  public setGithubTokenApiV1SettingsGithubTokenPost({
    requestBody,
  }: {
    requestBody: GitHubTokenRequest;
  }): CancelablePromise<MessageResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/settings/github-token',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Clear GitHub token
   * Remove the configured GitHub Personal Access Token.
   *
   * After clearing, API requests will use unauthenticated rate limits
   * (60 requests/hour instead of 5,000).
   * @returns void
   * @throws ApiError
   */
  public deleteGithubTokenApiV1SettingsGithubTokenDelete(): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/settings/github-token',
    });
  }
  /**
   * Check GitHub token status
   * Check if a GitHub Personal Access Token is configured.
   *
   * Returns:
   * - Whether a token is set
   * - Masked token (first 7 characters) if set
   * - Associated GitHub username if set
   * - Rate limit information (remaining/limit)
   * @returns GitHubTokenStatusResponse Successful Response
   * @throws ApiError
   */
  public getGithubTokenStatusApiV1SettingsGithubTokenStatusGet(): CancelablePromise<GitHubTokenStatusResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/settings/github-token/status',
    });
  }
  /**
   * Validate GitHub token without storing
   * Validate a GitHub Personal Access Token without storing it.
   *
   * Useful for testing a token before committing to save it.
   * Returns validation status, associated username, granted scopes,
   * and current rate limit information.
   * @returns GitHubTokenValidationResponse Successful Response
   * @throws ApiError
   */
  public validateGithubTokenApiV1SettingsGithubTokenValidatePost({
    requestBody,
  }: {
    requestBody: GitHubTokenRequest;
  }): CancelablePromise<GitHubTokenValidationResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/settings/github-token/validate',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get global artifact search indexing mode
   * Get the global artifact search indexing mode setting.
   *
   * Returns:
   * - "off": Indexing is disabled globally
   * - "on": Indexing is enabled globally
   * - "opt_in": Indexing is opt-in per artifact (default)
   * @returns IndexingModeResponse Successful Response
   * @throws ApiError
   */
  public getIndexingModeApiV1SettingsIndexingModeGet(): CancelablePromise<IndexingModeResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/settings/indexing-mode',
    });
  }
}
