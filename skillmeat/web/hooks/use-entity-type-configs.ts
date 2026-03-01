/**
 * TanStack Query hooks for entity type configuration management.
 *
 * Provides data fetching, caching, and mutations for EntityTypeConfig resources,
 * which define the built-in and user-defined context entity types.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchEntityTypeConfigs,
  createEntityTypeConfig,
  updateEntityTypeConfig,
  deleteEntityTypeConfig,
} from '@/lib/api/context-entities';
import type { EntityTypeConfigCreate, EntityTypeConfigUpdate } from '@/types/context-entity';

/**
 * Query key factory for entity type config cache management
 */
export const entityTypeConfigKeys = {
  all: ['entity-type-configs'] as const,
  lists: () => [...entityTypeConfigKeys.all, 'list'] as const,
  list: () => [...entityTypeConfigKeys.lists()] as const,
};

/**
 * Fetch all entity type configurations.
 *
 * Standard 5 minute stale time (browsing category per data-flow-patterns).
 */
export function useEntityTypeConfigs() {
  return useQuery({
    queryKey: entityTypeConfigKeys.list(),
    queryFn: fetchEntityTypeConfigs,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Create a new entity type configuration.
 * Invalidates the entity-type-configs list on success.
 */
export function useCreateEntityTypeConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: EntityTypeConfigCreate) => createEntityTypeConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityTypeConfigKeys.all });
    },
  });
}

/**
 * Update an existing entity type configuration by slug.
 * Invalidates the entity-type-configs list on success.
 */
export function useUpdateEntityTypeConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ slug, data }: { slug: string; data: EntityTypeConfigUpdate }) =>
      updateEntityTypeConfig(slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityTypeConfigKeys.all });
    },
  });
}

/**
 * Delete an entity type configuration by slug.
 * Invalidates the entity-type-configs list on success.
 */
export function useDeleteEntityTypeConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => deleteEntityTypeConfig(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityTypeConfigKeys.all });
    },
  });
}
