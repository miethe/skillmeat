/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for deployment status.
 */
export type DeploymentStatusResponse = {
    /**
     * Whether server is deployed to Claude Desktop
     */
    deployed: boolean;
    /**
     * Path to Claude Desktop settings.json
     */
    settings_path?: (string | null);
    /**
     * ISO 8601 timestamp of last deployment
     */
    last_deployed?: (string | null);
    /**
     * Health check status (healthy, unhealthy, unknown)
     */
    health_status?: (string | null);
    /**
     * Command used to run the server
     */
    command?: (string | null);
    /**
     * Arguments passed to the command
     */
    args?: (Array<string> | null);
};

