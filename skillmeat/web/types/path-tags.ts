/**
 * Path-based tag extraction type definitions
 *
 * Matches Python backend schema from:
 * skillmeat/api/app/schemas/marketplace.py
 */

/**
 * Represents a single extracted segment from a file path
 */
export interface ExtractedSegment {
  /** Original segment from path */
  segment: string;

  /** Normalized version for tag use */
  normalized: string;

  /** Current status of the segment */
  status: 'pending' | 'approved' | 'rejected' | 'excluded';

  /** Reason for exclusion (only populated when status is 'excluded') */
  reason?: string;
}

/**
 * Response containing extracted path segments for an entry
 */
export interface PathSegmentsResponse {
  /** Entry ID */
  entry_id: string;

  /** Original file path */
  raw_path: string;

  /** List of extracted segments with their statuses */
  extracted: ExtractedSegment[];

  /** ISO 8601 timestamp when segments were extracted */
  extracted_at: string;
}

/**
 * Request to update the status of a segment
 */
export interface UpdateSegmentStatusRequest {
  /** Original segment value to update */
  segment: string;

  /** New status for the segment (only approve/reject allowed in requests) */
  status: 'approved' | 'rejected';
}

/**
 * Response after updating segment status
 * Returns the updated path segments
 */
export type UpdateSegmentStatusResponse = PathSegmentsResponse;
