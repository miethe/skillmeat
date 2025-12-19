/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating a tag.
 *
 * All fields are optional to support partial updates.
 */
export type TagUpdateRequest = {
    /**
     * Tag name
     */
    name?: (string | null);
    /**
     * URL-friendly slug (kebab-case)
     */
    slug?: (string | null);
    /**
     * Hex color code (e.g., #FF5733)
     */
    color?: (string | null);
};

