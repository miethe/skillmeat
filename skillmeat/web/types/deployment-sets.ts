/**
 * TypeScript type definitions for Deployment Sets
 *
 * Mirrors the backend Pydantic schemas in:
 *   skillmeat/api/schemas/deployment_sets.py
 *
 * Deployment sets are named, ordered collections of artifacts, groups,
 * and/or nested sets that can be batch-deployed to a project in one operation.
 */

// =============================================================================
// Enums
// =============================================================================

/** Type of member in a deployment set */
export type DeploymentSetMemberType = 'artifact' | 'group' | 'set';

/** Status of a single artifact in a batch deployment */
export type DeployResultStatus = 'success' | 'failed' | 'skipped';

// =============================================================================
// Deployment Set (Core)
// =============================================================================

/** A named, ordered deployment set (response) */
export interface DeploymentSet {
  /** Deployment set unique identifier (UUID hex) */
  id: string;
  /** Human-readable deployment set name */
  name: string;
  /** Optional description of the deployment set */
  description: string | null;
  /** Optional icon identifier or emoji */
  icon: string | null;
  /** Optional color hex code or name */
  color: string | null;
  /** Tag names associated with this set */
  tags: string[];
  /** Owner identifier (user ID or collection ID) */
  owner_id: string | null;
  /** Number of members in this deployment set */
  member_count: number;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at: string;
}

/** Request to create a new deployment set */
export interface DeploymentSetCreate {
  /** Deployment set name */
  name: string;
  /** Optional description */
  description?: string | null;
  /** Optional icon identifier or emoji */
  icon?: string | null;
  /** Optional color hex code or name */
  color?: string | null;
  /** Optional list of tag names */
  tags?: string[] | null;
}

/** Request to partially update a deployment set (all fields optional) */
export interface DeploymentSetUpdate {
  /** Updated deployment set name */
  name?: string | null;
  /** Updated description */
  description?: string | null;
  /** Updated icon identifier or emoji */
  icon?: string | null;
  /** Updated color hex code or name */
  color?: string | null;
  /** Updated list of tag names (replaces existing tags) */
  tags?: string[] | null;
}

/** Paginated list of deployment sets */
export interface DeploymentSetListResponse {
  /** List of deployment sets */
  items: DeploymentSet[];
  /** Total number of deployment sets (before pagination) */
  total: number;
}

// =============================================================================
// Members
// =============================================================================

/** A single member within a deployment set (response) */
export interface DeploymentSetMember {
  /** Member unique identifier (UUID hex) */
  id: string;
  /** ID of the parent deployment set */
  deployment_set_id: string;
  /** UUID of the artifact member (if member_type is 'artifact') */
  artifact_uuid: string | null;
  /** ID of the group member (if member_type is 'group') */
  group_id: string | null;
  /** ID of the nested deployment set (if member_type is 'set') */
  nested_set_id: string | null;
  /** Type of member: 'artifact', 'group', or 'set' */
  member_type: DeploymentSetMemberType;
  /** Ordering position within the set */
  position: number | null;
  /** Timestamp when this member was added (ISO 8601) */
  added_at: string;
}

/**
 * Request to add a member to a deployment set.
 * Exactly one of artifact_uuid, group_id, or nested_set_id must be provided.
 */
export interface DeploymentSetMemberCreate {
  /** UUID of the artifact to add as a member */
  artifact_uuid?: string | null;
  /** ID of the group to add as a member */
  group_id?: string | null;
  /** ID of the nested deployment set to add as a member (UUID hex) */
  nested_set_id?: string | null;
  /** Optional ordering position within the set */
  position?: number | null;
}

/** Request to update a member's position within a deployment set */
export interface MemberUpdatePosition {
  /** New ordering position for this member */
  position: number;
}

// =============================================================================
// Resolution
// =============================================================================

/** A single artifact resolved from a deployment set traversal */
export interface ResolvedArtifact {
  /** UUID of the resolved artifact */
  artifact_uuid: string;
  /** Human-readable artifact name */
  artifact_name: string | null;
  /** Artifact type (e.g., 'skill', 'command', 'agent') */
  artifact_type: string | null;
  /**
   * Resolution trace: ordered list of set/group names traversed
   * to reach this artifact.
   */
  source_path: string[];
}

/** Response for deployment set artifact resolution */
export interface DeploymentSetResolution {
  /** ID of the resolved deployment set */
  set_id: string;
  /** Name of the resolved deployment set */
  set_name: string;
  /** All artifacts reachable from this deployment set */
  resolved_artifacts: ResolvedArtifact[];
  /** Total number of unique resolved artifacts */
  total_count: number;
}

// =============================================================================
// Batch Deploy
// =============================================================================

/** Request to batch deploy all artifacts in a deployment set */
export interface BatchDeployRequest {
  /** Absolute path to the target project directory */
  project_path: string;
  /** If true, simulate deployment without writing files */
  dry_run?: boolean;
}

/** Result for a single artifact in a batch deployment */
export interface BatchDeployResult {
  /** UUID of the artifact that was deployed (or attempted) */
  artifact_uuid: string;
  /** Human-readable artifact name */
  artifact_name: string | null;
  /** Deployment status */
  status: DeployResultStatus;
  /** Error message if status is 'failed' */
  error: string | null;
}

/** Response from a batch deployment operation */
export interface BatchDeployResponse {
  /** ID of the deployment set that was deployed */
  set_id: string;
  /** Name of the deployment set */
  set_name: string;
  /** Target project path */
  project_path: string;
  /** Total number of artifacts attempted */
  total: number;
  /** Number of artifacts successfully deployed */
  succeeded: number;
  /** Number of artifacts that failed to deploy */
  failed: number;
  /** Number of artifacts skipped (e.g., already up-to-date) */
  skipped: number;
  /** Per-artifact deployment results */
  results: BatchDeployResult[];
  /** Whether this was a dry run (no files written) */
  dry_run: boolean;
}

// =============================================================================
// Query Params
// =============================================================================

/** Query parameters for listing deployment sets */
export interface DeploymentSetListParams {
  /** Filter by name substring */
  name?: string;
  /** Filter by tag */
  tag?: string;
  /** Page size (1–200, default 50) */
  limit?: number;
  /** Pagination offset (default 0) */
  offset?: number;
}
