/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from drift detection for a single artifact.
 *
 * Represents the drift status between a collection artifact and its
 * deployment in a project, including version lineage tracking for
 * three-way merge support.
 */
export type DriftDetectionResponse = {
  /**
   * Name of the artifact
   */
  artifact_name: string;
  /**
   * Type of artifact (skill, command, agent, etc.)
   */
  artifact_type: string;
  /**
   * Type of drift detected:
   * - modified: Artifact modified in project only (local changes)
   * - outdated: Artifact modified in collection only (upstream changes)
   * - conflict: Both project and collection modified (three-way conflict)
   * - added: Artifact added to collection (not in project)
   * - removed: Artifact removed from collection
   * - version_mismatch: Version changed but content may be same
   */
  drift_type: 'modified' | 'outdated' | 'conflict' | 'added' | 'removed' | 'version_mismatch';
  /**
   * SHA from collection (None if artifact removed from collection)
   */
  collection_sha?: string | null;
  /**
   * SHA from project (None if artifact added to collection)
   */
  project_sha?: string | null;
  /**
   * Version in collection (None if removed)
   */
  collection_version?: string | null;
  /**
   * Version in project (None if added)
   */
  project_version?: string | null;
  /**
   * ISO 8601 timestamp of last deployment (None if never deployed)
   */
  last_deployed?: string | null;
  /**
   * Recommended sync action
   */
  recommendation: string;
  /**
   * Origin of the change that caused drift:
   * - 'deployment': Change came from deploying a collection artifact
   * - 'sync': Change came from syncing with upstream
   * - 'local_modification': Change made directly in project
   * None if no change detected (drift_type='added')
   */
  change_origin?: string | null;
  /**
   * Hash at deployment time (merge base for three-way merge).
   * This is the deployed.sha from deployment metadata - represents
   * the common ancestor for merge operations.
   */
  baseline_hash?: string | null;
  /**
   * Current hash of the artifact in the project
   */
  current_hash?: string | null;
  /**
   * When modification was first detected (None if no drift)
   */
  modification_detected_at?: string | null;
};
