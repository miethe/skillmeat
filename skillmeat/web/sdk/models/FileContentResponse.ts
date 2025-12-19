/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for artifact file content.
 */
export type FileContentResponse = {
    /**
     * Artifact identifier
     */
    artifact_id: string;
    /**
     * Artifact name
     */
    artifact_name: string;
    /**
     * Artifact type
     */
    artifact_type: string;
    /**
     * Collection name
     */
    collection_name: string;
    /**
     * Relative file path within artifact
     */
    path: string;
    /**
     * File content (UTF-8 encoded)
     */
    content: string;
    /**
     * File size in bytes
     */
    size: number;
    /**
     * MIME type of the file
     */
    mime_type?: (string | null);
};

