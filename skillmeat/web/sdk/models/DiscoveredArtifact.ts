/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CollectionMatch } from './CollectionMatch';
/**
 * An artifact discovered during scanning.
 */
export type DiscoveredArtifact = {
  /**
   * Artifact type: skill, command, agent, hook, mcp
   */
  type: string;
  /**
   * Artifact name
   */
  name: string;
  /**
   * GitHub source if known
   */
  source?: string | null;
  /**
   * Version if known
   */
  version?: string | null;
  /**
   * Scope: user or local
   */
  scope?: string | null;
  /**
   * Tags
   */
  tags?: Array<string> | null;
  /**
   * Description
   */
  description?: string | null;
  /**
   * Full path to artifact directory
   */
  path: string;
  /**
   * When artifact was discovered
   */
  discovered_at: string;
  /**
   * SHA256 content hash of the artifact for deduplication
   */
  content_hash?: string | null;
  /**
   * Hash-based collection matching result. Populated when collection context is provided during discovery. Shows if artifact content matches an existing collection artifact.
   */
  collection_match?: CollectionMatch | null;
};
