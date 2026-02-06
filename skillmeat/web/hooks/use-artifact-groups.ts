/**
 * Custom hook for fetching groups that contain a specific artifact
 *
 * Provides a TanStack Query hook to retrieve all groups within a collection
 * that contain a given artifact. Useful for displaying group membership
 * indicators in artifact cards and detail views.
 *
 * @module hooks/use-artifact-groups
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { apiRequest, apiConfig } from '@/lib/api';
import type { Group } from '@/types/groups';

const USE_MOCKS = apiConfig.useMocks;

/**
 * Query keys factory for artifact-to-group relationship queries
 *
 * Structured hierarchically for efficient cache invalidation:
 * - artifactGroupKeys.all: Base key for all artifact-group queries
 * - artifactGroupKeys.lists(): All list queries
 * - artifactGroupKeys.list(artifactId, collectionId): Specific artifact+collection pair
 *
 * Cache invalidation strategy:
 * - Invalidate artifactGroupKeys.all when any group membership changes
 * - Invalidate specific list when artifact is added/removed from groups
 */
export const artifactGroupKeys = {
  all: ['artifact-groups'] as const,
  lists: () => [...artifactGroupKeys.all, 'list'] as const,
  list: (artifactId?: string, collectionId?: string) =>
    [...artifactGroupKeys.lists(), { artifactId, collectionId }] as const,
};

// API response interface matching backend schema
interface ApiGroupListResponse {
  groups: Group[];
  total: number;
}

/**
 * Fetch groups that contain a specific artifact within a collection
 *
 * Uses the groups endpoint with artifact_id filter to retrieve only groups
 * where the artifact has been added. Results are sorted by position.
 *
 * @param artifactId - Artifact ID to find groups for (required for fetch)
 * @param collectionId - Collection ID to scope the search (required for fetch)
 * @returns Query result with array of Group objects sorted by position
 *
 * @remarks
 * - Query is disabled when either artifactId or collectionId is undefined
 * - Uses longer staleTime (10 minutes) since group membership changes infrequently
 * - Returns empty array on error (graceful degradation for UI display)
 *
 * @example
 * ```tsx
 * function ArtifactGroupBadges({ artifactId, collectionId }: Props) {
 *   const { data: groups, isLoading } = useArtifactGroups(artifactId, collectionId);
 *
 *   if (isLoading) return <Skeleton />;
 *
 *   return (
 *     <div className="flex gap-1">
 *       {groups?.map(group => (
 *         <Badge key={group.id} variant="secondary">
 *           {group.name}
 *         </Badge>
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 *
 * @example
 * ```tsx
 * // Conditional fetching - only fetch when modal is open
 * const { data: groups } = useArtifactGroups(
 *   isOpen ? artifactId : undefined,
 *   isOpen ? collectionId : undefined
 * );
 * ```
 */
export function useArtifactGroups(
  artifactId: string | undefined,
  collectionId: string | undefined
): UseQueryResult<Group[], Error> {
  return useQuery({
    queryKey: artifactGroupKeys.list(artifactId, collectionId),
    queryFn: async (): Promise<Group[]> => {
      if (!artifactId || !collectionId) {
        throw new Error('Both artifactId and collectionId are required');
      }

      try {
        const params = new URLSearchParams({
          collection_id: collectionId,
          artifact_id: artifactId,
        });
        const response = await apiRequest<ApiGroupListResponse>(`/groups?${params.toString()}`);

        // Sort by position to ensure consistent ordering
        // Backend may already sort, but defensive sorting ensures UI consistency
        const sortedGroups = [...response.groups].sort((a, b) => a.position - b.position);

        return sortedGroups;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(
            `[artifact-groups] API failed for artifact ${artifactId}, falling back to empty array`,
            error
          );
          return [];
        }
        // Graceful degradation: return empty array instead of throwing
        // This prevents UI crashes when group membership cannot be determined
        console.error(
          `[artifact-groups] Failed to fetch groups for artifact ${artifactId}:`,
          error
        );
        return [];
      }
    },
    enabled: !!artifactId && !!collectionId,
    // Longer stale time since group membership changes infrequently
    // This reduces API calls when navigating between artifacts
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
