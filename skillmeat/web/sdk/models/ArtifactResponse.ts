/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactMetadataResponse } from './ArtifactMetadataResponse';
import type { ArtifactUpstreamInfo } from './ArtifactUpstreamInfo';
import type { DeploymentStatistics } from './DeploymentStatistics';
/**
 * Response schema for a single artifact.
 *
 * Provides complete artifact information including metadata,
 * deployment status, and upstream tracking.
 */
export type ArtifactResponse = {
    /**
     * Artifact composite key (type:name)
     */
    id: string;
    /**
     * Artifact name
     */
    name: string;
    /**
     * Artifact type
     */
    type: string;
    /**
     * Source specification
     */
    source: string;
    /**
     * Version specification
     */
    version: string;
    /**
     * Artifact aliases
     */
    aliases?: Array<string>;
    /**
     * Artifact tags
     */
    tags?: Array<string>;
    /**
     * Artifact metadata
     */
    metadata?: (ArtifactMetadataResponse | null);
    /**
     * Upstream tracking information
     */
    upstream?: (ArtifactUpstreamInfo | null);
    /**
     * Deployment statistics (included when include_deployments=true)
     */
    deployment_stats?: (DeploymentStatistics | null);
    /**
     * Timestamp when artifact was added to collection
     */
    added: string;
    /**
     * Timestamp of last update
     */
    updated: string;
};

