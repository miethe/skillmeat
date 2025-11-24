/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactSourceType } from './ArtifactSourceType';
/**
 * Request schema for creating an artifact.
 */
export type ArtifactCreateRequest = {
    /**
     * Source type: github or local
     */
    source_type: ArtifactSourceType;
    /**
     * GitHub URL/spec or local path
     */
    source: string;
    /**
     * Type of artifact (skill, command, agent, mcp, hook)
     */
    artifact_type: string;
    /**
     * Override artifact name
     */
    name?: (string | null);
    /**
     * Target collection (uses default if not specified)
     */
    collection?: (string | null);
    /**
     * Tags to apply
     */
    tags?: (Array<string> | null);
    /**
     * Override description
     */
    description?: (string | null);
};

