/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * An artifact discovered during scanning.
 */
export type DiscoveredArtifact = {
    /**
     * Artifact type: skill, command, agent, hook, mcp
     */
    type: string;
    /**
     * Artifact name
     */
    name: string;
    /**
     * GitHub source if known
     */
    source?: (string | null);
    /**
     * Version if known
     */
    version?: (string | null);
    /**
     * Scope: user or local
     */
    scope?: (string | null);
    /**
     * Tags
     */
    tags?: (Array<string> | null);
    /**
     * Description
     */
    description?: (string | null);
    /**
     * Full path to artifact directory
     */
    path: string;
    /**
     * When artifact was discovered
     */
    discovered_at: string;
};

