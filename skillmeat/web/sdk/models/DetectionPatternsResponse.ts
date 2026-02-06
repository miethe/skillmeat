/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for artifact detection patterns.
 *
 * This schema exposes the detection patterns used by the Python backend
 * for identifying artifact types from directory structures. Frontend
 * applications can use this data to replicate the same detection logic.
 *
 * Attributes:
 * container_aliases: Maps artifact type to list of valid container names.
 * e.g., {"skill": ["skills", "skill", "claude-skills"]}
 * leaf_containers: Flattened unique list of all valid container names.
 * Useful for quick membership checks when traversing directories.
 * canonical_containers: Maps artifact type to its preferred container name.
 * e.g., {"skill": "skills"}
 */
export type DetectionPatternsResponse = {
  /**
   * Maps artifact type to list of valid container directory names
   */
  container_aliases: Record<string, Array<string>>;
  /**
   * Flattened unique list of all valid container names across all types
   */
  leaf_containers: Array<string>;
  /**
   * Maps artifact type to its canonical (preferred) container name
   */
  canonical_containers: Record<string, string>;
};
