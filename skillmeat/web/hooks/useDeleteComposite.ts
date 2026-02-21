/**
 * useDeleteComposite — mutation hook for DELETE /api/v1/composites/{id}.
 *
 * Deletes a composite artifact (and optionally its child Artifact rows) and
 * removes stale entries from the query cache.
 *
 * @example
 * ```tsx
 * const deleteComposite = useDeleteComposite();
 *
 * await deleteComposite.mutateAsync({
 *   compositeId: 'composite:my-plugin',
 *   collectionId: 'default',
 *   cascadeDeleteChildren: false,
 * });
 * ```
 */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { deleteComposite } from '@/lib/api/composites';
import { useToastNotification } from './use-toast-notification';
import { compositeKeys } from './useImportComposite';

// ---------------------------------------------------------------------------
// Mutation variable types
// ---------------------------------------------------------------------------

export interface DeleteCompositeVariables {
  compositeId: string;
  /** Owning collection — needed to invalidate the list cache. */
  collectionId: string;
  /**
   * When true, the backend also hard-deletes the child Artifact rows.
   * Defaults to false (only membership edges are removed).
   */
  cascadeDeleteChildren?: boolean;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Mutation hook for deleting a composite artifact.
 *
 * On success: removes the detail cache entry and invalidates the list cache.
 * On error: shows a toast with the server error detail.
 */
export function useDeleteComposite(): UseMutationResult<void, Error, DeleteCompositeVariables> {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation({
    mutationFn: ({ compositeId, cascadeDeleteChildren = false }) =>
      deleteComposite(compositeId, cascadeDeleteChildren),

    onSuccess: (_data, variables) => {
      const { compositeId, collectionId } = variables;

      // Remove the detail entry from cache immediately
      queryClient.removeQueries({ queryKey: compositeKeys.detail(compositeId) });

      // Invalidate the composites list so the collection view refreshes
      queryClient.invalidateQueries({
        queryKey: compositeKeys.list(collectionId),
      });

      // Also invalidate the root key in case any dashboards list all composites
      queryClient.invalidateQueries({
        queryKey: compositeKeys.all,
      });
    },

    onError: (error) => {
      showError(error, 'Failed to delete composite');
    },
  });
}
