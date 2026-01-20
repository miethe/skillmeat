/**
 * React hooks for context entity synchronization
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSyncStatus,
  pullChanges,
  pushChanges,
  resolveConflict,
  type SyncStatus,
  type SyncResolution,
} from '@/lib/api/context-sync';

/**
 * Hook to fetch context sync status for a project
 */
export function useContextSyncStatus(projectPath: string | undefined, enabled: boolean = true) {
  return useQuery<SyncStatus>({
    queryKey: ['context-sync-status', projectPath],
    queryFn: () => {
      if (!projectPath) throw new Error('Project path is required');
      return getSyncStatus(projectPath);
    },
    enabled: enabled && !!projectPath,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Auto-refresh every 60 seconds
  });
}

/**
 * Hook to get count of pending context changes for an entity
 */
export function usePendingContextChanges(
  entityId: string | undefined,
  projectPath: string | undefined
): number {
  const { data: syncStatus } = useContextSyncStatus(projectPath, !!entityId && !!projectPath);

  if (!syncStatus || !entityId) return 0;

  const hasProjectChanges = syncStatus.modified_in_project.includes(entityId);
  const hasCollectionChanges = syncStatus.modified_in_collection.includes(entityId);
  const hasConflict = syncStatus.conflicts.some((c) => c.entity_id === entityId);

  return (hasProjectChanges ? 1 : 0) + (hasCollectionChanges ? 1 : 0) + (hasConflict ? 1 : 0);
}

/**
 * Hook to pull changes from project to collection
 */
export function usePullContextChanges() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectPath, entityIds }: { projectPath: string; entityIds?: string[] }) =>
      pullChanges(projectPath, entityIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['context-sync-status', variables.projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
      queryClient.invalidateQueries({ queryKey: ['context-entities'] });
    },
  });
}

/**
 * Hook to push changes from collection to project
 */
export function usePushContextChanges() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectPath,
      entityIds,
      overwrite = false,
    }: {
      projectPath: string;
      entityIds?: string[];
      overwrite?: boolean;
    }) => pushChanges(projectPath, entityIds, overwrite),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['context-sync-status', variables.projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
    },
  });
}

/**
 * Hook to resolve context sync conflict
 */
export function useResolveContextConflict() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectPath,
      entityId,
      resolution,
      mergedContent,
    }: {
      projectPath: string;
      entityId: string;
      resolution: SyncResolution;
      mergedContent?: string;
    }) => resolveConflict(projectPath, entityId, resolution, mergedContent),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['context-sync-status', variables.projectPath] });
      queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
      queryClient.invalidateQueries({ queryKey: ['context-entities'] });
    },
  });
}
