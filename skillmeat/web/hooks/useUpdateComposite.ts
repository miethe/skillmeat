/**
 * useUpdateComposite — mutation hook for PUT /api/v1/composites/{id}.
 *
 * Updates mutable fields (display_name, description, composite_type) for an
 * existing composite and refreshes the relevant cached data.
 *
 * Implements optimistic updates: the cached composite detail is patched
 * immediately and rolled back if the server rejects the change.
 *
 * @example
 * ```tsx
 * const updateComposite = useUpdateComposite();
 *
 * await updateComposite.mutateAsync({
 *   compositeId: 'composite:my-plugin',
 *   collectionId: 'default',
 *   payload: { display_name: 'New Name', description: 'Updated desc.' },
 * });
 * ```
 */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import {
  updateComposite,
  type CompositeUpdatePayload,
  type CompositeResponse,
} from '@/lib/api/composites';
import { useToastNotification } from './use-toast-notification';
import { compositeKeys } from './useImportComposite';

// ---------------------------------------------------------------------------
// Mutation variable types
// ---------------------------------------------------------------------------

export interface UpdateCompositeVariables {
  compositeId: string;
  /** Owning collection — required to invalidate the list cache. */
  collectionId: string;
  payload: CompositeUpdatePayload;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Mutation hook for updating an existing composite artifact.
 *
 * Optimistic update: patches the detail cache immediately so the UI reflects
 * the change without waiting for the round-trip.  The previous value is stored
 * as the mutation context and restored on error.
 *
 * On success: invalidates the composites list for the collection.
 * On error: rolls back the optimistic update and shows a toast.
 */
export function useUpdateComposite(): UseMutationResult<
  CompositeResponse,
  Error,
  UpdateCompositeVariables,
  { previous: CompositeResponse | undefined }
> {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation({
    mutationFn: ({ compositeId, payload }) => updateComposite(compositeId, payload),

    // Optimistic update
    onMutate: async ({ compositeId, payload }) => {
      const detailKey = compositeKeys.detail(compositeId);

      // Cancel any in-flight refetches so they don't overwrite our optimistic value
      await queryClient.cancelQueries({ queryKey: detailKey });

      // Snapshot the previous value for rollback
      const previous = queryClient.getQueryData<CompositeResponse>(detailKey);

      // Apply optimistic patch
      if (previous) {
        queryClient.setQueryData<CompositeResponse>(detailKey, {
          ...previous,
          ...(payload.display_name !== undefined && { display_name: payload.display_name }),
          ...(payload.description !== undefined && { description: payload.description }),
          ...(payload.composite_type !== undefined && {
            composite_type: payload.composite_type ?? previous.composite_type,
          }),
        });
      }

      return { previous };
    },

    onSuccess: (data, variables) => {
      // Replace optimistic data with the authoritative server response
      queryClient.setQueryData(compositeKeys.detail(variables.compositeId), data);

      // Invalidate the list so the collection view refreshes
      queryClient.invalidateQueries({
        queryKey: compositeKeys.list(variables.collectionId),
      });
    },

    onError: (error, variables, context) => {
      // Roll back the optimistic update
      if (context?.previous) {
        queryClient.setQueryData(compositeKeys.detail(variables.compositeId), context.previous);
      }
      showError(error, 'Failed to update composite');
    },
  });
}
