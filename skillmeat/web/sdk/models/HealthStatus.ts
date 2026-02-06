/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Health check response model.
 */
export type HealthStatus = {
  /**
   * Service status (healthy, degraded, unhealthy)
   */
  status: string;
  /**
   * Current timestamp in ISO format
   */
  timestamp: string;
  /**
   * SkillMeat version
   */
  version: string;
  /**
   * Application environment
   */
  environment: string;
  /**
   * Service uptime in seconds
   */
  uptime_seconds?: number | null;
};
