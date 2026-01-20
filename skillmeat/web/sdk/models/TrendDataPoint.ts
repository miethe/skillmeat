/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single data point in a usage trend.
 *
 * Represents aggregated usage data for a specific time period.
 */
export type TrendDataPoint = {
    /**
     * Start of time period
     */
    timestamp: string;
    /**
     * Time period type (hour, day, week, month)
     */
    period: string;
    /**
     * Number of deployments in this period
     */
    deployment_count: number;
    /**
     * Total usage events in this period
     */
    usage_count: number;
    /**
     * Number of unique artifacts used in this period
     */
    unique_artifacts: number;
    /**
     * Most used artifact in this period
     */
    top_artifact: string;
};

