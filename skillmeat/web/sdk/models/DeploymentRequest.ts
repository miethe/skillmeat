/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for deploying an MCP server.
 */
export type DeploymentRequest = {
    /**
     * Preview deployment without applying changes
     */
    dry_run?: boolean;
    /**
     * Create backup of settings.json before deployment
     */
    backup?: boolean;
};

