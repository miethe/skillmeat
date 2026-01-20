/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to compare two snapshots.
 *
 * Generates a diff showing changes between two collection snapshots.
 */
export type VersionDiffRequest = {
  /**
   * First snapshot ID (older)
   */
  snapshot_id_1: string;
  /**
   * Second snapshot ID (newer)
   */
  snapshot_id_2: string;
  /**
   * Collection name (uses active collection if not specified)
   */
  collection_name?: string | null;
};
