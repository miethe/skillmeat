/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MCPServerResponse } from './MCPServerResponse';
/**
 * Response schema for listing MCP servers.
 */
export type MCPServerListResponse = {
  /**
   * List of MCP servers
   */
  servers: Array<MCPServerResponse>;
  /**
   * Total number of servers
   */
  total: number;
};
