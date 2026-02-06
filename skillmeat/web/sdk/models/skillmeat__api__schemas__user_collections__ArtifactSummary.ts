/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactCollectionInfo } from './ArtifactCollectionInfo';
import type { ArtifactGroupMembership } from './ArtifactGroupMembership';
import type { DeploymentSummary } from './DeploymentSummary';
/**
 * Lightweight artifact summary for collection listings.
 *
 * When include_groups=true query parameter is used, the groups field
 * will be populated with group membership information.
 *
 * This schema includes metadata fields (description, author, tags, collections)
 * to support the frontend entity-mapper which expects these fields for
 * consistent Entity rendering including collection badges.
 */
export type skillmeat__api__schemas__user_collections__ArtifactSummary = {
  /**
   * Unique artifact identifier
   */
  id: string;
  /**
   * Artifact name
   */
  name: string;
  /**
   * Artifact type (skill, command, agent, etc.)
   */
  type: string;
  /**
   * Current version
   */
  version?: string | null;
  /**
   * Source specification
   */
  source: string;
  /**
   * Artifact description from metadata
   */
  description?: string | null;
  /**
   * Artifact author from metadata
   */
  author?: string | null;
  /**
   * Artifact tags
   */
  tags?: Array<string> | null;
  /**
   * Claude Code tools used by this artifact
   */
  tools?: Array<string> | null;
  /**
   * Collections this artifact belongs to (for collection badges)
   */
  collections?: Array<ArtifactCollectionInfo> | null;
  /**
   * Groups this artifact belongs to (only populated when include_groups=true)
   */
  groups?: Array<ArtifactGroupMembership> | null;
  /**
   * Lightweight deployment summaries for this artifact
   */
  deployments?: Array<DeploymentSummary> | null;
};
