/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response containing inferred GitHub source structure.
 *
 * Returns parsed components or error message if parsing failed.
 */
export type InferUrlResponse = {
    /**
     * Whether URL was successfully parsed
     */
    success: boolean;
    /**
     * Base repository URL (e.g., https://github.com/owner/repo)
     */
    repo_url?: (string | null);
    /**
     * Branch, tag, or SHA extracted from URL (defaults to 'main' if not specified)
     */
    ref?: (string | null);
    /**
     * Subdirectory path within repository (None if URL points to repo root)
     */
    root_hint?: (string | null);
    /**
     * Error message if parsing failed (None on success)
     */
    error?: (string | null);
};

