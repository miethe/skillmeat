/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for a detected artifact in the catalog.
 *
 * Represents an artifact discovered during repository scanning.
 */
export type CatalogEntryResponse = {
    /**
     * Unique identifier for the catalog entry
     */
    id: string;
    /**
     * ID of the source this artifact was detected in
     */
    source_id: string;
    /**
     * Type of artifact detected
     */
    artifact_type: 'skill' | 'command' | 'agent' | 'mcp_server' | 'hook';
    /**
     * Artifact name extracted from manifest or inferred
     */
    name: string;
    /**
     * Path to artifact within repository
     */
    path: string;
    /**
     * Full URL to artifact in source repository
     */
    upstream_url: string;
    /**
     * Version extracted from manifest or inferred
     */
    detected_version?: (string | null);
    /**
     * Git commit SHA at time of detection
     */
    detected_sha?: (string | null);
    /**
     * Timestamp when artifact was first detected
     */
    detected_at: string;
    /**
     * Confidence score of detection (0-100)
     */
    confidence_score: number;
    /**
     * Lifecycle status of the catalog entry
     */
    status: 'new' | 'updated' | 'removed' | 'imported';
    /**
     * Timestamp when artifact was imported to collection
     */
    import_date?: (string | null);
    /**
     * ID of import operation if imported
     */
    import_id?: (string | null);
};

