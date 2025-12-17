/**
 * Version snapshot type definitions for collection versioning
 */

/** Represents a single version snapshot */
export interface Snapshot {
  /** SHA-256 hash identifier */
  id: string;
  /** Snapshot creation timestamp (ISO 8601) */
  timestamp: string;
  /** Snapshot description/message */
  message: string;
  /** Collection name */
  collectionName: string;
  /** Number of artifacts in snapshot */
  artifactCount: number;
}

/** Request to create a new snapshot */
export interface CreateSnapshotRequest {
  /** Optional collection name (defaults to current) */
  collectionName?: string;
  /** Snapshot description */
  message?: string;
}

/** Response when creating a snapshot */
export interface CreateSnapshotResponse {
  /** Created snapshot */
  snapshot: Snapshot;
  /** Whether snapshot was newly created */
  created: boolean;
}

/** Paginated snapshot list response */
export interface SnapshotListResponse {
  /** List of snapshots */
  items: Snapshot[];
  /** Pagination info */
  pageInfo: {
    /** Total number of items */
    total: number;
    /** Current page number */
    page: number;
    /** Number of items per page */
    pageSize: number;
    /** Cursor for next page */
    nextCursor?: string;
  };
}

/** Conflict metadata for rollback operation */
export interface ConflictMetadata {
  /** Path to file with conflict */
  filePath: string;
  /** Type of conflict (content, deletion, add_add, both_modified) */
  conflictType: 'content' | 'deletion' | 'add_add' | 'both_modified';
  /** Whether conflict can be auto-merged */
  autoMergeable: boolean;
  /** Whether file is binary */
  isBinary: boolean;
}

/** Rollback safety analysis response */
export interface RollbackSafetyAnalysis {
  /** Whether rollback is safe to execute */
  isSafe: boolean;
  /** Files that would have conflicts */
  filesWithConflicts: string[];
  /** Files that can be safely restored */
  filesSafeToRestore: string[];
  /** Warning messages */
  warnings: string[];
}

/** Request to execute a rollback */
export interface RollbackRequest {
  /** Snapshot ID to rollback to */
  snapshotId: string;
  /** Optional collection name */
  collectionName?: string;
  /** Whether to preserve uncommitted changes (3-way merge) */
  preserveChanges?: boolean;
  /** Optional list of specific files to rollback */
  selectivePaths?: string[];
}

/** Rollback operation response */
export interface RollbackResponse {
  /** Whether rollback succeeded */
  success: boolean;
  /** Files that were merged */
  filesMerged: string[];
  /** Files that were restored */
  filesRestored: string[];
  /** Conflicts encountered */
  conflicts: ConflictMetadata[];
  /** Safety snapshot ID (created before rollback) */
  safetySnapshotId?: string;
}

/** Request to diff two snapshots */
export interface DiffSnapshotsRequest {
  /** First snapshot ID */
  snapshotId1: string;
  /** Second snapshot ID */
  snapshotId2: string;
  /** Optional collection name */
  collectionName?: string;
}

/** Snapshot diff response */
export interface SnapshotDiff {
  /** Files added between snapshots */
  filesAdded: string[];
  /** Files removed between snapshots */
  filesRemoved: string[];
  /** Files modified between snapshots */
  filesModified: string[];
  /** Total lines added */
  totalLinesAdded: number;
  /** Total lines removed */
  totalLinesRemoved: number;
}
