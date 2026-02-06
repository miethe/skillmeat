/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for linked artifact reference.
 *
 * Represents a relationship between two artifacts, such as skills
 * required by agents or agents enabled by skills.
 */
export type LinkedArtifactReferenceSchema = {
  /**
   * ID of target artifact (None if external/unresolved)
   */
  artifact_id?: string | null;
  /**
   * Display name of target artifact
   */
  artifact_name: string;
  /**
   * Type of target artifact (skill, agent, command, etc.)
   */
  artifact_type: string;
  /**
   * Source where target was found (GitHub repo, etc.)
   */
  source_name?: string | null;
  /**
   * Type of relationship: requires, enables, or related
   */
  link_type?: string;
  /**
   * When link was created
   */
  created_at?: string | null;
};
