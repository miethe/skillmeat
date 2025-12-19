/**
 * Sync Operation Types for SkillMeat Sync UI
 *
 * Represents sync operations between collection and deployed project artifacts,
 * including change attribution and conflict detection.
 */

import type { ChangeOrigin } from './drift';

/**
 * File-level diff information for sync preview
 */
export interface FileDiff {
  /** File path relative to artifact root */
  path: string;
  /** Unified diff format output */
  diff: string;
  /** Origin of the change (optional for backwards compatibility) */
  change_origin?: ChangeOrigin;
  /** Baseline hash at deployment time (merge base) */
  baseline_hash?: string;
  /** Hash of currently deployed file */
  deployed_hash?: string;
  /** Hash of upstream (collection) file */
  upstream_hash?: string;
}

/**
 * Summary of changes in a sync preview
 */
export interface SyncPreviewSummary {
  /** Number of files with upstream changes only */
  upstream_changes: number;
  /** Number of files with local changes only */
  local_changes: number;
  /** Number of files with conflicts (both upstream and local changes) */
  conflicts: number;
}

/**
 * Preview of sync operation showing changes before execution
 */
export interface SyncPreview {
  /** Name of the artifact being synced */
  artifact_name: string;
  /** Type of artifact (skill, command, agent, etc.) */
  artifact_type: string;
  /** List of file diffs */
  files: FileDiff[];
  /** Whether any conflicts exist */
  has_conflicts: boolean;
  /** Summary of changes */
  summary: SyncPreviewSummary;
}

/**
 * Result of a sync operation
 */
export interface SyncResult {
  /** Whether the sync was successful */
  success: boolean;
  /** Name of the artifact that was synced */
  artifact_name: string;
  /** List of files that were successfully merged */
  merged_files: string[];
  /** List of files with unresolved conflicts (optional) */
  conflicts?: string[];
  /** Error message if sync failed (optional) */
  error?: string;
}
