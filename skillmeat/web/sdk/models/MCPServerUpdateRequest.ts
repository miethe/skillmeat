/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating an MCP server.
 */
export type MCPServerUpdateRequest = {
    /**
     * GitHub repository
     */
    repo?: (string | null);
    /**
     * Version spec
     */
    version?: (string | null);
    /**
     * Server description
     */
    description?: (string | null);
    /**
     * Environment variables (replaces existing)
     */
    env_vars?: (Record<string, string> | null);
};

