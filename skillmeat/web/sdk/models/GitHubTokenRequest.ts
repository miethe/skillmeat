/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to set GitHub Personal Access Token.
 *
 * The token must be a valid GitHub PAT starting with 'ghp_' (classic)
 * or 'github_pat_' (fine-grained).
 */
export type GitHubTokenRequest = {
    /**
     * GitHub Personal Access Token (must start with 'ghp_' or 'github_pat_')
     */
    token: string;
};

