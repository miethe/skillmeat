/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response containing a skip preference.
 */
export type SkipPreferenceResponse = {
  /**
   * Artifact identifier in format 'type:name'
   */
  artifact_key: string;
  /**
   * Human-readable reason for skipping this artifact
   */
  skip_reason: string;
  /**
   * When this skip preference was added (ISO 8601 format)
   */
  added_date: string;
};
