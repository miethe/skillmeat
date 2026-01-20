/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Hash-based collection matching result for a discovered artifact.
 *
 * Provides detailed information about how an artifact matches against
 * the collection using content hash and name+type matching.
 *
 * Attributes:
 * type: Type of match found:
 * - "exact": Content hash exact match (confidence: 1.0)
 * - "hash": Legacy alias for exact hash match (confidence: 1.0)
 * - "name_type": Name and type match but different content (confidence: 0.85)
 * - "none": No match found (confidence: 0.0)
 * matched_artifact_id: ID of matched artifact if found (format: type:name)
 * matched_name: Name of the matched artifact
 * confidence: Confidence score (0.0-1.0) indicating match quality
 */
export type CollectionMatch = {
  /**
   * Match type: 'exact' (hash match, 1.0 confidence), 'hash' (alias for exact), 'name_type' (0.85 confidence), 'none' (no match, 0.0 confidence)
   */
  type: string;
  /**
   * ID of matched artifact in collection (format: type:name)
   */
  matched_artifact_id?: string | null;
  /**
   * Name of the matched artifact
   */
  matched_name?: string | null;
  /**
   * Confidence score from 0.0 (no match) to 1.0 (exact hash match)
   */
  confidence: number;
};
