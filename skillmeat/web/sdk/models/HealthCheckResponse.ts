/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for MCP server health check.
 */
export type HealthCheckResponse = {
    /**
     * Name of the MCP server
     */
    server_name: string;
    /**
     * Health status (healthy, degraded, unhealthy, unknown, not_deployed)
     */
    status: string;
    /**
     * Whether server is deployed to Claude Desktop
     */
    deployed: boolean;
    /**
     * ISO 8601 timestamp of last log entry
     */
    last_seen?: (string | null);
    /**
     * Number of recent errors
     */
    error_count?: number;
    /**
     * Number of recent warnings
     */
    warning_count?: number;
    /**
     * List of recent error messages
     */
    recent_errors?: Array<string>;
    /**
     * List of recent warning messages
     */
    recent_warnings?: Array<string>;
    /**
     * ISO 8601 timestamp of health check
     */
    checked_at: string;
};

