/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating artifact tags.
 *
 * Accepts a list of tag names which will be normalized and synced
 * with the artifact's tag associations. Tags that don't exist will
 * be created automatically.
 */
export type ArtifactTagsUpdate = {
  /**
   * List of tag names to assign to the artifact
   */
  tags: Array<string>;
};
