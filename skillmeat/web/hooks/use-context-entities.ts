/**
 * Custom hooks for context entity management using TanStack Query
 *
 * Provides data fetching, caching, and state management for context entities.
 * Context entities are artifacts with special roles in Claude Code projects
 * (configs, specs, rules, context files, progress templates).
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchContextEntities,
  fetchContextEntity,
  createContextEntity,
  updateContextEntity,
  deleteContextEntity,
  fetchContextEntityContent,
  deployContextEntity,
} from '@/lib/api/context-entities';
import type {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityFilters,
  ContextEntityListResponse,
  ContextEntityDeployRequest,
  ContextEntityDeployResponse,
} from '@/types/context-entity';

/**
 * Query keys factory for type-safe cache management
 */
export const contextEntityKeys = {
  all: ['context-entities'] as const,
  lists: () => [...contextEntityKeys.all, 'list'] as const,
  list: (filters?: ContextEntityFilters) => [...contextEntityKeys.lists(), filters] as const,
  details: () => [...contextEntityKeys.all, 'detail'] as const,
  detail: (id: string) => [...contextEntityKeys.details(), id] as const,
  content: (id: string) => [...contextEntityKeys.detail(id), 'content'] as const,
};

/**
 * Fetch context entities with optional filtering and pagination
 *
 * @param filters - Optional filters for entity type, category, auto-load, search, and pagination
 * @returns Query result with context entities array
 *
 * @example
 * ```tsx
 * // Fetch all context entities
 * const { data, isLoading, error } = useContextEntities();
 *
 * // Filter by entity type
 * const { data: ruleFiles } = useContextEntities({
 *   entity_type: 'rule_file',
 *   limit: 20
 * });
 *
 * // Search by name/description
 * const { data: results } = useContextEntities({
 *   search: 'api patterns',
 *   category: 'backend'
 * });
 * ```
 */
export function useContextEntities(filters?: ContextEntityFilters) {
  return useQuery({
    queryKey: contextEntityKeys.list(filters),
    queryFn: async (): Promise<ContextEntityListResponse> => {
      return fetchContextEntities(filters);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch single context entity by ID
 *
 * @param id - Context entity ID (undefined will disable the query)
 * @returns Query result with context entity details
 *
 * @example
 * ```tsx
 * const { data: entity } = useContextEntity(entityId);
 * if (entity) {
 *   console.log(`Entity type: ${entity.entity_type}`);
 *   console.log(`Path pattern: ${entity.path_pattern}`);
 * }
 * ```
 */
export function useContextEntity(id: string | undefined) {
  return useQuery({
    queryKey: contextEntityKeys.detail(id!),
    queryFn: async (): Promise<ContextEntity> => {
      return fetchContextEntity(id!);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch raw markdown content for a context entity
 *
 * @param id - Context entity ID (undefined will disable the query)
 * @returns Query result with markdown content as string
 *
 * @example
 * ```tsx
 * const { data: markdown } = useContextEntityContent(entityId);
 * if (markdown) {
 *   console.log('Content length:', markdown.length);
 *   // Render markdown content
 *   return <MarkdownViewer content={markdown} />;
 * }
 * ```
 */
export function useContextEntityContent(id: string | undefined) {
  return useQuery({
    queryKey: contextEntityKeys.content(id!),
    queryFn: async (): Promise<string> => {
      return fetchContextEntityContent(id!);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Create new context entity mutation
 *
 * @returns Mutation function for creating context entities
 *
 * @example
 * ```tsx
 * const createEntity = useCreateContextEntity();
 *
 * await createEntity.mutateAsync({
 *   name: 'API Patterns',
 *   entity_type: 'rule_file',
 *   content: '# API Patterns\n\nFollow these patterns...',
 *   path_pattern: '.claude/rules/api/patterns.md',
 *   category: 'backend',
 *   auto_load: true
 * });
 * ```
 */
export function useCreateContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateContextEntityRequest): Promise<ContextEntity> => {
      return createContextEntity(data);
    },
    onSuccess: () => {
      // Invalidate context entities list to trigger refetch
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.lists() });
    },
  });
}

/**
 * Update existing context entity mutation
 *
 * @returns Mutation function for updating context entities
 *
 * @example
 * ```tsx
 * const updateEntity = useUpdateContextEntity();
 *
 * await updateEntity.mutateAsync({
 *   id: 'entity-id',
 *   data: {
 *     name: 'Updated Name',
 *     content: '# Updated content...',
 *     auto_load: false
 *   }
 * });
 * ```
 */
export function useUpdateContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: UpdateContextEntityRequest;
    }): Promise<ContextEntity> => {
      return updateContextEntity(id, data);
    },
    onSuccess: (_, { id }) => {
      // Invalidate both the specific entity and the list
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.lists() });
      // Also invalidate content cache since content may have changed
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.content(id) });
    },
  });
}

/**
 * Delete context entity mutation
 *
 * @returns Mutation function for deleting context entities
 *
 * @example
 * ```tsx
 * const deleteEntity = useDeleteContextEntity();
 *
 * await deleteEntity.mutateAsync('entity-id');
 * ```
 */
export function useDeleteContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      return deleteContextEntity(id);
    },
    onSuccess: () => {
      // Invalidate context entities list to remove deleted item
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.lists() });
    },
  });
}

/**
 * Deploy context entity mutation
 *
 * @returns Mutation function for deploying context entities
 *
 * @example
 * ```tsx
 * const deployEntity = useDeployContextEntity();
 *
 * await deployEntity.mutateAsync({ id: 'entity-id', projectPath: '/path/to/project' });
 * ```
 */
export function useDeployContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: ContextEntityDeployRequest;
    }): Promise<ContextEntityDeployResponse> => deployContextEntity(id, data),
    onSuccess: () => {
      // Invalidate context entities lists to reflect changes if any (e.g. usage stats)
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.lists() });
      // Also invalidate deployments list if we have one
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
    },
  });
}
