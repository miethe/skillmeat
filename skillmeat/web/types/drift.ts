/**
 * Drift Detection and Change Origin Types for SkillMeat
 *
 * These types represent change origins when comparing artifact versions
 * across upstream sources and local deployments.
 */

/**
 * Origin of a detected change
 * - upstream: Changes only in upstream source (maps to backend 'sync' or 'deployment')
 * - local: Local modifications only (maps to backend 'local_modification')
 * - both: Changes in both (requires conflict resolution)
 * - none: No changes detected
 */
export type ChangeOrigin = 'upstream' | 'local' | 'both' | 'none';

/**
 * File-level drift information
 */
export interface DriftFile {
  /** File path relative to project/artifact root */
  path: string;
  /** Type of change detected */
  status: 'added' | 'modified' | 'deleted';
  /** Origin of the change (optional for backwards compatibility) */
  change_origin?: ChangeOrigin;
}

/**
 * Drift detection result for a single artifact
 */
export interface ArtifactDrift {
  artifact_name: string;
  artifact_type: string;
  location: string;
  change_origin: ChangeOrigin;
  upstream_sha: string | null;
  local_sha: string;
  requires_merge: boolean;
  detected_at: string; // ISO 8601
  metadata: Record<string, any>;
}

/**
 * Summary of drift detection across multiple artifacts
 */
export interface DriftSummary {
  /** Total number of files with drift */
  total_files: number;
  /** Number of files with upstream changes only */
  upstream_changes: number;
  /** Number of files with local changes only */
  local_changes: number;
  /** Number of files with conflicts (both upstream and local changes) */
  conflicts: number;
  /** Number of files with no changes */
  no_changes: number;
}

/**
 * Full drift detection result for an artifact
 */
export interface DriftDetection {
  /** Whether any drift was detected */
  has_drift: boolean;
  /** List of files with drift */
  files: DriftFile[];
  /** Summary statistics (optional) */
  summary?: DriftSummary;
  /** Baseline hash at deployment time (merge base) */
  baseline_hash?: string;
  /** Current hash in project */
  current_hash?: string;
  /** Timestamp when modification was first detected (ISO 8601) */
  modification_detected_at?: string;
}
