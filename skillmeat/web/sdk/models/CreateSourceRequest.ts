/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to add a GitHub repository source.
 *
 * Specifies repository URL, branch/tag/SHA, and scanning options.
 */
export type CreateSourceRequest = {
    /**
     * Full GitHub repository URL
     */
    repo_url: string;
    /**
     * Branch, tag, or SHA to scan
     */
    ref?: string;
    /**
     * Subdirectory path within repository to start scanning
     */
    root_hint?: (string | null);
    /**
     * GitHub Personal Access Token for private repos (not stored, used for initial scan)
     */
    access_token?: (string | null);
    /**
     * Manual override: artifact_type -> list of paths
     */
    manual_map?: (Record<string, Array<string>> | null);
    /**
     * Trust level for artifacts from this source
     */
    trust_level?: 'untrusted' | 'basic' | 'verified' | 'official';
    /**
     * User-provided description for this source (max 500 chars)
     */
    description?: (string | null);
    /**
     * Internal notes/documentation for this source (max 2000 chars)
     */
    notes?: (string | null);
};

