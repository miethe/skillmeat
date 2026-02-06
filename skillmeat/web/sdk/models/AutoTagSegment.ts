/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single auto-tag extracted from GitHub repository topics.
 *
 * Represents a tag suggested from GitHub repository topics that can be
 * approved or rejected by the user for inclusion in source tags.
 */
export type AutoTagSegment = {
  /**
   * Original topic value from GitHub
   */
  value: string;
  /**
   * Normalized value for consistent tagging
   */
  normalized: string;
  /**
   * Approval status
   */
  status: 'pending' | 'approved' | 'rejected';
  /**
   * Source of the auto-tag
   */
  source?: string;
};
