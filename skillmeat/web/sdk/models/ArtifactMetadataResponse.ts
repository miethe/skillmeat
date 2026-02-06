/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LinkedArtifactReferenceSchema } from './LinkedArtifactReferenceSchema';
/**
 * Artifact metadata from SKILL.md / COMMAND.md / AGENT.md.
 */
export type ArtifactMetadataResponse = {
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
   * Artifact version from metadata
   */
  version?: string | null;
  /**
   * Required dependencies
   */
  dependencies?: Array<string>;
  /**
   * Claude Code tools used by this artifact
   */
  tools?: Array<string>;
  /**
   * Artifacts this artifact links to (requires, enables, or related)
   */
  linked_artifacts?: Array<LinkedArtifactReferenceSchema>;
  /**
   * References that could not be auto-matched to artifacts in the collection
   */
  unlinked_references?: Array<string>;
};
