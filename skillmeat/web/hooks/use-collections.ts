/**
 * Custom hooks for collection management using TanStack Query
 *
 * Provides data fetching, caching, and state management for collections.
 * Uses live API data with proper error handling and cache invalidation.
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import {
  createCollection,
  updateCollection,
  deleteCollection,
  addArtifactToCollection,
  removeArtifactFromCollection,
  fetchCollectionArtifactsPaginated,
  type CollectionArtifactsPaginatedResponse,
} from '@/lib/api/collections';
import type {
  Collection,
  CreateCollectionRequest,
  UpdateCollectionRequest,
  CollectionListResponse,
  CollectionArtifactsResponse,
} from '@/types/collections';

/**
 * API response interface for collection list
 */
interface ApiCollectionListResponse {
  items: Collection[];
  page_info: {
    has_next_page: boolean;
    has_previous_page: boolean;
    start_cursor: string | null;
    end_cursor: string | null;
    total_count: number;
  };
}

/**
 * API response interface for collection artifacts
 */
interface ApiCollectionArtifactsResponse {
  items: Array<{
    name: string;
    type: string;
    version?: string;
    source: string;
  }>;
  page_info: {
    has_next_page: boolean;
    has_previous_page: boolean;
    start_cursor: string | null;
    end_cursor: string | null;
    total_count: number;
  };
}

/**
 * Query keys factory for type-safe cache management
 */
export const collectionKeys = {
  all: ['collections'] as const,
  lists: () => [...collectionKeys.all, 'list'] as const,
  list: (filters?: CollectionFilters) => [...collectionKeys.lists(), filters] as const,
  details: () => [...collectionKeys.all, 'detail'] as const,
  detail: (id: string) => [...collectionKeys.details(), id] as const,
  artifacts: (id: string) => [...collectionKeys.detail(id), 'artifacts'] as const,
  infiniteArtifacts: (id: string, options?: { artifact_type?: string }) =>
    [...collectionKeys.detail(id), 'infinite-artifacts', options] as const,
};

/**
 * Filter options for collection queries
 */
export interface CollectionFilters {
  /** Search query for filtering collections */
  search?: string;
  /** Cursor for pagination */
  after?: string;
  /** Maximum number of items to return */
  limit?: number;
}

/**
 * Fetch all collections with optional filtering and pagination
 *
 * @param filters - Optional filters for search and pagination
 * @returns Query result with collections array
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useCollections({ limit: 10 });
 * if (data) {
 *   console.log(`Found ${data.total} collections`);
 * }
 * ```
 */
export function useCollections(filters?: CollectionFilters) {
  return useQuery({
    queryKey: collectionKeys.list(filters),
    queryFn: async (): Promise<CollectionListResponse> => {
      const params = new URLSearchParams();

      if (filters?.limit) {
        params.set('limit', filters.limit.toString());
      }
      if (filters?.after) {
        params.set('after', filters.after);
      }

      const queryString = params.toString();
      const path = queryString ? `/user-collections?${queryString}` : '/user-collections';

      const response = await apiRequest<ApiCollectionListResponse>(path);

      // Transform API response to frontend format
      const collections = response.items;

      // Apply client-side search filter if provided
      let filteredCollections = collections;
      if (filters?.search) {
        const searchLower = filters.search.toLowerCase();
        filteredCollections = collections.filter(
          (c) => c.name.toLowerCase().includes(searchLower) || c.id.toLowerCase().includes(searchLower)
        );
      }

      return {
        items: filteredCollections,
        total: response.page_info.total_count,
        page: 1,
        page_size: filteredCollections.length,
      };
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch single collection by ID
 *
 * @param id - Collection ID (undefined will disable the query)
 * @returns Query result with collection details
 *
 * @example
 * ```tsx
 * const { data: collection } = useCollection(collectionId);
 * if (collection) {
 *   console.log(`Collection has ${collection.artifact_count} artifacts`);
 * }
 * ```
 */
export function useCollection(id: string | undefined) {
  return useQuery({
    queryKey: collectionKeys.detail(id!),
    queryFn: async (): Promise<Collection> => {
      const collection = await apiRequest<Collection>(`/user-collections/${id}`);
      return collection;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch artifacts in a collection with pagination
 *
 * @param id - Collection ID
 * @param options - Pagination and filtering options
 * @returns Query result with artifact list
 *
 * @example
 * ```tsx
 * const { data } = useCollectionArtifacts(collectionId, { limit: 20 });
 * if (data) {
 *   data.items.forEach(artifact => console.log(artifact.name));
 * }
 * ```
 */
export function useCollectionArtifacts(
  id: string | undefined,
  options?: {
    limit?: number;
    after?: string;
    artifact_type?: string;
  }
) {
  return useQuery({
    queryKey: [...collectionKeys.artifacts(id!), options],
    queryFn: async (): Promise<CollectionArtifactsResponse> => {
      const params = new URLSearchParams();

      if (options?.limit) {
        params.set('limit', options.limit.toString());
      }
      if (options?.after) {
        params.set('after', options.after);
      }
      if (options?.artifact_type) {
        params.set('artifact_type', options.artifact_type);
      }

      const queryString = params.toString();
      const path = queryString
        ? `/user-collections/${id}/artifacts?${queryString}`
        : `/user-collections/${id}/artifacts`;

      const response = await apiRequest<ApiCollectionArtifactsResponse>(path);

      return {
        items: response.items,
        total: response.page_info.total_count,
        page: 1,
        page_size: response.items.length,
      };
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Options for infinite collection artifacts query
 */
export interface InfiniteArtifactsOptions {
  /** Number of items to fetch per page */
  limit?: number;
  /** Filter by artifact type */
  artifact_type?: string;
  /** Whether the query should be enabled */
  enabled?: boolean;
}

/**
 * Fetch collection artifacts with infinite scroll pagination
 *
 * Uses cursor-based pagination for efficient loading of large collections.
 * Returns flattened items from all pages plus pagination controls.
 *
 * @param id - Collection ID (undefined will disable the query)
 * @param options - Pagination and filtering options
 * @returns Infinite query result with pages array and pagination helpers
 *
 * @example
 * ```tsx
 * const {
 *   data,
 *   fetchNextPage,
 *   hasNextPage,
 *   isFetchingNextPage,
 * } = useInfiniteCollectionArtifacts(collectionId, { limit: 20 });
 *
 * // Flatten pages to get all items
 * const allItems = data?.pages.flatMap(p => p.items) || [];
 *
 * // Get total count from first page
 * const totalCount = data?.pages[0]?.page_info.total_count || 0;
 * ```
 */
export function useInfiniteCollectionArtifacts(
  id: string | undefined,
  options?: InfiniteArtifactsOptions
) {
  const { limit = 20, artifact_type, enabled = true } = options || {};

  return useInfiniteQuery({
    queryKey: collectionKeys.infiniteArtifacts(id!, { artifact_type }),
    queryFn: async ({ pageParam }): Promise<CollectionArtifactsPaginatedResponse> => {
      return fetchCollectionArtifactsPaginated(id!, {
        limit,
        after: pageParam,
        artifact_type,
      });
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.page_info.has_next_page ? lastPage.page_info.end_cursor ?? undefined : undefined,
    enabled: !!id && enabled,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Create new collection mutation
 *
 * @returns Mutation function for creating collections
 *
 * @example
 * ```tsx
 * const createCollection = useCreateCollection();
 * await createCollection.mutateAsync({ name: 'My Collection', description: 'Optional description' });
 * ```
 */
export function useCreateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateCollectionRequest): Promise<Collection> => {
      return createCollection(data);
    },
    onSuccess: () => {
      // Invalidate collections list to trigger refetch
      queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
    },
  });
}

/**
 * Update existing collection mutation
 *
 * @returns Mutation function for updating collections
 *
 * @example
 * ```tsx
 * const updateCollection = useUpdateCollection();
 * await updateCollection.mutateAsync({
 *   id: 'default',
 *   data: { name: 'Renamed Collection' }
 * });
 * ```
 */
export function useUpdateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: {
      id: string;
      data: UpdateCollectionRequest;
    }): Promise<Collection> => {
      return updateCollection(id, data);
    },
    onSuccess: (_, { id }) => {
      // Invalidate both the specific collection and the list
      queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
    },
  });
}

/**
 * Delete collection mutation
 *
 * @returns Mutation function for deleting collections
 *
 * @example
 * ```tsx
 * const deleteCollection = useDeleteCollection();
 * await deleteCollection.mutateAsync('collection-id');
 * ```
 */
export function useDeleteCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      return deleteCollection(id);
    },
    onSuccess: () => {
      // Invalidate collections list to remove deleted item
      queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
    },
  });
}

/**
 * Add artifact to collection mutation
 *
 * @returns Mutation function for adding artifacts to collections
 *
 * @example
 * ```tsx
 * const addArtifact = useAddArtifactToCollection();
 * await addArtifact.mutateAsync({
 *   collectionId: 'default',
 *   artifactId: 'canvas-design'
 * });
 * ```
 */
export function useAddArtifactToCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ collectionId, artifactId }: {
      collectionId: string;
      artifactId: string;
    }): Promise<{ collection_id: string; added_count: number; already_present_count: number; total_artifacts: number }> => {
      return addArtifactToCollection(collectionId, artifactId);
    },
    onSuccess: (_, { collectionId }) => {
      // Invalidate collection details and artifacts list
      queryClient.invalidateQueries({ queryKey: collectionKeys.detail(collectionId) });
      queryClient.invalidateQueries({ queryKey: collectionKeys.artifacts(collectionId) });
      // Invalidate artifact queries since collections data on artifacts changes
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });
}

/**
 * Remove artifact from collection mutation
 *
 * @returns Mutation function for removing artifacts from collections
 *
 * @example
 * ```tsx
 * const removeArtifact = useRemoveArtifactFromCollection();
 * await removeArtifact.mutateAsync({
 *   collectionId: 'default',
 *   artifactId: 'canvas-design'
 * });
 * ```
 */
export function useRemoveArtifactFromCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ collectionId, artifactId }: {
      collectionId: string;
      artifactId: string;
    }): Promise<void> => {
      return removeArtifactFromCollection(collectionId, artifactId);
    },
    onSuccess: (_, { collectionId }) => {
      // Invalidate collection details and artifacts list
      queryClient.invalidateQueries({ queryKey: collectionKeys.detail(collectionId) });
      queryClient.invalidateQueries({ queryKey: collectionKeys.artifacts(collectionId) });
      // Invalidate artifact queries since collections data on artifacts changes
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });
}
