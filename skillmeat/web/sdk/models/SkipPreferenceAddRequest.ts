/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to add a skip preference.
 */
export type SkipPreferenceAddRequest = {
  /**
   * Artifact identifier in format 'type:name'
   */
  artifact_key: string;
  /**
   * Human-readable reason for skipping this artifact
   */
  skip_reason: string;
};
