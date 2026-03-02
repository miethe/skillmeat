/**
 * TanStack Query hooks for entity category management.
 *
 * Provides data fetching and mutation for ContextEntityCategory resources,
 * which are used for multi-select categorisation in the context entity editor.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchEntityCategories,
  createEntityCategory,
  updateEntityCategory,
  deleteEntityCategory,
  type EntityCategory,
  type EntityCategoryFilters,
  type EntityCategoryCreateRequest,
  type EntityCategoryUpdateRequest,
} from '@/lib/api/context-entities';

// Re-export types for consumers
export type { EntityCategory, EntityCategoryCreateRequest, EntityCategoryUpdateRequest };

/**
 * Query key factory for entity category cache management.
 */
export const entityCategoryKeys = {
  all: ['entity-categories'] as const,
  lists: () => [...entityCategoryKeys.all, 'list'] as const,
  list: (filters?: EntityCategoryFilters) =>
    [...entityCategoryKeys.lists(), filters ?? {}] as const,
};

/**
 * Fetch all entity categories, optionally filtered by entity type slug or platform.
 *
 * Uses 5 minute stale time (standard browsing category per data-flow-patterns).
 */
export function useEntityCategories(filters?: EntityCategoryFilters) {
  return useQuery({
    queryKey: entityCategoryKeys.list(filters),
    queryFn: () => fetchEntityCategories(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Create a new entity category.
 *
 * Invalidates the categories list on success so the combobox immediately
 * reflects newly created categories.
 */
export function useCreateEntityCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: EntityCategoryCreateRequest) => createEntityCategory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityCategoryKeys.all });
    },
  });
}

/**
 * Update an existing entity category by slug.
 * Invalidates the categories list on success.
 */
export function useUpdateEntityCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ slug, data }: { slug: string; data: EntityCategoryUpdateRequest }) =>
      updateEntityCategory(slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityCategoryKeys.all });
    },
  });
}

/**
 * Delete an entity category by slug.
 * Invalidates the categories list on success.
 */
export function useDeleteEntityCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => deleteEntityCategory(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityCategoryKeys.all });
    },
  });
}
