/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for a single group.
 */
export type GroupResponse = {
    /**
     * Group unique identifier
     */
    id: string;
    /**
     * Collection this group belongs to
     */
    collection_id: string;
    /**
     * Group name
     */
    name: string;
    /**
     * Group description
     */
    description?: (string | null);
    /**
     * Display order in collection
     */
    position: number;
    /**
     * Group creation timestamp
     */
    created_at: string;
    /**
     * Last update timestamp
     */
    updated_at: string;
    /**
     * Number of artifacts in this group
     */
    artifact_count: number;
};

