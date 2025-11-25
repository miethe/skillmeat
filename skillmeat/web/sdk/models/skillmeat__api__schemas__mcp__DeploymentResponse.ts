/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for deployment operation.
 */
export type skillmeat__api__schemas__mcp__DeploymentResponse = {
    /**
     * Whether deployment succeeded
     */
    success: boolean;
    /**
     * Human-readable result message
     */
    message: string;
    /**
     * Path to settings.json
     */
    settings_path?: (string | null);
    /**
     * Path to backup file
     */
    backup_path?: (string | null);
    /**
     * Path to .env file with environment variables
     */
    env_file_path?: (string | null);
    /**
     * Command configured for the server
     */
    command?: (string | null);
    /**
     * Arguments configured for the server
     */
    args?: (Array<string> | null);
    /**
     * Error details if deployment failed
     */
    error_message?: (string | null);
};

