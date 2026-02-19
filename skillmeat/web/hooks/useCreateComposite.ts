/**
 * useCreateComposite — mutation hook for POST /api/v1/composites.
 *
 * Creates a new composite artifact and invalidates the composites list cache
 * for the owning collection.
 *
 * @example
 * ```tsx
 * const createComposite = useCreateComposite();
 *
 * await createComposite.mutateAsync({
 *   composite_id: 'composite:my-plugin',
 *   collection_id: 'default',
 *   composite_type: 'plugin',
 *   display_name: 'My Plugin',
 *   description: 'Groups canvas and code-review skills.',
 *   initial_members: ['skill:canvas-design', 'skill:code-review'],
 * });
 * ```
 */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import {
  createComposite,
  type CompositeCreatePayload,
  type CompositeResponse,
} from '@/lib/api/composites';
import { useToastNotification } from './use-toast-notification';
import { compositeKeys } from './useImportComposite';

/**
 * Mutation hook for creating a new composite artifact.
 *
 * On success: invalidates composites list for the collection.
 * On error: shows a toast with the server error detail.
 */
export function useCreateComposite(): UseMutationResult<
  CompositeResponse,
  Error,
  CompositeCreatePayload
> {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation({
    mutationFn: createComposite,
    onSuccess: (_data, variables) => {
      // Invalidate the composites list for the owning collection
      queryClient.invalidateQueries({
        queryKey: compositeKeys.list(variables.collection_id),
      });
      // Invalidate the all-composites root key (e.g. dashboards)
      queryClient.invalidateQueries({
        queryKey: compositeKeys.all,
      });
    },
    onError: (error) => {
      showError(error, 'Failed to create composite');
    },
  });
}
