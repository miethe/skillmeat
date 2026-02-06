/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single extracted path segment with approval status.
 *
 * Represents a single segment from an artifact path with its normalized
 * value and approval/rejection status for tag creation.
 */
export type ExtractedSegmentResponse = {
  /**
   * Original segment from path
   */
  segment: string;
  /**
   * Normalized segment value
   */
  normalized: string;
  /**
   * Approval status
   */
  status: 'pending' | 'approved' | 'rejected' | 'excluded';
  /**
   * Reason if excluded
   */
  reason?: string | null;
};
