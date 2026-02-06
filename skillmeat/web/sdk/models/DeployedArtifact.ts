/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactCollectionInfo } from './ArtifactCollectionInfo';
/**
 * Summary of a deployed artifact within a project.
 *
 * Represents an artifact that has been deployed from a collection
 * to a specific project location.
 */
export type DeployedArtifact = {
  /**
   * Name of the deployed artifact
   */
  artifact_name: string;
  /**
   * Type of artifact (skill, command, agent, mcp, hook)
   */
  artifact_type: string;
  /**
   * Source collection name
   */
  from_collection: string;
  /**
   * Deployment timestamp
   */
  deployed_at: string;
  /**
   * Relative path within .claude/ directory
   */
  artifact_path: string;
  /**
   * Artifact version at deployment time
   */
  version?: string | null;
  /**
   * Content hash at deployment time
   */
  collection_sha: string;
  /**
   * Whether local modifications detected
   */
  local_modifications?: boolean;
  /**
   * Collections this artifact belongs to (many-to-many relationship)
   */
  collections?: Array<ArtifactCollectionInfo>;
};
