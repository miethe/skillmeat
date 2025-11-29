/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Version information for a single artifact instance.
 *
 * Represents a specific version of an artifact at a point in time,
 * tracking content hash and parent lineage.
 */
export type ArtifactVersionInfo = {
  /**
   * Artifact name
   */
  artifact_name: string;
  /**
   * Artifact type (skill/command/agent)
   */
  artifact_type: string;
  /**
   * Location (collection name or absolute project path)
   */
  location: string;
  /**
   * Type of location
   */
  location_type: 'collection' | 'project';
  /**
   * SHA-256 content hash of artifact
   */
  content_sha: string;
  /**
   * Parent version SHA (for tracking lineage)
   */
  parent_sha?: string | null;
  /**
   * Whether content differs from parent version
   */
  is_modified: boolean;
  /**
   * Version creation timestamp
   */
  created_at: string;
  /**
   * Additional version metadata
   */
  metadata?: Record<string, any>;
};
