/**
 * Custom hooks for custom color management using TanStack Query
 *
 * Provides data fetching, caching, and mutation state for user-defined custom
 * colors.  Uses the live API (/api/v1/colors) with proper cache invalidation.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchCustomColors,
  createCustomColor,
  updateCustomColor,
  deleteCustomColor,
  type ColorCreateRequest,
  type ColorUpdateRequest,
  type ColorResponse,
} from '@/lib/api/colors';

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

/**
 * Query key factory for type-safe color cache management
 */
export const colorKeys = {
  all: ['colors'] as const,
  lists: () => [...colorKeys.all, 'list'] as const,
  list: () => [...colorKeys.lists()] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch all user-defined custom colors
 *
 * @returns Query result with the list of custom colors
 *
 * @example
 * ```tsx
 * const { data: customColors, isLoading } = useCustomColors();
 * ```
 */
export function useCustomColors() {
  return useQuery({
    queryKey: colorKeys.list(),
    queryFn: fetchCustomColors,
    staleTime: 30 * 1000, // 30 seconds - interactive freshness
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Create a new custom color
 *
 * @returns Mutation function for creating a custom color
 *
 * @example
 * ```tsx
 * const createColor = useCreateCustomColor();
 * await createColor.mutateAsync({ hex: '#ff6b6b', name: 'Coral' });
 * ```
 */
export function useCreateCustomColor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ColorCreateRequest): Promise<ColorResponse> => createCustomColor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: colorKeys.all });
    },
  });
}

/**
 * Update an existing custom color
 *
 * @returns Mutation function for updating a custom color
 *
 * @example
 * ```tsx
 * const updateColor = useUpdateCustomColor();
 * await updateColor.mutateAsync({ id: 'color-123', data: { name: 'Salmon' } });
 * ```
 */
export function useUpdateCustomColor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ColorUpdateRequest }): Promise<ColorResponse> =>
      updateCustomColor(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: colorKeys.all });
    },
  });
}

/**
 * Delete a custom color
 *
 * @returns Mutation function for deleting a custom color
 *
 * @example
 * ```tsx
 * const deleteColor = useDeleteCustomColor();
 * await deleteColor.mutateAsync('color-123');
 * ```
 */
export function useDeleteCustomColor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string): Promise<void> => deleteCustomColor(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: colorKeys.all });
    },
  });
}
