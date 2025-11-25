/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AllServersHealthResponse } from '../models/AllServersHealthResponse';
import type { DeploymentRequest } from '../models/DeploymentRequest';
import type { DeploymentStatusResponse } from '../models/DeploymentStatusResponse';
import type { HealthCheckResponse } from '../models/HealthCheckResponse';
import type { MCPServerCreateRequest } from '../models/MCPServerCreateRequest';
import type { MCPServerListResponse } from '../models/MCPServerListResponse';
import type { MCPServerResponse } from '../models/MCPServerResponse';
import type { MCPServerUpdateRequest } from '../models/MCPServerUpdateRequest';
import type { skillmeat__api__schemas__mcp__DeploymentResponse } from '../models/skillmeat__api__schemas__mcp__DeploymentResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class McpService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * List all MCP servers
     * Retrieve all MCP servers in the collection
     * @returns MCPServerListResponse Successfully retrieved MCP servers
     * @throws ApiError
     */
    public listMcpServersApiV1McpServersGet({
        collection,
    }: {
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<MCPServerListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/mcp/servers',
            query: {
                'collection': collection,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Add new MCP server
     * Add a new MCP server to the collection
     * @returns MCPServerResponse Server created successfully
     * @throws ApiError
     */
    public createMcpServerApiV1McpServersPost({
        requestBody,
        collection,
    }: {
        requestBody: MCPServerCreateRequest,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<MCPServerResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/mcp/servers',
            query: {
                'collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                409: `Server already exists`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get MCP server details
     * Retrieve detailed information about a specific MCP server
     * @returns MCPServerResponse Successfully retrieved server details
     * @throws ApiError
     */
    public getMcpServerApiV1McpServersNameGet({
        name,
        collection,
    }: {
        name: string,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<MCPServerResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/mcp/servers/{name}',
            path: {
                'name': name,
            },
            query: {
                'collection': collection,
            },
            errors: {
                401: `Unauthorized`,
                404: `Server not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Update MCP server
     * Update an existing MCP server configuration
     * @returns MCPServerResponse Server updated successfully
     * @throws ApiError
     */
    public updateMcpServerApiV1McpServersNamePut({
        name,
        requestBody,
        collection,
    }: {
        name: string,
        requestBody: MCPServerUpdateRequest,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<MCPServerResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/mcp/servers/{name}',
            path: {
                'name': name,
            },
            query: {
                'collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Server not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Delete MCP server
     * Remove an MCP server from the collection
     * @returns void
     * @throws ApiError
     */
    public deleteMcpServerApiV1McpServersNameDelete({
        name,
        collection,
    }: {
        name: string,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/mcp/servers/{name}',
            path: {
                'name': name,
            },
            query: {
                'collection': collection,
            },
            errors: {
                401: `Unauthorized`,
                404: `Server not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Deploy MCP server
     * Deploy MCP server to Claude Desktop settings.json
     * @returns skillmeat__api__schemas__mcp__DeploymentResponse Server deployed successfully
     * @throws ApiError
     */
    public deployMcpServerApiV1McpServersNameDeployPost({
        name,
        requestBody,
        collection,
    }: {
        name: string,
        requestBody: DeploymentRequest,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<skillmeat__api__schemas__mcp__DeploymentResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/mcp/servers/{name}/deploy',
            path: {
                'name': name,
            },
            query: {
                'collection': collection,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid request`,
                401: `Unauthorized`,
                404: `Server not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Undeploy MCP server
     * Remove MCP server from Claude Desktop settings.json
     * @returns skillmeat__api__schemas__mcp__DeploymentResponse Server undeployed successfully
     * @throws ApiError
     */
    public undeployMcpServerApiV1McpServersNameUndeployPost({
        name,
        collection,
    }: {
        name: string,
        /**
         * Collection name (uses default if not specified)
         */
        collection?: (string | null),
    }): CancelablePromise<skillmeat__api__schemas__mcp__DeploymentResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/mcp/servers/{name}/undeploy',
            path: {
                'name': name,
            },
            query: {
                'collection': collection,
            },
            errors: {
                401: `Unauthorized`,
                404: `Server not found`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Get deployment status
     * Check if MCP server is deployed to Claude Desktop
     * @returns DeploymentStatusResponse Successfully retrieved deployment status
     * @throws ApiError
     */
    public getDeploymentStatusApiV1McpServersNameStatusGet({
        name,
    }: {
        name: string,
    }): CancelablePromise<DeploymentStatusResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/mcp/servers/{name}/status',
            path: {
                'name': name,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Check MCP server health
     * Get health status for a specific MCP server
     * @returns HealthCheckResponse Successfully retrieved health status
     * @throws ApiError
     */
    public getServerHealthApiV1McpServersNameHealthGet({
        name,
        useCache = true,
    }: {
        name: string,
        /**
         * Use cached results (30 second TTL)
         */
        useCache?: boolean,
    }): CancelablePromise<HealthCheckResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/mcp/servers/{name}/health',
            path: {
                'name': name,
            },
            query: {
                'use_cache': useCache,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
    /**
     * Check all MCP servers health
     * Get health status for all deployed MCP servers
     * @returns AllServersHealthResponse Successfully retrieved health status for all servers
     * @throws ApiError
     */
    public getAllServersHealthApiV1McpHealthGet({
        useCache = true,
    }: {
        /**
         * Use cached results (30 second TTL)
         */
        useCache?: boolean,
    }): CancelablePromise<AllServersHealthResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/mcp/health',
            query: {
                'use_cache': useCache,
            },
            errors: {
                401: `Unauthorized`,
                422: `Validation Error`,
                500: `Internal server error`,
            },
        });
    }
}
