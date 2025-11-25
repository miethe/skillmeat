/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for MCP server details.
 */
export type MCPServerResponse = {
    /**
     * Unique server name (alphanumeric, dash, underscore)
     */
    name: string;
    /**
     * GitHub repository (user/repo or full URL)
     */
    repo: string;
    /**
     * Version spec (latest, tag, or SHA)
     */
    version?: string;
    /**
     * Human-readable description
     */
    description?: (string | null);
    /**
     * Environment variables as key-value pairs
     */
    env_vars?: Record<string, string>;
    /**
     * Installation status
     */
    status: string;
    /**
     * ISO 8601 timestamp of installation
     */
    installed_at?: (string | null);
    /**
     * Resolved git SHA
     */
    resolved_sha?: (string | null);
    /**
     * Resolved version tag
     */
    resolved_version?: (string | null);
    /**
     * ISO 8601 timestamp of last update
     */
    last_updated?: (string | null);
};

