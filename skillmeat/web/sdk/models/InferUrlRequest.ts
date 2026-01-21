/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to infer GitHub source structure from a full URL.
 *
 * Supports parsing GitHub URLs to extract repository, ref, and subdirectory.
 */
export type InferUrlRequest = {
    /**
     * GitHub URL to parse (full URL with branch/path or basic repo URL)
     */
    url: string;
};

