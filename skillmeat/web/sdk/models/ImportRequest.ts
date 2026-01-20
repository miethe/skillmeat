/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to import artifacts from catalog to collection.
 *
 * Specifies which entries to import and how to handle conflicts.
 */
export type ImportRequest = {
  /**
   * List of catalog entry IDs to import
   */
  entry_ids: Array<string>;
  /**
   * Strategy for handling conflicts with existing artifacts
   */
  conflict_strategy?: 'skip' | 'overwrite' | 'rename';
};
