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
    /**
     * Enable parsing markdown frontmatter for artifact type hints
     */
    enable_frontmatter_detection?: boolean;
    /**
     * Fetch repository description from GitHub on import
     */
    import_repo_description?: boolean;
    /**
     * Fetch README content from GitHub on import
     */
    import_repo_readme?: boolean;
    /**
     * Tags to apply to source (max 20, each 1-50 chars)
     */
    tags?: (Array<string> | null);
    /**
     * Treat the entire repository (or root_hint directory) as a single artifact, bypassing automatic detection
     */
    single_artifact_mode?: boolean;
    /**
     * Artifact type when single_artifact_mode is enabled (required when mode is True)
     */
    single_artifact_type?: ('skill' | 'command' | 'agent' | 'mcp_server' | 'hook' | null);
};

