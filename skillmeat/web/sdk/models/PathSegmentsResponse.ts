/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExtractedSegmentResponse } from './ExtractedSegmentResponse';
/**
 * All path segments for a catalog entry.
 *
 * Contains the full path and all extracted segments with their approval
 * status for tag management.
 */
export type PathSegmentsResponse = {
  /**
   * Catalog entry ID
   */
  entry_id: string;
  /**
   * Full artifact path
   */
  raw_path: string;
  /**
   * Extracted segments with status
   */
  extracted: Array<ExtractedSegmentResponse>;
  /**
   * Extraction timestamp
   */
  extracted_at: string;
};
