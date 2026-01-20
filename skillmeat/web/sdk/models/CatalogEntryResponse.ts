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
    artifact_type: 'skill' | 'command' | 'agent' | 'mcp' | 'mcp_server' | 'hook';
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
     * Raw score before normalization (0-120 typical)
     */
    raw_score?: (number | null);
    /**
     * Detailed signal breakdown: dir_name_score (0-10), manifest_score (0-20), extensions_score (0-5), parent_hint_score (0-15), frontmatter_score (0-15), depth_penalty (negative), raw_total, normalized_score (0-100)
     */
    score_breakdown?: (Record<string, number> | null);
    /**
     * Lifecycle status of the catalog entry
     */
    status: 'new' | 'updated' | 'removed' | 'imported' | 'excluded';
    /**
     * Timestamp when artifact was imported to collection
     */
    import_date?: (string | null);
    /**
     * ID of import operation if imported
     */
    import_id?: (string | null);
    /**
     * ISO 8601 timestamp when artifact was marked as excluded from catalog. Null if not excluded.
     */
    excluded_at?: (string | null);
    /**
     * User-provided reason for exclusion (max 500 chars). Null if not excluded or no reason provided.
     */
    excluded_reason?: (string | null);
    /**
     * Whether this artifact was excluded as a duplicate (within-source or cross-source)
     */
    is_duplicate?: boolean;
    /**
     * Whether an artifact with matching name and type exists in the active collection
     */
    in_collection?: boolean;
};

