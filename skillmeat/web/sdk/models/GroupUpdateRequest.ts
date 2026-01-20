/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating a group.
 *
 * All fields are optional. Only provided fields will be updated.
 */
export type GroupUpdateRequest = {
    /**
     * New group name
     */
    name?: (string | null);
    /**
     * New description
     */
    description?: (string | null);
    /**
     * New position in collection
     */
    position?: (number | null);
};

