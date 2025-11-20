/**
 * Version Tracking Types for SkillMeat
 *
 * These types represent version tracking information for artifacts
 * across collections and projects.
 */

/**
 * Version information for a single artifact instance
 */
export interface ArtifactVersionInfo {
  artifact_name: string;
  artifact_type: string;
  location: string;
  location_type: "collection" | "project";
  content_sha: string;
  parent_sha: string | null;
  is_modified: boolean;
  created_at: string; // ISO 8601
  metadata: Record<string, any>;
}

/**
 * Node in version graph visualization (recursive type)
 */
export interface VersionGraphNode {
  id: string;
  artifact_name: string;
  artifact_type: string;
  version_info: ArtifactVersionInfo;
  children: VersionGraphNode[];
  metadata: Record<string, any>;
}

/**
 * Complete version graph for an artifact
 */
export interface VersionGraph {
  artifact_name: string;
  artifact_type: string;
  root: VersionGraphNode | null;
  statistics: {
    total_deployments: number;
    modified_count: number;
    unmodified_count: number;
    orphaned_count: number;
  };
  last_updated: string; // ISO 8601
}

/**
 * Response from modification check operation
 */
export interface ModificationCheckResult {
  project_id: string;
  checked_at: string; // ISO 8601
  modifications_detected: number;
  deployments: DeploymentModificationStatus[];
}

/**
 * Modification status for a single deployment
 */
export interface DeploymentModificationStatus {
  artifact_name: string;
  artifact_type: string;
  deployed_sha: string;
  current_sha: string;
  is_modified: boolean;
  modification_detected_at: string | null; // ISO 8601
}
