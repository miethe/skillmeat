/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Summary of an artifact within a collection.
 *
 * Lightweight artifact representation for collection listings.
 */
export type ArtifactSummary = {
    /**
     * Artifact name
     */
    name: string;
    /**
     * Artifact type (skill, command, agent)
     */
    type: string;
    /**
     * Current version
     */
    version?: (string | null);
    /**
     * Source specification
     */
    source: string;
};

