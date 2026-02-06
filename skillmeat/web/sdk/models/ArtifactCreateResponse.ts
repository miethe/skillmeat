/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for artifact creation.
 */
export type ArtifactCreateResponse = {
  /**
   * Whether creation succeeded
   */
  success: boolean;
  /**
   * Artifact ID (format: type:name)
   */
  artifact_id: string;
  /**
   * Name of created artifact
   */
  artifact_name: string;
  /**
   * Type of artifact
   */
  artifact_type: string;
  /**
   * Collection name
   */
  collection: string;
  /**
   * Source specification or path
   */
  source: string;
  /**
   * Source type (github or local)
   */
  source_type: string;
  /**
   * Path to artifact in collection
   */
  path: string;
  /**
   * Human-readable result message
   */
  message: string;
};
