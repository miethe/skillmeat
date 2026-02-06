'use client';

/**
 * Custom hooks for context module management using TanStack Query
 *
 * Provides data fetching, caching, and mutations for context modules.
 * Context modules are named groupings of memory items with selector criteria
 * that define how memories are assembled into contextual knowledge.
 *
 * Includes:
 * - useContextModules / useContextModule (queries)
 * - useCreateContextModule / useUpdateContextModule / useDeleteContextModule (CRUD mutations)
 * - useAddMemoryToModule / useRemoveMemoryFromModule (association mutations)
 * - useModuleMemories (query)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseMutationOptions } from '@tanstack/react-query';
import {
  fetchContextModules,
  fetchContextModule,
  createContextModule,
  updateContextModule,
  deleteContextModule,
  addMemoryToModule,
  removeMemoryFromModule,
  fetchModuleMemories,
} from '@/lib/api/context-modules';
import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';
import type { ContextModuleListResponse } from '@/sdk/models/ContextModuleListResponse';
import type { ContextModuleCreateRequest } from '@/sdk/models/ContextModuleCreateRequest';
import type { ContextModuleUpdateRequest } from '@/sdk/models/ContextModuleUpdateRequest';
import type { AddMemoryToModuleRequest } from '@/sdk/models/AddMemoryToModuleRequest';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { memoryItemKeys } from './use-memory-items';

// ============================================================================
// QUERY KEY FACTORY
// ============================================================================

export const contextModuleKeys = {
  all: ['context-modules'] as const,
  lists: () => [...contextModuleKeys.all, 'list'] as const,
  list: (projectId: string, params?: { limit?: number; cursor?: string }) =>
    [...contextModuleKeys.lists(), projectId, params] as const,
  details: () => [...contextModuleKeys.all, 'detail'] as const,
  detail: (id: string) => [...contextModuleKeys.details(), id] as const,
  memories: (moduleId: string) => [...contextModuleKeys.detail(moduleId), 'memories'] as const,
};

// ============================================================================
// STALE TIME (interactive = 30 seconds)
// ============================================================================

const MODULE_STALE_TIME = 30 * 1000;

// ============================================================================
// QUERY HOOKS
// ============================================================================

export function useContextModules(
  projectId: string,
  params?: { limit?: number; cursor?: string }
) {
  return useQuery({
    queryKey: contextModuleKeys.list(projectId, params),
    queryFn: async (): Promise<ContextModuleListResponse> => {
      return fetchContextModules(projectId, params);
    },
    enabled: !!projectId,
    staleTime: MODULE_STALE_TIME,
  });
}

export function useContextModule(moduleId: string | undefined, includeItems?: boolean) {
  return useQuery({
    queryKey: contextModuleKeys.detail(moduleId!),
    queryFn: async (): Promise<ContextModuleResponse> => {
      return fetchContextModule(moduleId!, includeItems);
    },
    enabled: !!moduleId,
    staleTime: MODULE_STALE_TIME,
  });
}

export function useModuleMemories(moduleId: string | undefined, limit?: number) {
  return useQuery({
    queryKey: contextModuleKeys.memories(moduleId!),
    queryFn: async (): Promise<MemoryItemResponse[]> => {
      return fetchModuleMemories(moduleId!, limit);
    },
    enabled: !!moduleId,
    staleTime: MODULE_STALE_TIME,
  });
}

// ============================================================================
// MUTATION HOOKS
// ============================================================================

export function useCreateContextModule(
  options?: Pick<
    UseMutationOptions<
      ContextModuleResponse,
      Error,
      { projectId: string; data: ContextModuleCreateRequest }
    >,
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
      data: ContextModuleCreateRequest;
    }): Promise<ContextModuleResponse> => {
      return createContextModule(projectId, data);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.lists() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

export function useUpdateContextModule(
  options?: Pick<
    UseMutationOptions<
      ContextModuleResponse,
      Error,
      { moduleId: string; data: ContextModuleUpdateRequest }
    >,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      moduleId,
      data,
    }: {
      moduleId: string;
      data: ContextModuleUpdateRequest;
    }): Promise<ContextModuleResponse> => {
      return updateContextModule(moduleId, data);
    },
    onSuccess: (...args) => {
      const [, { moduleId }] = args;
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.detail(moduleId) });
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.lists() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

export function useDeleteContextModule(
  options?: Pick<UseMutationOptions<void, Error, string>, 'onSuccess' | 'onError'>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (moduleId: string): Promise<void> => {
      return deleteContextModule(moduleId);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.lists() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

export function useAddMemoryToModule(
  options?: Pick<
    UseMutationOptions<
      ContextModuleResponse,
      Error,
      { moduleId: string; data: AddMemoryToModuleRequest }
    >,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      moduleId,
      data,
    }: {
      moduleId: string;
      data: AddMemoryToModuleRequest;
    }): Promise<ContextModuleResponse> => {
      return addMemoryToModule(moduleId, data);
    },
    onSuccess: (...args) => {
      const [, { moduleId }] = args;
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.detail(moduleId) });
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.memories(moduleId) });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}

export function useRemoveMemoryFromModule(
  options?: Pick<
    UseMutationOptions<void, Error, { moduleId: string; memoryId: string }>,
    'onSuccess' | 'onError'
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      moduleId,
      memoryId,
    }: {
      moduleId: string;
      memoryId: string;
    }): Promise<void> => {
      return removeMemoryFromModule(moduleId, memoryId);
    },
    onSuccess: (...args) => {
      const [, { moduleId }] = args;
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.detail(moduleId) });
      queryClient.invalidateQueries({ queryKey: contextModuleKeys.memories(moduleId) });
      queryClient.invalidateQueries({ queryKey: memoryItemKeys.lists() });
      options?.onSuccess?.(...args);
    },
    onError: options?.onError,
  });
}
