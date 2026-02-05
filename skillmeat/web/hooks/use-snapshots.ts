/**
 * Custom hooks for version snapshot management using TanStack Query
 *
 * Provides data fetching, caching, and state management for snapshots.
 * Uses live API data with proper error handling and cache invalidation.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchSnapshots,
  fetchSnapshot,
  createSnapshot,
  deleteSnapshot,
  analyzeRollbackSafety,
  executeRollback,
  diffSnapshots,
} from '@/lib/api/snapshots';
import type {
  Snapshot,
  SnapshotListResponse,
  CreateSnapshotRequest,
  CreateSnapshotResponse,
  RollbackSafetyAnalysis,
  RollbackRequest,
  RollbackResponse,
  DiffSnapshotsRequest,
  SnapshotDiff,
} from '@/types/snapshot';

/**
 * Filter options for snapshot queries
 */
export interface SnapshotFilters {
  /** Collection name filter */
  collectionName?: string;
  /** Maximum number of items to return */
  limit?: number;
  /** Cursor for pagination */
  after?: string;
}

/**
 * Query keys factory for type-safe cache management
 */
export const snapshotKeys = {
  all: ['snapshots'] as const,
  lists: () => [...snapshotKeys.all, 'list'] as const,
  list: (filters?: SnapshotFilters) => [...snapshotKeys.lists(), filters] as const,
  details: () => [...snapshotKeys.all, 'detail'] as const,
  detail: (id: string, collectionName?: string) =>
    [...snapshotKeys.details(), id, collectionName] as const,
  rollbackAnalysis: (id: string, collectionName?: string) =>
    [...snapshotKeys.detail(id, collectionName), 'rollback-analysis'] as const,
};

/**
 * Fetch paginated list of snapshots with optional filtering
 *
 * @param filters - Optional filters for collection name and pagination
 * @returns Query result with snapshot list
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useSnapshots({ collectionName: 'default', limit: 20 });
 * if (data) {
 *   console.log(`Found ${data.pageInfo.total} snapshots`);
 * }
 * ```
 */
export function useSnapshots(filters?: SnapshotFilters) {
  return useQuery({
    queryKey: snapshotKeys.list(filters),
    queryFn: async (): Promise<SnapshotListResponse> => {
      return fetchSnapshots(filters);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch single snapshot by ID
 *
 * @param id - Snapshot SHA-256 hash identifier
 * @param collectionName - Optional collection name
 * @returns Query result with snapshot details
 *
 * @example
 * ```tsx
 * const { data: snapshot } = useSnapshot(snapshotId, 'default');
 * if (snapshot) {
 *   console.log(`Snapshot has ${snapshot.artifactCount} artifacts`);
 * }
 * ```
 */
export function useSnapshot(id: string, collectionName?: string) {
  return useQuery({
    queryKey: snapshotKeys.detail(id, collectionName),
    queryFn: async (): Promise<Snapshot> => {
      return fetchSnapshot(id, collectionName);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Analyze rollback safety for a snapshot
 *
 * Checks for conflicts and provides warnings before rollback execution.
 *
 * @param snapshotId - Snapshot SHA-256 hash identifier
 * @param collectionName - Optional collection name
 * @returns Query result with safety analysis
 *
 * @example
 * ```tsx
 * const { data: analysis } = useRollbackAnalysis(snapshotId, 'default');
 * if (analysis && !analysis.isSafe) {
 *   console.warn('Conflicts detected:', analysis.filesWithConflicts);
 * }
 * ```
 */
export function useRollbackAnalysis(snapshotId: string, collectionName?: string) {
  return useQuery({
    queryKey: snapshotKeys.rollbackAnalysis(snapshotId, collectionName),
    queryFn: async (): Promise<RollbackSafetyAnalysis> => {
      return analyzeRollbackSafety(snapshotId, collectionName);
    },
    enabled: !!snapshotId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Create new version snapshot mutation
 *
 * Captures current collection state as a new snapshot.
 *
 * @returns Mutation function for creating snapshots
 *
 * @example
 * ```tsx
 * const createSnapshotMutation = useCreateSnapshot();
 * await createSnapshotMutation.mutateAsync({
 *   collectionName: 'default',
 *   message: 'Before major update'
 * });
 * ```
 */
export function useCreateSnapshot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateSnapshotRequest): Promise<CreateSnapshotResponse> => {
      return createSnapshot(data);
    },
    onSuccess: () => {
      // Invalidate snapshot lists to trigger refetch
      queryClient.invalidateQueries({ queryKey: snapshotKeys.lists() });
    },
  });
}

/**
 * Delete snapshot mutation
 *
 * Permanently removes a snapshot from history.
 *
 * @returns Mutation function for deleting snapshots
 *
 * @example
 * ```tsx
 * const deleteSnapshotMutation = useDeleteSnapshot();
 * await deleteSnapshotMutation.mutateAsync({
 *   id: snapshotId,
 *   collectionName: 'default'
 * });
 * ```
 */
export function useDeleteSnapshot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      collectionName,
    }: {
      id: string;
      collectionName?: string;
    }): Promise<void> => {
      return deleteSnapshot(id, collectionName);
    },
    onSuccess: (_, { id, collectionName }) => {
      // Invalidate both the specific snapshot and the list
      queryClient.invalidateQueries({ queryKey: snapshotKeys.detail(id, collectionName) });
      queryClient.invalidateQueries({ queryKey: snapshotKeys.lists() });
    },
  });
}

/**
 * Execute rollback to snapshot mutation
 *
 * Restores collection state to a previous snapshot, with optional
 * preservation of uncommitted changes via 3-way merge.
 *
 * @returns Mutation function for executing rollback
 *
 * @example
 * ```tsx
 * const rollbackMutation = useRollback();
 * await rollbackMutation.mutateAsync({
 *   snapshotId: targetSnapshotId,
 *   collectionName: 'default',
 *   preserveChanges: true,
 *   selectivePaths: ['skills/my-skill']
 * });
 * ```
 */
export function useRollback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RollbackRequest): Promise<RollbackResponse> => {
      return executeRollback(data.snapshotId, data);
    },
    onSuccess: () => {
      // Rollback changes everything - invalidate all snapshot and collection data
      queryClient.invalidateQueries({ queryKey: snapshotKeys.all });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] }); // Rollback changes deployed state
      queryClient.invalidateQueries({ queryKey: ['projects'] }); // Project deployment info may change
    },
  });
}

/**
 * Compare two snapshots mutation
 *
 * Generates diff showing changes between two snapshots.
 * Uses mutation since it's a POST with body, not a simple query.
 *
 * @returns Mutation function for diffing snapshots
 *
 * @example
 * ```tsx
 * const diffMutation = useDiffSnapshots();
 * const diff = await diffMutation.mutateAsync({
 *   snapshotId1: oldSnapshotId,
 *   snapshotId2: newSnapshotId,
 *   collectionName: 'default'
 * });
 * console.log(`${diff.filesAdded.length} files added, ${diff.filesRemoved.length} removed`);
 * ```
 */
export function useDiffSnapshots() {
  return useMutation({
    mutationFn: async (data: DiffSnapshotsRequest): Promise<SnapshotDiff> => {
      return diffSnapshots(data);
    },
    // No cache invalidation needed - diff is read-only operation
  });
}
