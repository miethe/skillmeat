/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for GitHub token validation.
 *
 * Returns validation results including rate limit information
 * and token scopes without storing the token.
 */
export type GitHubTokenValidationResponse = {
    /**
     * Whether the token is valid and can authenticate with GitHub
     */
    valid: boolean;
    /**
     * GitHub username associated with the token
     */
    username?: (string | null);
    /**
     * OAuth scopes granted to the token
     */
    scopes?: (Array<string> | null);
    /**
     * Maximum requests per hour with this token
     */
    rate_limit?: (number | null);
    /**
     * Remaining requests in current rate limit window
     */
    rate_remaining?: (number | null);
};

