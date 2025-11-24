/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for a single collection.
 *
 * Provides complete collection metadata including artifact count
 * and timestamps.
 */
export type CollectionResponse = {
    /**
     * Collection unique identifier
     */
    id: string;
    /**
     * Collection name
     */
    name: string;
    /**
     * Collection format version
     */
    version: string;
    /**
     * Number of artifacts in collection
     */
    artifact_count: number;
    /**
     * Collection creation timestamp
     */
    created: string;
    /**
     * Last update timestamp
     */
    updated: string;
};

