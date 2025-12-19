/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single artifact in the top artifacts list.
 *
 * Represents an artifact with its usage statistics.
 */
export type TopArtifactItem = {
    /**
     * Artifact name
     */
    artifact_name: string;
    /**
     * Artifact type
     */
    artifact_type: string;
    /**
     * Number of times deployed
     */
    deployment_count: number;
    /**
     * Total usage events
     */
    usage_count: number;
    /**
     * Timestamp of last usage
     */
    last_used: string;
    /**
     * Collections containing this artifact
     */
    collections: Array<string>;
};

