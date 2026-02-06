/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for GitHub token status check.
 *
 * Returns whether a token is configured and, if so, a masked version
 * along with the associated GitHub username and rate limit information.
 */
export type GitHubTokenStatusResponse = {
  /**
   * Whether a GitHub token is currently configured
   */
  is_set: boolean;
  /**
   * Masked token showing first 7 characters (e.g., 'ghp_xxx...')
   */
  masked_token?: string | null;
  /**
   * GitHub username associated with the token
   */
  username?: string | null;
  /**
   * Maximum requests per hour (5000 with token, 60 without)
   */
  rate_limit?: number | null;
  /**
   * Remaining requests in current rate limit window
   */
  rate_remaining?: number | null;
};
