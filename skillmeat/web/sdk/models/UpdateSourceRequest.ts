/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to update a GitHub repository source.
 *
 * All fields are optional - only provided fields will be updated.
 * Uses PATCH semantics for partial updates.
 */
export type UpdateSourceRequest = {
    /**
     * Branch, tag, or SHA to scan
     */
    ref?: (string | null);
    /**
     * Subdirectory path within repository to start scanning
     */
    root_hint?: (string | null);
    /**
     * Trust level for artifacts from this source
     */
    trust_level?: ('untrusted' | 'basic' | 'verified' | 'official' | null);
    /**
     * User-provided description for this source (max 500 chars)
     */
    description?: (string | null);
    /**
     * Internal notes/documentation for this source (max 2000 chars)
     */
    notes?: (string | null);
};

