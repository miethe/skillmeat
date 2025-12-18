/**
 * Custom hooks for tags management using TanStack Query
 *
 * Provides data fetching, caching, and state management for tags.
 * Uses live API data with proper error handling and cache invalidation.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchTags,
  searchTags,
  createTag,
  updateTag,
  deleteTag,
  getArtifactTags,
  addTagToArtifact,
  removeTagFromArtifact,
  type Tag,
  type TagCreateRequest,
  type TagUpdateRequest,
  type TagListResponse,
} from '@/lib/api/tags';

/**
 * Query keys factory for type-safe cache management
 */
export const tagKeys = {
  all: ['tags'] as const,
  lists: () => [...tagKeys.all, 'list'] as const,
  list: (filters?: { limit?: number; after?: string }) =>
    [...tagKeys.lists(), filters] as const,
  search: (query: string) => [...tagKeys.all, 'search', query] as const,
  artifact: (artifactId: string) =>
    [...tagKeys.all, 'artifact', artifactId] as const,
};

/**
 * Fetch all tags with optional pagination
 *
 * @param limit - Maximum number of tags to return
 * @param after - Cursor for pagination
 * @returns Query result with tags list
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useTags(50);
 * if (data) {
 *   console.log(`Found ${data.page_info.total} tags`);
 * }
 * ```
 */
export function useTags(limit?: number, after?: string) {
  return useQuery({
    queryKey: tagKeys.list({ limit, after }),
    queryFn: () => fetchTags(limit, after),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Search tags by query string
 *
 * @param query - Search query string
 * @param enabled - Whether to enable the query (default: true when query is non-empty)
 * @returns Query result with matching tags
 *
 * @example
 * ```tsx
 * const { data: searchResults } = useSearchTags('python');
 * ```
 */
export function useSearchTags(query: string, enabled = true) {
  return useQuery({
    queryKey: tagKeys.search(query),
    queryFn: () => searchTags(query),
    enabled: enabled && query.length > 0,
    staleTime: 30 * 1000, // 30 seconds - more frequent updates for search
  });
}

/**
 * Fetch all tags for a specific artifact
 *
 * @param artifactId - Artifact ID
 * @returns Query result with artifact's tags
 *
 * @example
 * ```tsx
 * const { data: artifactTags } = useArtifactTags('canvas-design');
 * ```
 */
export function useArtifactTags(artifactId: string | undefined) {
  return useQuery({
    queryKey: tagKeys.artifact(artifactId!),
    queryFn: () => getArtifactTags(artifactId!),
    enabled: !!artifactId,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Create new tag mutation
 *
 * @returns Mutation function for creating tags
 *
 * @example
 * ```tsx
 * const createTag = useCreateTag();
 * await createTag.mutateAsync({
 *   name: 'Python',
 *   slug: 'python',
 *   color: '#3776ab'
 * });
 * ```
 */
export function useCreateTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TagCreateRequest): Promise<Tag> => {
      return createTag(data);
    },
    onSuccess: () => {
      // Invalidate all tag lists to trigger refetch
      queryClient.invalidateQueries({ queryKey: tagKeys.all });
    },
  });
}

/**
 * Update existing tag mutation
 *
 * @returns Mutation function for updating tags
 *
 * @example
 * ```tsx
 * const updateTag = useUpdateTag();
 * await updateTag.mutateAsync({
 *   id: 'tag-123',
 *   data: { name: 'Python 3' }
 * });
 * ```
 */
export function useUpdateTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TagUpdateRequest }): Promise<Tag> => {
      return updateTag(id, data);
    },
    onSuccess: () => {
      // Invalidate all tag lists to trigger refetch
      queryClient.invalidateQueries({ queryKey: tagKeys.all });
    },
  });
}

/**
 * Delete tag mutation
 *
 * @returns Mutation function for deleting tags
 *
 * @example
 * ```tsx
 * const deleteTag = useDeleteTag();
 * await deleteTag.mutateAsync('tag-123');
 * ```
 */
export function useDeleteTag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string): Promise<void> => {
      return deleteTag(id);
    },
    onSuccess: () => {
      // Invalidate all tag lists to trigger refetch
      queryClient.invalidateQueries({ queryKey: tagKeys.all });
    },
  });
}

/**
 * Add tag to artifact mutation
 *
 * @returns Mutation function for adding tags to artifacts
 *
 * @example
 * ```tsx
 * const addTag = useAddTagToArtifact();
 * await addTag.mutateAsync({
 *   artifactId: 'canvas-design',
 *   tagId: 'python'
 * });
 * ```
 */
export function useAddTagToArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ artifactId, tagId }: { artifactId: string; tagId: string }): Promise<void> => {
      return addTagToArtifact(artifactId, tagId);
    },
    onSuccess: (_, { artifactId }) => {
      // Invalidate artifact's tags to trigger refetch
      queryClient.invalidateQueries({ queryKey: tagKeys.artifact(artifactId) });
    },
  });
}

/**
 * Remove tag from artifact mutation
 *
 * @returns Mutation function for removing tags from artifacts
 *
 * @example
 * ```tsx
 * const removeTag = useRemoveTagFromArtifact();
 * await removeTag.mutateAsync({
 *   artifactId: 'canvas-design',
 *   tagId: 'python'
 * });
 * ```
 */
export function useRemoveTagFromArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ artifactId, tagId }: { artifactId: string; tagId: string }): Promise<void> => {
      return removeTagFromArtifact(artifactId, tagId);
    },
    onSuccess: (_, { artifactId }) => {
      // Invalidate artifact's tags to trigger refetch
      queryClient.invalidateQueries({ queryKey: tagKeys.artifact(artifactId) });
    },
  });
}
