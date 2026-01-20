/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Detailed health check response with component status.
 */
export type DetailedHealthStatus = {
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
  /**
   * Health status of individual components
   */
  components: Record<string, Record<string, string>>;
  /**
   * System information
   */
  system_info: Record<string, string>;
};
