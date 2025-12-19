/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Artifact information in preview.
 */
export type PreviewArtifact = {
    /**
     * Artifact name
     */
    name: string;
    /**
     * Artifact type (skill, command, agent)
     */
    type: string;
    /**
     * Artifact version
     */
    version?: (string | null);
    /**
     * Relative path in bundle
     */
    path: string;
    /**
     * Whether this artifact conflicts with existing one
     */
    has_conflict?: boolean;
    /**
     * Version of existing artifact if conflict exists
     */
    existing_version?: (string | null);
};

