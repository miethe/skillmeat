/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating a new MCP server.
 */
export type MCPServerCreateRequest = {
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
};

