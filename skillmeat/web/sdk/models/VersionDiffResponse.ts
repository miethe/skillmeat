/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Diff result between two snapshots.
 *
 * Provides statistical comparison of changes between two
 * collection snapshots.
 */
export type VersionDiffResponse = {
  /**
   * Files added between snapshots
   */
  files_added?: Array<string>;
  /**
   * Files removed between snapshots
   */
  files_removed?: Array<string>;
  /**
   * Files modified between snapshots
   */
  files_modified?: Array<string>;
  /**
   * Total number of lines added across all files
   */
  total_lines_added: number;
  /**
   * Total number of lines removed across all files
   */
  total_lines_removed: number;
};
