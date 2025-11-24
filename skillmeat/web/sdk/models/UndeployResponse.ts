/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from an undeploy operation.
 */
export type UndeployResponse = {
    /**
     * Whether undeploy succeeded
     */
    success: boolean;
    /**
     * Status message
     */
    message: string;
    /**
     * Undeployed artifact name
     */
    artifact_name: string;
    /**
     * Undeployed artifact type
     */
    artifact_type: string;
    /**
     * Project path
     */
    project_path: string;
};

