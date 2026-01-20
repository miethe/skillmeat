/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GroupSummary } from './GroupSummary';
/**
 * Response schema for a collection with nested groups.
 *
 * Extends UserCollectionResponse with full group details.
 */
export type UserCollectionWithGroupsResponse = {
    /**
     * Collection unique identifier
     */
    id: string;
    /**
     * Collection name
     */
    name: string;
    /**
     * Collection description
     */
    description?: (string | null);
    /**
     * User identifier (for future multi-user support)
     */
    created_by?: (string | null);
    /**
     * Collection type
     */
    collection_type?: (string | null);
    /**
     * Context category
     */
    context_category?: (string | null);
    /**
     * Collection creation timestamp
     */
    created_at: string;
    /**
     * Last update timestamp
     */
    updated_at: string;
    /**
     * Number of groups in collection
     */
    group_count: number;
    /**
     * Total number of artifacts in collection
     */
    artifact_count: number;
    /**
     * List of groups in this collection
     */
    groups?: Array<GroupSummary>;
};

