'use client';

/**
 * Custom hooks for memory item management using TanStack Query
 *
 * Provides data fetching, caching, mutations, and selection state management
 * for memory items in the context system. Memory items track decisions,
 * constraints, learnings, style rules, and gotchas per project.
 *
 * Includes:
 * - useMemoryItems / useMemoryItem / useMemoryItemCounts (queries)
 * - useCreateMemoryItem / useUpdateMemoryItem / useDeleteMemoryItem (CRUD mutations)
 * - usePromoteMemoryItem / useDeprecateMemoryItem (lifecycle mutations)
 * - useBulkPromoteMemoryItems / useBulkDeprecateMemoryItems (bulk lifecycle)
 * - useMergeMemoryItems (merge mutation)
 * - useMemorySelection (client-side selection state)
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseMutationOptions } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import type { MemoryItemListResponse } from '@/sdk/models/MemoryItemListResponse';
import type { MemoryItemCreateRequest } from '@/sdk/models/MemoryItemCreateRequest';
import type { MemoryItemUpdateRequest } from '@/sdk/models/MemoryItemUpdateRequest';
import type { PromoteRequest } from '@/sdk/models/PromoteRequest';
import type { DeprecateRequest } from '@/sdk/models/DeprecateRequest';
import type { BulkPromoteRequest } from '@/sdk/models/BulkPromoteRequest';
import type { BulkDeprecateRequest } from '@/sdk/models/BulkDeprecateRequest';
import type { BulkActionResponse } from '@/sdk/models/BulkActionResponse';
import type { MergeRequest } from '@/sdk/models/MergeRequest';
import type { MergeResponse } from '@/sdk/models/MergeResponse';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryType } from '@/sdk/models/MemoryType';

// ============================================================================
// FILTERS INTERFACE
// ============================================================================

/**
 * Filter parameters for memory item list queries.
 */
export interface MemoryItemFilters {
  projectId: string;
  status?: MemoryStatus;
  type?: MemoryType;
  shareScope?: 'private' | 'project' | 'global_candidate';
  gitBranch?: string;
  gitCommit?: string;
  sessionId?: string;
  agentType?: string;
  model?: string;
  sourceType?: string;
  minConfidence?: number;
  search?: string;
  sortBy?: string; // created_at | confidence | access_count
  sortOrder?: 'asc' | 'desc';
  cursor?: string;
  limit?: number;
}

/**
 * Filter parameters for global memory list queries.
 */
export interface GlobalMemoryItemFilters {
  projectId?: string;
  status?: MemoryStatus;
  type?: MemoryType;
  shareScope?: 'private' | 'project' | 'global_candidate';
  gitBranch?: string;
  gitCommit?: string;
  sessionId?: string;
  agentType?: string;
  model?: string;
  sourceType?: string;
  minConfidence?: number;
  search?: string;
  sortBy?: string; // created_at | confidence | access_count
  sortOrder?: 'asc' | 'desc';
  cursor?: string;
  limit?: number;
}

// ============================================================================
// QUERY KEY FACTORY
// ============================================================================

/**
 * Query key factory for type-safe cache management of memory items.
 *
 * Hierarchy:
 *   ['memory-items']
 *     -> ['memory-items', 'list']
 *       -> ['memory-items', 'list', filters]
 *     -> ['memory-items', 'detail']
 *       -> ['memory-items', 'detail', id]
 *     -> ['memory-items', 'count']
 *       -> ['memory-items', 'count', filters]
 */
export const memoryItemKeys = {
  all: ['memory-items'] as const,
  lists: () => [...memoryItemKeys.all, 'list'] as const,
  list: (filters?: MemoryItemFilters) => [...memoryItemKeys.lists(), filters] as const,
  globalLists: () => [...memoryItemKeys.all, 'global-list'] as const,
  globalList: (filters?: GlobalMemoryItemFilters) =>
    [...memoryItemKeys.globalLists(), filters] as const,
  details: () => [...memoryItemKeys.all, 'detail'] as const,
  detail: (id: string) => [...memoryItemKeys.details(), id] as const,
  counts: () => [...memoryItemKeys.all, 'count'] as const,
  count: (filters?: { projectId: string; status?: MemoryStatus; type?: MemoryType }) =>
    [...memoryItemKeys.counts(), filters] as const,
};

// ============================================================================
// STALE TIME (interactive/monitoring = 30 seconds)
// ============================================================================

const MEMORY_STALE_TIME = 30 * 1000;

// ============================================================================
// QUERY HOOKS
// ============================================================================

/**
 * Fetch a paginated list of memory items for a project.
 *
 * Uses cursor-based pagination. Enabled only when `projectId` is truthy.
 *
 * @param filters - Filter/sort/pagination parameters (projectId required)
 * @returns Query result with MemoryItemListResponse
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useMemoryItems({ projectId: 'proj-1', status: 'active' });
 * ```
 */
export function useMemoryItems(filters: MemoryItemFilters) {
  return useQuery({
    queryKey: memoryItemKeys.list(filters),
    queryFn: async (): Promise<MemoryItemListResponse> => {
      const params = new URLSearchParams();
      params.set('project_id', filters.projectId);
      if (filters.status) params.set('status', filters.status);
      if (filters.type) params.set('type', filters.type);
      if (filters.shareScope) params.set('share_scope', filters.shareScope);
      if (filters.gitBranch) params.set('git_branch', filters.gitBranch);
      if (filters.gitCommit) params.set('git_commit', filters.gitCommit);
      if (filters.sessionId) params.set('session_id', filters.sessionId);
      if (filters.agentType) params.set('agent_type', filters.agentType);
      if (filters.model) params.set('model', filters.model);
      if (filters.sourceType) params.set('source_type', filters.sourceType);
      if (filters.search) params.set('search', filters.search);
      if (filters.minConfidence != null) params.set('min_confidence', String(filters.minConfidence));
      if (filters.limit != null) params.set('limit', String(filters.limit));
      if (filters.cursor) params.set('cursor', filters.cursor);
      if (filters.sortBy) params.set('sort_by', filters.sortBy);
      if (filters.sortOrder) params.set('sort_order', filters.sortOrder);
      return apiRequest<MemoryItemListResponse>(`/memory-items?${params.toString()}`);
    },
    enabled: !!filters.projectId,
    staleTime: MEMORY_STALE_TIME,
  });
}

/**
 * Fetch memory items globally or scoped to a selected project.
 *
 * - If projectId is provided, uses the project-scoped list endpoint.
 * - Otherwise uses the global list endpoint.
 */
export function useGlobalMemoryItems(filters: GlobalMemoryItemFilters) {
  return useQuery({
    queryKey: memoryItemKeys.globalList(filters),
    queryFn: async (): Promise<MemoryItemListResponse> => {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.type) params.set('type', filters.type);
      if (filters.shareScope) params.set('share_scope', filters.shareScope);
      if (filters.gitBranch) params.set('git_branch', filters.gitBranch);
      if (filters.gitCommit) params.set('git_commit', filters.gitCommit);
      if (filters.sessionId) params.set('session_id', filters.sessionId);
      if (filters.agentType) params.set('agent_type', filters.agentType);
      if (filters.model) params.set('model', filters.model);
      if (filters.sourceType) params.set('source_type', filters.sourceType);
      if (filters.search) params.set('search', filters.search);
      if (filters.minConfidence != null) params.set('min_confidence', String(filters.minConfidence));
      if (filters.limit != null) params.set('limit', String(filters.limit));
      if (filters.cursor) params.set('cursor', filters.cursor);
      if (filters.sortBy) params.set('sort_by', filters.sortBy);
      if (filters.sortOrder) params.set('sort_order', filters.sortOrder);

      if (filters.projectId) {
        params.set('project_id', filters.projectId);
        return apiRequest<MemoryItemListResponse>(`/memory-items?${params.toString()}`);
      }

      return apiRequest<MemoryItemListResponse>(`/memory-items/global?${params.toString()}`);
    },
    staleTime: MEMORY_STALE_TIME,
  });
}

/**
 * Fetch a single memory item by ID. Increments access count on the backend.
 *
 * @param id - Memory item ID (undefined disables the query)
 * @returns Query result with MemoryItemResponse
 *
 * @example
 * ```tsx
 * const { data: item } = useMemoryItem(selectedId);
 * ```
 */
export function useMemoryItem(id: string | undefined) {
  return useQuery({
    queryKey: memoryItemKeys.detail(id!),
    queryFn: async (): Promise<MemoryItemResponse> => {
      return apiRequest<MemoryItemResponse>(`/memory-items/${id}`);
    },
    enabled: !!id,
    staleTime: MEMORY_STALE_TIME,
  });
}

/**
 * Fetch count of memory items for a project, with optional status/type filters.
 * Useful for filter badges and summary displays.
 *
 * @param filters - projectId (required), optional status and type
 * @returns Query result with count record
 *
 * @example
 * ```tsx
 * const { data: counts } = useMemoryItemCounts({ projectId: 'proj-1' });
 * ```
 */
export function useMemoryItemCounts(filters: {
  projectId: string;
  status?: MemoryStatus;
  type?: MemoryType;
}) {
  return useQuery({
    queryKey: memoryItemKeys.count(filters),
    queryFn: async (): Promise<Record<string, number>> => {
      const buildCountPath = (params: URLSearchParams) =>
        `/memory-items/count?${params.toString()}`;

      // Filtered count request preserves existing single-count behavior.
      if (filters.status || filters.type) {
        const params = new URLSearchParams();
        params.set('project_id', filters.projectId);
        if (filters.status) params.set('status', filters.status);
        if (filters.type) params.set('type', filters.type);
        const filtered = await apiRequest<{ count: number }>(buildCountPath(params));
        return { all: filtered.count };
      }

      const types: MemoryType[] = ['constraint', 'decision', 'gotcha', 'learning', 'style_rule'];
      const statuses: MemoryStatus[] = ['candidate', 'active', 'stable', 'deprecated'];

      const totalParams = new URLSearchParams();
      totalParams.set('project_id', filters.projectId);

      const typeParams = types.map((type) => {
        const params = new URLSearchParams();
        params.set('project_id', filters.projectId);
        params.set('type', type);
        return params;
      });

      const statusParams = statuses.map((status) => {
        const params = new URLSearchParams();
        params.set('project_id', filters.projectId);
        params.set('status', status);
        return params;
      });

      const responses = await Promise.all([
        apiRequest<{ count: number }>(buildCountPath(totalParams)),
        ...typeParams.map((p) => apiRequest<{ count: number }>(buildCountPath(p))),
        ...statusParams.map((p) => apiRequest<{ count: number }>(buildCountPath(p))),
      ]);

      const [total, ...rest] = responses;
      const typeResponses = rest.slice(0, types.length);
      const statusResponses = rest.slice(types.length);

      const counts: Record<string, number> = { all: total.count };
      types.forEach((type, idx) => {
        counts[type] = typeResponses[idx]?.count ?? 0;
      });
      statuses.forEach((status, idx) => {
        counts[status] = statusResponses[idx]?.count ?? 0;
      });
      return counts;
    },
    enabled: !!filters.projectId,
    staleTime: MEMORY_STALE_TIME,
  });
}

// ============================================================================
// MUTATION HOOKS (HOOKS-3.10: useMutateMemory)
// ============================================================================

/**
 * Create a new memory item for a project.
 *
 * Includes automatic duplicate detection via content hashing on the backend.
 *
 * @example
 * ```tsx
 * const create = useCreateMemoryItem();
 * await create.mutateAsync({ projectId: 'proj-1', data: { type: 'decision', content: '...' } });
 * ```
 */
export function useCreateMemoryItem(
  options?: Pick<
    UseMutationOptions<MemoryItemResponse, Error, { projectId: string; data: MemoryItemCreateRequest }>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: string;
      data: MemoryItemCreateRequest;
    }): Promise<MemoryItemResponse> => {
      return apiRequest<MemoryItemResponse>(`/memory-items?project_id=${encodeURIComponent(projectId)}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Update an existing memory item. Only provided fields are changed.
 *
 * @example
 * ```tsx
 * const update = useUpdateMemoryItem();
 * await update.mutateAsync({ itemId: 'item-1', data: { confidence: 0.9 } });
 * ```
 */
export function useUpdateMemoryItem(
  options?: Pick<
    UseMutationOptions<MemoryItemResponse, Error, { itemId: string; data: MemoryItemUpdateRequest }>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      data,
    }: {
      itemId: string;
      data: MemoryItemUpdateRequest;
    }): Promise<MemoryItemResponse> => {
      return apiRequest<MemoryItemResponse>(`/memory-items/${itemId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      const [, { itemId }] = args;
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.detail(itemId) });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Permanently delete a memory item by ID.
 *
 * @example
 * ```tsx
 * const remove = useDeleteMemoryItem();
 * await remove.mutateAsync('item-1');
 * ```
 */
export function useDeleteMemoryItem(
  options?: Pick<UseMutationOptions<void, Error, string>, 'onSuccess' | 'onError'>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (itemId: string): Promise<void> => {
      return apiRequest<void>(`/memory-items/${itemId}`, { method: 'DELETE' });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Promote a memory item to the next lifecycle stage.
 *
 * State machine: candidate -> active -> stable.
 * Items that are already stable or deprecated cannot be promoted.
 *
 * @example
 * ```tsx
 * const promote = usePromoteMemoryItem();
 * await promote.mutateAsync({ itemId: 'item-1', data: { reason: 'Proven in prod' } });
 * ```
 */
export function usePromoteMemoryItem(
  options?: Pick<
    UseMutationOptions<MemoryItemResponse, Error, { itemId: string; data: PromoteRequest }>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      data,
    }: {
      itemId: string;
      data: PromoteRequest;
    }): Promise<MemoryItemResponse> => {
      return apiRequest<MemoryItemResponse>(`/memory-items/${itemId}/promote`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      const [, { itemId }] = args;
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.detail(itemId) });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Deprecate a memory item regardless of its current lifecycle stage.
 *
 * Any non-deprecated status can transition to deprecated.
 *
 * @example
 * ```tsx
 * const deprecate = useDeprecateMemoryItem();
 * await deprecate.mutateAsync({ itemId: 'item-1', data: { reason: 'Superseded' } });
 * ```
 */
export function useDeprecateMemoryItem(
  options?: Pick<
    UseMutationOptions<MemoryItemResponse, Error, { itemId: string; data: DeprecateRequest }>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      data,
    }: {
      itemId: string;
      data: DeprecateRequest;
    }): Promise<MemoryItemResponse> => {
      return apiRequest<MemoryItemResponse>(`/memory-items/${itemId}/deprecate`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      const [, { itemId }] = args;
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.detail(itemId) });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Promote multiple memory items to their next lifecycle stage in a single request.
 *
 * @example
 * ```tsx
 * const bulkPromote = useBulkPromoteMemoryItems();
 * await bulkPromote.mutateAsync({ item_ids: ['a', 'b'], reason: 'Batch promotion' });
 * ```
 */
export function useBulkPromoteMemoryItems(
  options?: Pick<
    UseMutationOptions<BulkActionResponse, Error, BulkPromoteRequest>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BulkPromoteRequest): Promise<BulkActionResponse> => {
      return apiRequest<BulkActionResponse>('/memory-items/bulk-promote', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Deprecate multiple memory items in a single request.
 *
 * @example
 * ```tsx
 * const bulkDeprecate = useBulkDeprecateMemoryItems();
 * await bulkDeprecate.mutateAsync({ item_ids: ['a', 'b'], reason: 'Cleanup' });
 * ```
 */
export function useBulkDeprecateMemoryItems(
  options?: Pick<
    UseMutationOptions<BulkActionResponse, Error, BulkDeprecateRequest>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BulkDeprecateRequest): Promise<BulkActionResponse> => {
      return apiRequest<BulkActionResponse>('/memory-items/bulk-deprecate', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Delete multiple memory items by looping individual DELETE calls.
 *
 * Since there is no bulk-delete API endpoint, this uses Promise.allSettled
 * to fire individual deletions in parallel and reports success/failure counts.
 *
 * @example
 * ```tsx
 * const bulkDelete = useBulkDeleteMemoryItems();
 * await bulkDelete.mutateAsync(['item-1', 'item-2', 'item-3']);
 * ```
 */
export function useBulkDeleteMemoryItems(
  options?: Pick<UseMutationOptions<{ deleted: number; failed: number }, Error, string[]>, 'onSuccess' | 'onError'>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (itemIds: string[]): Promise<{ deleted: number; failed: number }> => {
      const results = await Promise.allSettled(
        itemIds.map((id) => apiRequest<void>(`/memory-items/${id}`, { method: 'DELETE' }))
      );
      const deleted = results.filter((r) => r.status === 'fulfilled').length;
      const failed = results.filter((r) => r.status === 'rejected').length;
      return { deleted, failed };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

/**
 * Merge two memory items using a specified strategy.
 *
 * Strategies:
 * - keep_target: Keep the target's content, deprecate the source.
 * - keep_source: Replace the target's content with the source's, deprecate the source.
 * - combine: Use the provided merged_content for the target, deprecate the source.
 *
 * The source item is always deprecated after a successful merge.
 *
 * @example
 * ```tsx
 * const merge = useMergeMemoryItems();
 * await merge.mutateAsync({ source_id: 'a', target_id: 'b', strategy: 'keep_target' });
 * ```
 */
export function useMergeMemoryItems(
  options?: Pick<
    UseMutationOptions<MergeResponse, Error, MergeRequest>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MergeRequest): Promise<MergeResponse> => {
      return apiRequest<MergeResponse>('/memory-items/merge', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.globalLists() });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.counts() });
      // Invalidate both source and target details
      const [, variables] = args;
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.detail(variables.source_id) });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.detail(variables.target_id) });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

// ============================================================================
// SELECTION HOOK (HOOKS-3.11: useMemorySelection)
// ============================================================================

/**
 * Client-side selection state for memory items.
 *
 * Provides multi-select with toggle, select-all, and clear operations.
 * Includes focused index tracking for keyboard navigation.
 *
 * @returns Selection state and manipulation functions
 *
 * @example
 * ```tsx
 * const { selectedIds, toggleSelect, selectAll, clearSelection, isSelected } = useMemorySelection();
 *
 * // Toggle single item
 * <Checkbox checked={isSelected(item.id)} onChange={() => toggleSelect(item.id)} />
 *
 * // Select all visible
 * <Button onClick={() => selectAll(visibleIds)}>Select All</Button>
 *
 * // Bulk action on selection
 * <Button onClick={() => bulkPromote({ item_ids: [...selectedIds] })}>Promote Selected</Button>
 * ```
 */
export function useMemorySelection() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback((id: string) => selectedIds.has(id), [selectedIds]);

  return {
    selectedIds,
    focusedIndex,
    setFocusedIndex,
    toggleSelect,
    selectAll,
    clearSelection,
    isSelected,
  };
}
