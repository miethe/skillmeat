/**
 * Custom hooks for group management using TanStack Query
 *
 * Provides hooks for fetching, creating, updating, deleting, and reordering groups
 * within collections, as well as managing artifacts within groups.
 */

import { useQuery, useMutation, useQueryClient, type UseQueryResult, type UseMutationResult } from '@tanstack/react-query';
import { apiRequest, apiConfig } from '@/lib/api';
import type {
  Group,
  CreateGroupRequest,
  UpdateGroupRequest,
  GroupArtifact,
  GroupListResponse,
} from '@/types/groups';

const USE_MOCKS = apiConfig.useMocks;

/**
 * Query keys factory for group-related queries
 * Structured hierarchically for efficient cache invalidation
 */
export const groupKeys = {
  all: ['groups'] as const,
  lists: () => [...groupKeys.all, 'list'] as const,
  list: (collectionId?: string) => [...groupKeys.lists(), { collectionId }] as const,
  details: () => [...groupKeys.all, 'detail'] as const,
  detail: (id: string) => [...groupKeys.details(), id] as const,
  artifacts: (groupId: string) => [...groupKeys.detail(groupId), 'artifacts'] as const,
};

// API response interfaces matching backend schemas
interface ApiGroupListResponse {
  groups: Group[];
  total: number;
}

/**
 * Fetch groups for a collection
 *
 * @param collectionId - Parent collection ID (required)
 * @returns Query result with groups array ordered by position
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGroups(collectionId);
 * if (data) {
 *   // data.groups is already sorted by position
 *   data.groups.map(group => <GroupCard key={group.id} group={group} />)
 * }
 * ```
 */
export function useGroups(collectionId: string | undefined): UseQueryResult<GroupListResponse, Error> {
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
export function useGroupArtifacts(groupId: string | undefined): UseQueryResult<GroupArtifact[], Error> {
  return useQuery({
    queryKey: groupKeys.artifacts(groupId!),
    queryFn: async (): Promise<GroupArtifact[]> => {
      if (!groupId) {
        throw new Error('Group ID is required');
      }

      try {
        const artifacts = await apiRequest<GroupArtifact[]>(`/groups/${groupId}/artifacts`);
        // Sort by position to ensure consistent ordering
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
export function useUpdateGroup(): UseMutationResult<Group, Error, { id: string; data: UpdateGroupRequest }> {
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
export function useDeleteGroup(): UseMutationResult<void, Error, { id: string; collectionId: string }> {
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
export function useReorderGroups(): UseMutationResult<void, Error, { collectionId: string; groupIds: string[] }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ collectionId, groupIds }: { collectionId: string; groupIds: string[] }): Promise<void> => {
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
export function useAddArtifactToGroup(): UseMutationResult<void, Error, { groupId: string; artifactId: string; position?: number }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ groupId, artifactId, position }: { groupId: string; artifactId: string; position?: number }): Promise<void> => {
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
export function useRemoveArtifactFromGroup(): UseMutationResult<void, Error, { groupId: string; artifactId: string }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ groupId, artifactId }: { groupId: string; artifactId: string }): Promise<void> => {
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
export function useReorderArtifactsInGroup(): UseMutationResult<void, Error, { groupId: string; artifactIds: string[] }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ groupId, artifactIds }: { groupId: string; artifactIds: string[] }): Promise<void> => {
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
export function useMoveArtifactToGroup(): UseMutationResult<void, Error, {
  sourceGroupId: string;
  targetGroupId: string;
  artifactId: string;
  position?: number
}> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sourceGroupId,
      targetGroupId,
      artifactId,
      position
    }: {
      sourceGroupId: string;
      targetGroupId: string;
      artifactId: string;
      position?: number
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
          console.warn(`[groups] Move artifact API failed from ${sourceGroupId} to ${targetGroupId}`, error);
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
export function useCopyGroup(): UseMutationResult<Group, Error, {
  groupId: string;
  targetCollectionId: string;
}> {
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
    },
  });
}
