/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single artifact to import in bulk operation.
 */
export type BulkImportArtifact = {
    /**
     * GitHub source or local path
     */
    source: string;
    /**
     * Filesystem path for local artifacts (required when source starts with 'local/')
     */
    path?: (string | null);
    /**
     * Type: skill, command, agent, hook, mcp
     */
    artifact_type: string;
    /**
     * Name (auto-derived from source if None)
     */
    name?: (string | null);
    /**
     * Description override
     */
    description?: (string | null);
    /**
     * Author override
     */
    author?: (string | null);
    /**
     * Tags to apply
     */
    tags?: Array<string>;
    /**
     * Scope: user or local
     */
    scope?: string;
};

