/**
 * Deployment type definitions for tracking artifact deployments
 *
 * Note: Types prefixed with "Artifact" to distinguish from MCP deployment types
 */

/** Artifact deployment status enum */
export type ArtifactDeploymentStatus =
  | 'active'
  | 'inactive'
  | 'error'
  | 'pending'
  | 'version_mismatch';

/** Artifact sync status enum */
export type ArtifactSyncStatus = 'synced' | 'modified' | 'outdated';

/** Request to deploy an artifact */
export interface ArtifactDeployRequest {
  /** Artifact identifier (format: 'type:name', e.g., 'skill:pdf') */
  artifact_id: string;
  /** Artifact name for display */
  artifact_name: string;
  /** Artifact type */
  artifact_type: string;
  /** Path to project directory (uses CWD if not specified) */
  project_path?: string;
  /** Source collection name (uses active collection if None) */
  collection_name?: string;
  /** Overwrite existing deployment without prompting */
  overwrite?: boolean;
  /**
   * Custom destination path relative to project root.
   * If provided, artifact will be deployed to {dest_path}/{artifact_name}/.
   * Must not contain '..' or be absolute.
   * Examples: '.claude/skills/', '.claude/skills/dev/'
   */
  dest_path?: string;
}

/** Request to undeploy (remove) an artifact from a project */
export interface ArtifactUndeployRequest {
  /** Artifact name */
  artifact_name: string;
  /** Artifact type */
  artifact_type: string;
  /** Path to project directory (uses CWD if not specified) */
  project_path?: string;
}

/** Response from an artifact deployment operation */
export interface ArtifactDeploymentResponse {
  /** Whether deployment succeeded */
  success: boolean;
  /** Status message */
  message: string;
  /** Deployment identifier (format: 'type:name') */
  deployment_id?: string;
  /** SSE stream URL for progress updates (if supported) */
  stream_url?: string;
  /** Deployed artifact name */
  artifact_name: string;
  /** Deployed artifact type */
  artifact_type: string;
  /** Target project path */
  project_path: string;
  /** Path where artifact was deployed */
  deployed_path: string;
  /** Timestamp of deployment (ISO 8601) */
  deployed_at?: string;
}

/** Response from an artifact undeploy operation */
export interface ArtifactUndeployResponse {
  /** Whether undeploy succeeded */
  success: boolean;
  /** Status message */
  message: string;
  /** Undeployed artifact name */
  artifact_name: string;
  /** Undeployed artifact type */
  artifact_type: string;
  /** Project path */
  project_path: string;
}

/** Request to remove a deployed artifact from a specific project */
export interface ProjectDeploymentRemovalRequest {
  /** Name of the artifact to remove */
  artifact_name: string;
  /** Type of the artifact to remove */
  artifact_type: string;
  /** Whether to remove files from filesystem (default: True) */
  remove_files?: boolean;
}

/** Response for removing a deployed artifact from a project */
export interface ProjectDeploymentRemovalResponse {
  /** Whether the removal was successful */
  success: boolean;
  /** Human-readable status message */
  message: string;
  /** Name of the removed artifact */
  artifact_name: string;
  /** Type of the removed artifact */
  artifact_type: string;
  /** Path to the project */
  project_path: string;
  /** Whether files were removed from filesystem */
  files_removed: boolean;
}

/** Information about a single artifact deployment */
export interface ArtifactDeploymentInfo {
  /** Artifact name */
  artifact_name: string;
  /** Artifact type */
  artifact_type: string;
  /** Source collection name */
  from_collection: string;
  /** Deployment timestamp (ISO 8601) */
  deployed_at: string;
  /** Relative path within .claude/ */
  artifact_path: string;
  /** Absolute path to the project directory */
  project_path: string;
  /** SHA at deployment time */
  collection_sha: string;
  /** Whether local modifications detected */
  local_modifications: boolean;
  /** Sync status: synced, modified, outdated */
  sync_status?: ArtifactSyncStatus;
}

/** List of artifact deployments in a project */
export interface ArtifactDeploymentListResponse {
  /** Project directory path */
  project_path: string;
  /** List of deployments */
  deployments: ArtifactDeploymentInfo[];
  /** Total number of deployments */
  total: number;
}
