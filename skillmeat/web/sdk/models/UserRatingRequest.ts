/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for submitting artifact rating.
 *
 * Allows users to rate artifacts and optionally provide feedback.
 */
export type UserRatingRequest = {
  /**
   * Numeric rating from 1 (poor) to 5 (excellent)
   */
  rating: number;
  /**
   * Optional text feedback from user
   */
  feedback?: string | null;
  /**
   * Whether to share rating with community (opt-in)
   */
  share_with_community?: boolean;
};
