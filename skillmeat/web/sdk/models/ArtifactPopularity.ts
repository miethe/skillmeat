/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Popular artifact statistics.
 */
export type ArtifactPopularity = {
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
    deploy_count: number;
    /**
     * ISO 8601 timestamp of last deployment
     */
    last_deployed?: (string | null);
};

