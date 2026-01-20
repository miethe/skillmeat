/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for pushing collection changes to project.
 *
 * Attributes:
 * project_path: Absolute path to project directory
 * entity_ids: Optional list of entity IDs to push (pushes all if None)
 * overwrite: If True, push even if file modified locally (force)
 */
export type SyncPushRequest = {
    /**
     * Absolute path to project directory
     */
    project_path: string;
    /**
     * Optional list of entity IDs to push (pushes all if None)
     */
    entity_ids?: (Array<string> | null);
    /**
     * If True, push even if file modified locally (force)
     */
    overwrite?: boolean;
};

