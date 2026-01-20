/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating artifact metadata fields.
 */
export type ArtifactUpdateMetadataRequest = {
  /**
   * Artifact title
   */
  title?: string | null;
  /**
   * Artifact description
   */
  description?: string | null;
  /**
   * Artifact author
   */
  author?: string | null;
  /**
   * Artifact license
   */
  license?: string | null;
  /**
   * Artifact tags
   */
  tags?: Array<string> | null;
};
