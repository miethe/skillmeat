/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to deploy an artifact to a project.
 */
export type DeployRequest = {
    /**
     * Artifact identifier (format: 'type:name')
     */
    artifact_id: string;
    /**
     * Artifact name for display
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
    /**
     * Source collection name (uses active collection if None)
     */
    collection_name?: (string | null);
    /**
     * Overwrite existing deployment without prompting
     */
    overwrite?: boolean;
};

