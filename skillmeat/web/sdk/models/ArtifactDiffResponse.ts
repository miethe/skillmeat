/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FileDiff } from './FileDiff';
/**
 * Response for artifact diff.
 */
export type ArtifactDiffResponse = {
  /**
   * Artifact identifier
   */
  artifact_id: string;
  /**
   * Artifact name
   */
  artifact_name: string;
  /**
   * Artifact type
   */
  artifact_type: string;
  /**
   * Collection name
   */
  collection_name: string;
  /**
   * Project path
   */
  project_path: string;
  /**
   * Whether any changes detected
   */
  has_changes: boolean;
  /**
   * List of file diffs
   */
  files: Array<FileDiff>;
  /**
   * Summary counts: added, modified, deleted, unchanged
   */
  summary: Record<string, number>;
};
