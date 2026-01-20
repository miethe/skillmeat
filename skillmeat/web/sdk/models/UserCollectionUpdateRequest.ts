/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating user collection metadata.
 *
 * Supports partial updates - only provided fields will be modified.
 */
export type UserCollectionUpdateRequest = {
    /**
     * New collection name
     */
    name?: (string | null);
    /**
     * New collection description
     */
    description?: (string | null);
    /**
     * Collection type
     */
    collection_type?: (string | null);
    /**
     * Context category
     */
    context_category?: (string | null);
};

