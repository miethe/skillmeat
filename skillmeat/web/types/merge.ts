/**
 * Merge and conflict resolution types
 * Maps to backend schemas from skillmeat/api/schemas/merge.py
 */

export interface ConflictMetadata {
  filePath: string;
  conflictType: 'content' | 'deletion' | 'add_add' | 'both_modified';
  autoMergeable: boolean;
  isBinary: boolean;
}

export interface MergeAnalyzeRequest {
  baseSnapshotId: string;
  localCollection: string;
  remoteSnapshotId: string;
  remoteCollection?: string;
}

export interface MergeSafetyResponse {
  canAutoMerge: boolean;
  autoMergeableCount: number;
  conflictCount: number;
  conflicts: ConflictMetadata[];
  warnings: string[];
}

export interface MergePreviewResponse {
  filesAdded: string[];
  filesRemoved: string[];
  filesChanged: string[];
  potentialConflicts: ConflictMetadata[];
  canAutoMerge: boolean;
}

export interface MergeExecuteRequest {
  baseSnapshotId: string;
  localCollection: string;
  remoteSnapshotId: string;
  remoteCollection?: string;
  autoSnapshot?: boolean;
}

export interface MergeExecuteResponse {
  success: boolean;
  filesMerged: string[];
  conflicts: ConflictMetadata[];
  preMergeSnapshotId?: string;
  error?: string;
}

export interface ConflictResolveRequest {
  filePath: string;
  resolution: 'use_local' | 'use_remote' | 'use_base' | 'custom';
  customContent?: string;
}

export interface ConflictResolveResponse {
  success: boolean;
  filePath: string;
  resolutionApplied: string;
}

export type MergeStrategy = 'auto' | 'manual' | 'abort_on_conflict';

export interface MergeWorkflowState {
  step: 'analyze' | 'preview' | 'resolve' | 'confirm' | 'execute' | 'complete';
  analysis?: MergeSafetyResponse;
  preview?: MergePreviewResponse;
  unresolvedConflicts: ConflictMetadata[];
  resolvedConflicts: Map<string, ConflictResolveRequest>;
  strategy: MergeStrategy;
}
