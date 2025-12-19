/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Artifact metadata from SKILL.md / COMMAND.md / AGENT.md.
 */
export type ArtifactMetadataResponse = {
    /**
     * Artifact title
     */
    title?: (string | null);
    /**
     * Artifact description
     */
    description?: (string | null);
    /**
     * Artifact author
     */
    author?: (string | null);
    /**
     * Artifact license
     */
    license?: (string | null);
    /**
     * Artifact version from metadata
     */
    version?: (string | null);
    /**
     * Artifact tags
     */
    tags?: Array<string>;
    /**
     * Required dependencies
     */
    dependencies?: Array<string>;
};

