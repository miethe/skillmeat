/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating artifact link.
 */
export type CreateLinkedArtifactRequest = {
  /**
   * ID of artifact to link to
   */
  target_artifact_id: string;
  /**
   * Type of relationship: requires, enables, or related
   */
  link_type?: string;
};
