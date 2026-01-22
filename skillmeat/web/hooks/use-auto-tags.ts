/**
 * Custom hooks for source auto-tag management using TanStack Query
 *
 * Provides hooks for fetching and updating auto-tags (GitHub repository topics)
 * for marketplace sources.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSourceAutoTags, updateSourceAutoTag } from '@/lib/api/marketplace';
import type {
  AutoTagsResponse,
  UpdateAutoTagRequest,
  UpdateAutoTagResponse,
} from '@/types/marketplace';

/**
 * Query keys factory for auto-tag queries
 * Structured hierarchically for efficient cache invalidation
 */
export const autoTagsKeys = {
  all: ['auto-tags'] as const,
  source: (sourceId: string) => [...autoTagsKeys.all, sourceId] as const,
};

/**
 * Fetch auto-tag suggestions for a marketplace source
 *
 * @param sourceId - Marketplace source ID
 * @returns Query result with auto-tag segments and pending status
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useSourceAutoTags(sourceId);
 * if (data?.has_pending) {
 *   console.log(`${data.segments.length} auto-tags available`);
 * }
 * ```
 */
export function useSourceAutoTags(sourceId: string) {
  return useQuery<AutoTagsResponse>({
    queryKey: autoTagsKeys.source(sourceId),
    queryFn: () => getSourceAutoTags(sourceId),
    enabled: !!sourceId,
    staleTime: 5 * 60 * 1000, // 5 minutes - topics don't change often
  });
}

/**
 * Update the status of a source auto-tag (approve or reject)
 *
 * Automatically invalidates the auto-tags cache and source query on success
 *
 * @param sourceId - Marketplace source ID
 * @returns Mutation function for updating auto-tag status
 *
 * @example
 * ```tsx
 * const updateAutoTag = useUpdateAutoTag(sourceId);
 *
 * // Approve an auto-tag
 * await updateAutoTag.mutateAsync({
 *   value: 'claude-code',
 *   status: 'approved',
 * });
 *
 * // Reject an auto-tag
 * await updateAutoTag.mutateAsync({
 *   value: 'test',
 *   status: 'rejected',
 * });
 * ```
 */
export function useUpdateAutoTag(sourceId: string) {
  const queryClient = useQueryClient();

  return useMutation<UpdateAutoTagResponse, Error, UpdateAutoTagRequest>({
    mutationFn: (request) => updateSourceAutoTag(sourceId, request),
    onSuccess: () => {
      // Invalidate auto-tags query to refresh the list
      queryClient.invalidateQueries({ queryKey: autoTagsKeys.source(sourceId) });
      // Also invalidate the source query since tags may have been added
      queryClient.invalidateQueries({ queryKey: ['sources', sourceId] });
    },
  });
}
