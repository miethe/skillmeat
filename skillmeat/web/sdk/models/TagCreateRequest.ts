/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating a tag.
 *
 * All fields from TagBase are required except color (optional).
 */
export type TagCreateRequest = {
    /**
     * Tag name
     */
    name: string;
    /**
     * URL-friendly slug (kebab-case)
     */
    slug: string;
    /**
     * Hex color code (e.g., #FF5733)
     */
    color?: (string | null);
};

