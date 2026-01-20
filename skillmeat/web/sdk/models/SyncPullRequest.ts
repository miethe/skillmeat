/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for pulling changes from project to collection.
 *
 * Attributes:
 * project_path: Absolute path to project directory
 * entity_ids: Optional list of entity IDs to pull (pulls all if None)
 */
export type SyncPullRequest = {
    /**
     * Absolute path to project directory
     */
    project_path: string;
    /**
     * Optional list of entity IDs to pull (pulls all if None)
     */
    entity_ids?: (Array<string> | null);
};

