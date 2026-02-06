/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthCheckResponse } from './HealthCheckResponse';
/**
 * Response schema for health check of all servers.
 */
export type AllServersHealthResponse = {
  /**
   * Health status for each server
   */
  servers: Record<string, HealthCheckResponse>;
  /**
   * Total number of servers checked
   */
  total: number;
  /**
   * Number of healthy servers
   */
  healthy?: number;
  /**
   * Number of degraded servers
   */
  degraded?: number;
  /**
   * Number of unhealthy servers
   */
  unhealthy?: number;
};
