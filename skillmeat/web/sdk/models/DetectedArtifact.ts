/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * An artifact detected during scanning.
 *
 * Internal model used by scanning service, not directly exposed via API.
 */
export type DetectedArtifact = {
  /**
   * Type of artifact detected
   */
  artifact_type: string;
  /**
   * Artifact name
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
   * Confidence score of detection (0-100)
   */
  confidence_score: number;
  /**
   * Git commit SHA at time of detection
   */
  detected_sha?: string | null;
  /**
   * Version extracted from manifest
   */
  detected_version?: string | null;
  /**
   * Additional metadata extracted during detection
   */
  metadata?: Record<string, any> | null;
  /**
   * Raw unscaled confidence score before normalization (0-120 typical)
   */
  raw_score?: number | null;
  /**
   * Detailed breakdown of heuristic signal scores
   */
  score_breakdown?: Record<string, number> | null;
  /**
   * Whether this artifact was excluded during deduplication
   */
  excluded?: boolean | null;
  /**
   * Reason for exclusion (e.g., 'within_source_duplicate', 'cross_source_duplicate')
   */
  excluded_reason?: string | null;
  /**
   * ISO timestamp when artifact was marked as excluded
   */
  excluded_at?: string | null;
  /**
   * Path of the artifact this is a duplicate of (for within-source duplicates)
   */
  duplicate_of?: string | null;
  /**
   * SHA256 content hash of artifact files (for deduplication)
   */
  content_hash?: string | null;
  /**
   * Artifact status (e.g., 'new', 'excluded')
   */
  status?: string | null;
};
