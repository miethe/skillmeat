/**
 * Custom hooks for path tag management using TanStack Query
 *
 * Provides hooks for fetching and updating path-based tag segments
 * for marketplace catalog entries.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPathTags, updatePathTagStatus } from '@/lib/api/marketplace';
import type { PathSegmentsResponse } from '@/types/path-tags';

/**
 * Query keys factory for path tag queries
 * Structured hierarchically for efficient cache invalidation
 */
export const pathTagKeys = {
  all: ['path-tags'] as const,
  details: () => [...pathTagKeys.all, 'detail'] as const,
  detail: (sourceId: string, entryId: string) =>
    [...pathTagKeys.details(), sourceId, entryId] as const,
};

/**
 * Fetch path tag segments for a marketplace catalog entry
 *
 * @param sourceId - Marketplace source ID
 * @param entryId - Catalog entry ID
 * @returns Query result with extracted path segments
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = usePathTags(sourceId, entryId);
 * if (data) {
 *   data.extracted.forEach(segment => {
 *     console.log(`${segment.segment} (${segment.status})`);
 *   });
 * }
 * ```
 */
export function usePathTags(sourceId: string, entryId: string) {
  return useQuery({
    queryKey: pathTagKeys.detail(sourceId, entryId),
    queryFn: async (): Promise<PathSegmentsResponse> => {
      return getPathTags(sourceId, entryId);
    },
    enabled: !!sourceId && !!entryId,
    staleTime: 5 * 60 * 1000, // 5 minutes - segments don't change often
  });
}

/**
 * Update the status of a path tag segment (approve or reject)
 *
 * Automatically invalidates the path tags cache for the entry on success
 *
 * @returns Mutation function for updating segment status
 *
 * @example
 * ```tsx
 * const updateStatus = useUpdatePathTagStatus();
 *
 * // Approve a segment
 * await updateStatus.mutateAsync({
 *   sourceId: 'source-123',
 *   entryId: 'entry-456',
 *   segment: 'canvas',
 *   status: 'approved',
 * });
 *
 * // Reject a segment
 * await updateStatus.mutateAsync({
 *   sourceId: 'source-123',
 *   entryId: 'entry-456',
 *   segment: 'test',
 *   status: 'rejected',
 * });
 * ```
 */
export function useUpdatePathTagStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sourceId,
      entryId,
      segment,
      status,
    }: {
      sourceId: string;
      entryId: string;
      segment: string;
      status: 'approved' | 'rejected';
    }): Promise<PathSegmentsResponse> => {
      return updatePathTagStatus(sourceId, entryId, segment, status);
    },
    onSuccess: (_, { sourceId, entryId }) => {
      // Invalidate the path tags cache for this entry to reflect updated status
      queryClient.invalidateQueries({
        queryKey: pathTagKeys.detail(sourceId, entryId),
      });
    },
  });
}
