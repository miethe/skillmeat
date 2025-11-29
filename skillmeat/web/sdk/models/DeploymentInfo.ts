/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Information about a single deployment.
 */
export type DeploymentInfo = {
  /**
   * Artifact name
   */
  artifact_name: string;
  /**
   * Artifact type
   */
  artifact_type: string;
  /**
   * Source collection name
   */
  from_collection: string;
  /**
   * Deployment timestamp
   */
  deployed_at: string;
  /**
   * Relative path within .claude/
   */
  artifact_path: string;
  /**
   * SHA at deployment time
   */
  collection_sha: string;
  /**
   * Whether local modifications detected
   */
  local_modifications?: boolean;
  /**
   * Sync status: synced, modified, outdated
   */
  sync_status?: string | null;
};
