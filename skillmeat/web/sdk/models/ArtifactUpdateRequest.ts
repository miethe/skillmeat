/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactUpdateMetadataRequest } from './ArtifactUpdateMetadataRequest';
/**
 * Request schema for updating an artifact.
 *
 * Allows updating metadata and tags. Note: aliases are not yet
 * implemented in the backend but are included for future compatibility.
 */
export type ArtifactUpdateRequest = {
  /**
   * Artifact aliases (not yet implemented)
   */
  aliases?: Array<string> | null;
  /**
   * Artifact tags
   */
  tags?: Array<string> | null;
  /**
   * Artifact metadata to update
   */
  metadata?: ArtifactUpdateMetadataRequest | null;
};
