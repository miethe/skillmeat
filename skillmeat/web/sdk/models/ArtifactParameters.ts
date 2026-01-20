/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Updatable artifact parameters.
 */
export type ArtifactParameters = {
    /**
     * GitHub source or local path
     */
    source?: (string | null);
    /**
     * Version specification
     */
    version?: (string | null);
    /**
     * Scope: user or local
     */
    scope?: (string | null);
    /**
     * Tags to apply (replaces existing tags)
     */
    tags?: (Array<string> | null);
    /**
     * Aliases to apply (replaces existing aliases)
     */
    aliases?: (Array<string> | null);
};

