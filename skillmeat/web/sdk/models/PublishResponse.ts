/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for publish operations.
 *
 * Contains submission details and status information.
 */
export type PublishResponse = {
  /**
   * Unique identifier for the submission
   */
  submission_id: string;
  /**
   * Submission status
   */
  status: 'pending' | 'approved' | 'rejected';
  /**
   * Status message
   */
  message: string;
  /**
   * Broker the bundle was published to
   */
  broker: string;
  /**
   * URL to view the listing (if approved)
   */
  listing_url?: string | null;
};
