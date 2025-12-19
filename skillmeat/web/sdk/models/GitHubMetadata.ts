/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Metadata fetched from GitHub.
 */
export type GitHubMetadata = {
    /**
     * Repository or artifact title
     */
    title?: (string | null);
    /**
     * Repository or artifact description
     */
    description?: (string | null);
    /**
     * Repository owner or artifact author
     */
    author?: (string | null);
    /**
     * Repository license
     */
    license?: (string | null);
    /**
     * Repository topics (tags)
     */
    topics?: Array<string>;
    /**
     * GitHub URL
     */
    url: string;
    /**
     * Timestamp when metadata was fetched
     */
    fetched_at: string;
    /**
     * Source of metadata
     */
    source?: string;
};

