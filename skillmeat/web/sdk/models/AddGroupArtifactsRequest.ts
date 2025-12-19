/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for adding artifacts to a group.
 */
export type AddGroupArtifactsRequest = {
    /**
     * List of artifact IDs to add to the group
     */
    artifact_ids: Array<string>;
    /**
     * Position to insert artifacts at (default: append)
     */
    position?: (number | null);
};

