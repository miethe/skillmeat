/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for rating submission confirmation.
 *
 * Confirms successful rating submission and provides server-assigned metadata.
 */
export type UserRatingResponse = {
  /**
   * Database-assigned rating ID
   */
  id: number;
  /**
   * Artifact that was rated (type:name)
   */
  artifact_id: string;
  /**
   * Submitted rating value (1-5)
   */
  rating: number;
  /**
   * Submitted feedback text
   */
  feedback?: string | null;
  /**
   * Whether rating is shared with community
   */
  share_with_community: boolean;
  /**
   * Timestamp when rating was recorded
   */
  rated_at: string;
  /**
   * Schema version for future migrations
   */
  schema_version?: string;
};
