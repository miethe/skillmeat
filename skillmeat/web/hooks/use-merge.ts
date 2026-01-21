/**
 * Merge and conflict resolution hooks
 */
'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { analyzeMergeSafety, previewMerge, executeMerge, resolveConflict } from '@/lib/api/merge';
import type {
  MergeAnalyzeRequest,
  MergeSafetyResponse,
  MergePreviewResponse,
  MergeExecuteRequest,
  MergeExecuteResponse,
  ConflictResolveRequest,
  ConflictResolveResponse,
} from '@/types/merge';

/**
 * Query key factory for merge operations
 */
export const mergeKeys = {
  all: ['merge'] as const,
  analysis: (baseId: string, remoteId: string) =>
    [...mergeKeys.all, 'analysis', baseId, remoteId] as const,
  preview: (baseId: string, remoteId: string) =>
    [...mergeKeys.all, 'preview', baseId, remoteId] as const,
};

/**
 * Hook to analyze merge safety
 */
export function useAnalyzeMerge() {
  return useMutation<MergeSafetyResponse, Error, MergeAnalyzeRequest>({
    mutationFn: analyzeMergeSafety,
  });
}

/**
 * Hook to preview merge changes
 */
export function usePreviewMerge() {
  return useMutation<MergePreviewResponse, Error, MergeAnalyzeRequest>({
    mutationFn: previewMerge,
  });
}

/**
 * Hook to execute merge
 * Invalidates snapshot queries on success
 */
export function useExecuteMerge() {
  const queryClient = useQueryClient();

  return useMutation<MergeExecuteResponse, Error, MergeExecuteRequest>({
    mutationFn: executeMerge,
    onSuccess: (_data, variables) => {
      // Invalidate snapshot queries since merge creates/modifies snapshots
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });

      // Invalidate the specific collection if we know it
      if (variables.localCollection) {
        queryClient.invalidateQueries({
          queryKey: ['collections', variables.localCollection],
        });
      }
    },
  });
}

/**
 * Hook to resolve a single conflict
 */
export function useResolveConflict() {
  return useMutation<ConflictResolveResponse, Error, ConflictResolveRequest>({
    mutationFn: resolveConflict,
  });
}
