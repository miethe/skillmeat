/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single imported artifact in import result.
 */
export type ImportedArtifactResponse = {
    /**
     * Artifact name
     */
    name: string;
    /**
     * Artifact type (skill, command, agent)
     */
    type: string;
    /**
     * How conflict was resolved (imported, forked, skipped, merged)
     */
    resolution: string;
    /**
     * New name if forked
     */
    new_name?: (string | null);
    /**
     * Reason for resolution decision
     */
    reason?: (string | null);
};

