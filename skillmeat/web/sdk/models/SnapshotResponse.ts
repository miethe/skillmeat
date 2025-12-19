/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single snapshot representation.
 *
 * Provides metadata about a collection snapshot including artifact count
 * and timestamp information.
 */
export type SnapshotResponse = {
    /**
     * Snapshot unique identifier (SHA-256 hash)
     */
    id: string;
    /**
     * Snapshot creation timestamp
     */
    timestamp: string;
    /**
     * Snapshot description or commit message
     */
    message: string;
    /**
     * Name of the collection this snapshot belongs to
     */
    collection_name: string;
    /**
     * Number of artifacts captured in this snapshot
     */
    artifact_count: number;
};

