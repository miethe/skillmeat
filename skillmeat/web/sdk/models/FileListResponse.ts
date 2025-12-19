/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FileNode } from './FileNode';
/**
 * Response for artifact file listing.
 */
export type FileListResponse = {
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
     * File tree structure
     */
    files: Array<FileNode>;
};

