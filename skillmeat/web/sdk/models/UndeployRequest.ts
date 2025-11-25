/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to undeploy (remove) an artifact from a project.
 */
export type UndeployRequest = {
    /**
     * Artifact name
     */
    artifact_name: string;
    /**
     * Artifact type
     */
    artifact_type: string;
    /**
     * Path to project directory (uses CWD if not specified)
     */
    project_path?: (string | null);
};

