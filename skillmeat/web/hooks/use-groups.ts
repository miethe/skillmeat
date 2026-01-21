/**
 * Custom hooks for group management using TanStack Query.
 *
 * Groups are organizational containers within collections that allow users to
 * logically arrange artifacts. Each group has a position for ordering and can
 * contain multiple artifacts (also with positions for intra-group ordering).
 *
 * @module hooks/use-groups
 *
 * ## Available Hooks
 *
 * ### Query Hooks
 * - `useGroups(collectionId)` - Fetch all groups for a collection
 * - `useGroup(id)` - Fetch single group details
 * - `useGroupArtifacts(groupId)` - Fetch artifacts within a group
 *
 * ### Mutation Hooks
 * - `useCreateGroup()` - Create new group
 * - `useUpdateGroup()` - Update group name/description
 * - `useDeleteGroup()` - Delete group
 * - `useReorderGroups()` - Reorder groups within collection
 * - `useAddArtifactToGroup()` - Add artifact to group
 * - `useRemoveArtifactFromGroup()` - Remove artifact from group
 * - `useReorderArtifactsInGroup()` - Reorder artifacts within group
 * - `useMoveArtifactToGroup()` - Move artifact between groups
 * - `useCopyGroup()` - Copy group to another collection
 *
 * ## Cache Strategy
 *
 * All queries use 5-minute stale time. Mutations automatically invalidate
 * relevant caches via hierarchical query keys.
 *
 * ### Cross-Hook Cache Invalidation
 *
 * Group mutations can affect artifact-group membership queries (from `use-artifact-groups.ts`).
 * When groups or group membership change, we invalidate both:
 * - `groupKeys.*` - For group list/detail queries in this module
 * - `artifactGroupKeys.all` - For "which groups contain artifact X" queries
 *
 * This ensures UI components showing group membership badges stay in sync when:
 * - Artifacts are added/removed from groups
 * - Groups are deleted (artifacts no longer belong to that group)
 * - Artifacts are moved between groups
 *
 * @example
 * ```tsx
 * import { useGroups, useCreateGroup, groupKeys } from '@/hooks';
 *
 * function CollectionGroups({ collectionId }) {
 *   const { data } = useGroups(collectionId);
 *   const createGroup = useCreateGroup();
 *
 *   const handleCreate = async () => {
 *     await createGroup.mutateAsync({
 *       collection_id: collectionId,
 *       name: 'New Group',
 *     });
 *     // Cache auto-invalidated
 *   };
 * }
 * ```
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query';
import { apiRequest, apiConfig } from '@/lib/api';
import type {
  Group,
  GroupWithArtifacts,
  CreateGroupRequest,
  UpdateGroupRequest,
  GroupArtifact,
  GroupListResponse,
} from '@/types/groups';
import { artifactGroupKeys } from './use-artifact-groups';

const USE_MOCKS = apiConfig.useMocks;

/**
 * Query keys factory for group-related queries.
 *
 * Provides hierarchical cache keys enabling targeted or broad invalidation.
 * Use these keys with `queryClient.invalidateQueries()` for cache management.
 *
 * @example
 * ```typescript
 * // Invalidate all group queries
 * queryClient.invalidateQueries({ queryKey: groupKeys.all });
 *
 * // Invalidate all group lists (all collections)
 * queryClient.invalidateQueries({ queryKey: groupKeys.lists() });
 *
 * // Invalidate specific collection's groups
 * queryClient.invalidateQueries({ queryKey: groupKeys.list(collectionId) });
 *
 * // Invalidate specific group detail
 * queryClient.invalidateQueries({ queryKey: groupKeys.detail(groupId) });
 *
 * // Invalidate group's artifacts
 * queryClient.invalidateQueries({ queryKey: groupKeys.artifacts(groupId) });
 * ```
 */
export const groupKeys = {
  /** Base key for all group queries: `['groups']` */
  all: ['groups'] as const,
  /** Key for all group list queries: `['groups', 'list']` */
  lists: () => [...groupKeys.all, 'list'] as const,
  /** Key for specific collection's groups: `['groups', 'list', { collectionId }]` */
  list: (collectionId?: string) => [...groupKeys.lists(), { collectionId }] as const,
  /** Key for all group detail queries: `['groups', 'detail']` */
  details: () => [...groupKeys.all, 'detail'] as const,
  /** Key for specific group detail: `['groups', 'detail', groupId]` */
  detail: (id: string) => [...groupKeys.details(), id] as const,
  /** Key for group's artifacts: `['groups', 'detail', groupId, 'artifacts']` */
  artifacts: (groupId: string) => [...groupKeys.detail(groupId), 'artifacts'] as const,
};

// API response interfaces matching backend schemas
interface ApiGroupListResponse {
  groups: Group[];
  total: number;
}

/**
 * Fetch groups for a specific collection.
 *
 * Retrieves all groups belonging to a collection, sorted by position for
 * consistent display ordering. Uses the `GET /api/v1/groups?collection_id={id}`
 * endpoint.
 *
 * @param collectionId - The collection ID to fetch groups for. When undefined,
 *   the query is disabled and returns undefined data.
 *
 * @returns TanStack Query result containing:
 *   - `data.groups`: Array of Group objects sorted by position (ascending)
 *   - `data.total`: Total count of groups in the collection
 *   - Standard query states: `isLoading`, `isError`, `error`, `refetch`, etc.
 *
 * @remarks
 * **Caching**: Results are cached for 5 minutes (`staleTime: 300000ms`).
 * Use `queryClient.invalidateQueries({ queryKey: groupKeys.list(collectionId) })`
 * to force refresh.
 *
 * **Cache Key Hierarchy**: Query key is `['groups', 'list', { collectionId }]`.
 * Invalidating `groupKeys.lists()` will clear all collection group caches.
 *
 * **Error Handling**: In mock mode (`USE_MOCKS=true`), API failures return
 * an empty array fallback `{ groups: [], total: 0 }`. In production mode,
 * errors are thrown and available via `error` property.
 *
 * @example
 * ```tsx
 * // Basic usage with loading state
 * function GroupList({ collectionId }: { collectionId: string }) {
 *   const { data, isLoading, isError, error } = useGroups(collectionId);
 *
 *   if (isLoading) return <Skeleton />;
 *   if (isError) return <ErrorMessage error={error} />;
 *
 *   // data.groups is already sorted by position
 *   return (
 *     <div>
 *       {data.groups.map(group => (
 *         <GroupCard key={group.id} group={group} />
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 *
 * @example
 * ```tsx
 * // Conditional fetching - query disabled when no collection selected
 * const { data } = useGroups(selectedCollectionId); // undefined until selected
 * ```
 *
 * @example
 * ```tsx
 * // Manual cache invalidation after mutation
 * const queryClient = useQueryClient();
 * queryClient.invalidateQueries({ queryKey: groupKeys.list(collectionId) });
 * ```
 */
export function useGroups(
  collectionId: string | undefined
): UseQueryResult<GroupListResponse, Error> {
  return useQuery({
    queryKey: groupKeys.list(collectionId),
    queryFn: async (): Promise<GroupListResponse> => {
      if (!collectionId) {
        throw new Error('Collection ID is required');
      }

      try {
        const params = new URLSearchParams({ collection_id: collectionId });
        const response = await apiRequest<ApiGroupListResponse>(`/groups?${params.toString()}`);

        // Sort by position to ensure consistent ordering
        const sortedGroups = [...response.groups].sort((a, b) => a.position - b.position);

        return {
          groups: sortedGroups,
          total: response.total,
        };
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[groups] API failed, falling back to mock data', error);
          return {
            groups: [],
            total: 0,
          };
        }
        throw error;
      }
    },
    enabled: !!collectionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch single group by ID with full details
 *
 * @param id - Group ID
 * @returns Query result with group details
 *
 * @example
 * ```tsx
 * const { data: group } = useGroup(groupId);
 * if (group) {
 *   console.log(`${group.name} has ${group.artifact_count} artifacts`);
 * }
 * ```
 */
export function useGroup(id: string | undefined): UseQueryResult<Group, Error> {
  return useQuery({
    queryKey: groupKeys.detail(id!),
    queryFn: async (): Promise<Group> => {
      if (!id) {
        throw new Error('Group ID is required');
      }

      try {
        const group = await apiRequest<Group>(`/groups/${id}`);
        return group;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Failed to fetch group ${id}, falling back to mock`, error);
          throw new Error('Group not found');
        }
        throw error;
      }
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch artifacts in a group
 *
 * Uses GET /groups/{groupId} endpoint which returns GroupWithArtifactsResponse
 * containing the artifacts array. This hook extracts just the artifacts from
 * that response for convenience when only artifacts are needed.
 *
 * Note: There is no dedicated GET /groups/{groupId}/artifacts endpoint.
 * The group detail endpoint already includes artifacts in its response.
 *
 * @param groupId - Group ID
 * @returns Query result with artifacts ordered by position
 *
 * @example
 * ```tsx
 * const { data: artifacts } = useGroupArtifacts(groupId);
 * artifacts?.map(artifact => (
 *   <div key={artifact.artifact_id}>
 *     Position: {artifact.position}
 *   </div>
 * ))
 * ```
 */
export function useGroupArtifacts(
  groupId: string | undefined
): UseQueryResult<GroupArtifact[], Error> {
  return useQuery({
    queryKey: groupKeys.artifacts(groupId!),
    queryFn: async (): Promise<GroupArtifact[]> => {
      if (!groupId) {
        throw new Error('Group ID is required');
      }

      try {
        // Use the group detail endpoint which includes artifacts in the response
        // API: GET /groups/{groupId} returns GroupWithArtifactsResponse with artifacts array
        const group = await apiRequest<GroupWithArtifacts>(`/groups/${groupId}`);
        const artifacts = group.artifacts ?? [];
        // Sort by position to ensure consistent ordering (backend already sorts, but defensive)
        return [...artifacts].sort((a, b) => a.position - b.position);
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Failed to fetch artifacts for group ${groupId}`, error);
          return [];
        }
        throw error;
      }
    },
    enabled: !!groupId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Create new group mutation
 *
 * Automatically invalidates the parent collection's groups list on success
 *
 * @example
 * ```tsx
 * const createGroup = useCreateGroup();
 *
 * await createGroup.mutateAsync({
 *   collection_id: collectionId,
 *   name: 'My Group',
 *   description: 'Group for organizing skills',
 *   position: 0,
 * });
 * ```
 */
export function useCreateGroup(): UseMutationResult<Group, Error, CreateGroupRequest> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateGroupRequest): Promise<Group> => {
      try {
        const group = await apiRequest<Group>('/groups', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        return group;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn('[groups] Create API failed, falling back to mock', error);
          // Return mock group
          return {
            id: `mock-${Date.now()}`,
            collection_id: data.collection_id,
            name: data.name,
            description: data.description,
            position: data.position ?? 0,
            artifact_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
        }
        throw error;
      }
    },
    onSuccess: (_, { collection_id }) => {
      // Invalidate the collection's groups list
      queryClient.invalidateQueries({ queryKey: groupKeys.list(collection_id) });
    },
  });
}

/**
 * Update existing group mutation
 *
 * Automatically invalidates the group detail and parent collection's groups list
 *
 * @example
 * ```tsx
 * const updateGroup = useUpdateGroup();
 *
 * await updateGroup.mutateAsync({
 *   id: groupId,
 *   data: {
 *     name: 'Updated Name',
 *     description: 'New description',
 *   },
 * });
 * ```
 */
export function useUpdateGroup(): UseMutationResult<
  Group,
  Error,
  { id: string; data: UpdateGroupRequest }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateGroupRequest }): Promise<Group> => {
      try {
        const group = await apiRequest<Group>(`/groups/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        return group;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Update API failed for group ${id}`, error);
          throw error;
        }
        throw error;
      }
    },
    onSuccess: (result, { id }) => {
      // Invalidate the specific group detail
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(id) });
      // Invalidate the parent collection's groups list
      if (result?.collection_id) {
        queryClient.invalidateQueries({ queryKey: groupKeys.list(result.collection_id) });
      }
    },
  });
}

/**
 * Delete group mutation
 *
 * Automatically invalidates the parent collection's groups list on success
 *
 * @example
 * ```tsx
 * const deleteGroup = useDeleteGroup();
 *
 * await deleteGroup.mutateAsync({
 *   id: groupId,
 *   collectionId: collectionId,
 * });
 * ```
 */
export function useDeleteGroup(): UseMutationResult<
  void,
  Error,
  { id: string; collectionId: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id }: { id: string; collectionId: string }): Promise<void> => {
      try {
        await apiRequest<void>(`/groups/${id}`, {
          method: 'DELETE',
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Delete API failed for group ${id}`, error);
          return;
        }
        throw error;
      }
    },
    onSuccess: (_, { collectionId }) => {
      // Invalidate the collection's groups list
      queryClient.invalidateQueries({ queryKey: groupKeys.list(collectionId) });
      // Cross-hook invalidation: artifacts that were in this group
      // no longer belong to it after deletion. Any useArtifactGroups
      // queries showing this group need to refresh.
      queryClient.invalidateQueries({ queryKey: artifactGroupKeys.all });
    },
  });
}

/**
 * Reorder groups within a collection (bulk position update)
 *
 * @param collectionId - Collection ID containing the groups
 * @param groupIds - Array of group IDs in desired order (positions assigned 0, 1, 2, ...)
 *
 * @example
 * ```tsx
 * const reorderGroups = useReorderGroups();
 *
 * // After drag and drop, update order
 * await reorderGroups.mutateAsync({
 *   collectionId,
 *   groupIds: ['group-3', 'group-1', 'group-2'], // New order
 * });
 * ```
 */
export function useReorderGroups(): UseMutationResult<
  void,
  Error,
  { collectionId: string; groupIds: string[] }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      collectionId,
      groupIds,
    }: {
      collectionId: string;
      groupIds: string[];
    }): Promise<void> => {
      try {
        const updates = groupIds.map((id, index) => ({
          id,
          position: index,
        }));

        await apiRequest<void>(`/collections/${collectionId}/groups/reorder`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ groups: updates }),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Reorder API failed for collection ${collectionId}`, error);
          return;
        }
        throw error;
      }
    },
    onSuccess: (_, { collectionId }) => {
      // Invalidate the collection's groups list to reflect new order
      queryClient.invalidateQueries({ queryKey: groupKeys.list(collectionId) });
    },
  });
}

/**
 * Add artifact to group mutation
 *
 * @param groupId - Group ID to add artifact to
 * @param artifactId - Artifact ID to add
 * @param position - Optional position (default: append to end)
 *
 * @example
 * ```tsx
 * const addArtifact = useAddArtifactToGroup();
 *
 * await addArtifact.mutateAsync({
 *   groupId,
 *   artifactId,
 *   position: 0, // Add to beginning
 * });
 * ```
 */
export function useAddArtifactToGroup(): UseMutationResult<
  void,
  Error,
  { groupId: string; artifactId: string; position?: number }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      groupId,
      artifactId,
      position,
    }: {
      groupId: string;
      artifactId: string;
      position?: number;
    }): Promise<void> => {
      try {
        const body: { artifact_ids: string[]; position?: number } = { artifact_ids: [artifactId] };
        if (position !== undefined) {
          body.position = position;
        }
        await apiRequest<void>(`/groups/${groupId}/artifacts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Add artifact API failed for group ${groupId}`, error);
          return;
        }
        throw error;
      }
    },
    onSuccess: (_, { groupId }) => {
      // Invalidate group artifacts and detail to update artifact_count
      queryClient.invalidateQueries({ queryKey: groupKeys.artifacts(groupId) });
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(groupId) });
      // Cross-hook invalidation: artifact's group membership has changed
      // This ensures useArtifactGroups queries reflect the new membership
      queryClient.invalidateQueries({ queryKey: artifactGroupKeys.all });
    },
  });
}

/**
 * Remove artifact from group mutation
 *
 * @param groupId - Group ID to remove artifact from
 * @param artifactId - Artifact ID to remove
 *
 * @example
 * ```tsx
 * const removeArtifact = useRemoveArtifactFromGroup();
 *
 * await removeArtifact.mutateAsync({
 *   groupId,
 *   artifactId,
 * });
 * ```
 */
export function useRemoveArtifactFromGroup(): UseMutationResult<
  void,
  Error,
  { groupId: string; artifactId: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      groupId,
      artifactId,
    }: {
      groupId: string;
      artifactId: string;
    }): Promise<void> => {
      try {
        await apiRequest<void>(`/groups/${groupId}/artifacts/${artifactId}`, {
          method: 'DELETE',
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Remove artifact API failed for group ${groupId}`, error);
          return;
        }
        throw error;
      }
    },
    onSuccess: (_, { groupId }) => {
      // Invalidate group artifacts and detail to update artifact_count
      queryClient.invalidateQueries({ queryKey: groupKeys.artifacts(groupId) });
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(groupId) });
      // Cross-hook invalidation: artifact's group membership has changed
      // This ensures useArtifactGroups queries reflect the removal
      queryClient.invalidateQueries({ queryKey: artifactGroupKeys.all });
    },
  });
}

/**
 * Reorder artifacts within a group
 *
 * @param groupId - Group ID
 * @param artifactIds - Array of artifact IDs in desired order (positions assigned 0, 1, 2, ...)
 *
 * @example
 * ```tsx
 * const reorderArtifacts = useReorderArtifactsInGroup();
 *
 * // After drag and drop within group
 * await reorderArtifacts.mutateAsync({
 *   groupId,
 *   artifactIds: ['artifact-2', 'artifact-1', 'artifact-3'],
 * });
 * ```
 */
export function useReorderArtifactsInGroup(): UseMutationResult<
  void,
  Error,
  { groupId: string; artifactIds: string[] }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      groupId,
      artifactIds,
    }: {
      groupId: string;
      artifactIds: string[];
    }): Promise<void> => {
      try {
        const updates = artifactIds.map((artifact_id, index) => ({
          artifact_id,
          position: index,
        }));

        await apiRequest<void>(`/groups/${groupId}/artifacts/reorder`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ artifacts: updates }),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Reorder artifacts API failed for group ${groupId}`, error);
          return;
        }
        throw error;
      }
    },
    onSuccess: (_, { groupId }) => {
      // Invalidate group artifacts to reflect new order
      queryClient.invalidateQueries({ queryKey: groupKeys.artifacts(groupId) });
    },
  });
}

/**
 * Move artifact between groups
 *
 * Removes artifact from source group and adds to target group atomically
 *
 * @param sourceGroupId - Group to remove artifact from
 * @param targetGroupId - Group to add artifact to
 * @param artifactId - Artifact ID to move
 * @param position - Optional position in target group (default: append)
 *
 * @example
 * ```tsx
 * const moveArtifact = useMoveArtifactToGroup();
 *
 * await moveArtifact.mutateAsync({
 *   sourceGroupId,
 *   targetGroupId,
 *   artifactId,
 *   position: 0, // Add to beginning of target group
 * });
 * ```
 */
export function useMoveArtifactToGroup(): UseMutationResult<
  void,
  Error,
  {
    sourceGroupId: string;
    targetGroupId: string;
    artifactId: string;
    position?: number;
  }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sourceGroupId,
      targetGroupId,
      artifactId,
      position,
    }: {
      sourceGroupId: string;
      targetGroupId: string;
      artifactId: string;
      position?: number;
    }): Promise<void> => {
      try {
        const body = {
          target_group_id: targetGroupId,
          ...(position !== undefined && { position }),
        };

        await apiRequest<void>(`/groups/${sourceGroupId}/artifacts/${artifactId}/move`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(
            `[groups] Move artifact API failed from ${sourceGroupId} to ${targetGroupId}`,
            error
          );
          return;
        }
        throw error;
      }
    },
    onSuccess: (_, { sourceGroupId, targetGroupId }) => {
      // Invalidate both source and target group artifacts and details
      queryClient.invalidateQueries({ queryKey: groupKeys.artifacts(sourceGroupId) });
      queryClient.invalidateQueries({ queryKey: groupKeys.artifacts(targetGroupId) });
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(sourceGroupId) });
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(targetGroupId) });
      // Cross-hook invalidation: artifact's group membership has changed
      // Moving between groups changes which groups the artifact belongs to
      queryClient.invalidateQueries({ queryKey: artifactGroupKeys.all });
    },
  });
}

/**
 * Copy group to another collection
 *
 * Creates a copy of the group (with all its artifacts) in the target collection
 *
 * @param groupId - Group ID to copy
 * @param targetCollectionId - Target collection ID
 *
 * @example
 * ```tsx
 * const copyGroup = useCopyGroup();
 *
 * await copyGroup.mutateAsync({
 *   groupId,
 *   targetCollectionId,
 * });
 * ```
 */
export function useCopyGroup(): UseMutationResult<
  Group,
  Error,
  {
    groupId: string;
    targetCollectionId: string;
  }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      groupId,
      targetCollectionId,
    }: {
      groupId: string;
      targetCollectionId: string;
    }): Promise<Group> => {
      try {
        const group = await apiRequest<Group>(`/groups/${groupId}/copy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_collection_id: targetCollectionId }),
        });
        return group;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn(`[groups] Copy group API failed for group ${groupId}`, error);
          // Return mock group for development
          return {
            id: `mock-copy-${Date.now()}`,
            collection_id: targetCollectionId,
            name: 'Copied Group',
            description: undefined,
            position: 0,
            artifact_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
        }
        throw error;
      }
    },
    onSuccess: (_, { targetCollectionId }) => {
      // Invalidate the target collection's groups list to show the new copy
      queryClient.invalidateQueries({ queryKey: groupKeys.list(targetCollectionId) });
      // Cross-hook invalidation: if the copied group contains artifacts,
      // those artifacts now belong to an additional group in the target collection.
      // Note: This depends on backend behavior - if copy includes artifacts,
      // their membership queries need to reflect the new group.
      queryClient.invalidateQueries({ queryKey: artifactGroupKeys.all });
    },
  });
}
