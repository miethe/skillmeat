/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for syncing an artifact.
 *
 * If project_path is provided: Syncs FROM project TO collection (reverse sync).
 * If project_path is omitted: Syncs FROM upstream source TO collection (update).
 */
export type ArtifactSyncRequest = {
  /**
   * Path to project directory containing deployed artifact. If omitted, syncs from upstream source.
   */
  project_path?: string | null;
  /**
   * Force sync even if conflicts are detected
   */
  force?: boolean;
  /**
   * Conflict resolution strategy: 'theirs' (take upstream), 'ours' (keep local), 'manual' (preserve conflicts)
   */
  strategy?: string;
};
