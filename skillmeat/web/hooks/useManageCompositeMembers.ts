/**
 * useManageCompositeMembers — mutation hooks for composite member operations.
 *
 * Exports three focused hooks:
 *   - useAddCompositeMember    → POST   /api/v1/composites/{id}/members
 *   - useRemoveCompositeMember → DELETE /api/v1/composites/{id}/members/{uuid}
 *   - useReorderCompositeMembers → PATCH /api/v1/composites/{id}/members
 *
 * @example
 * ```tsx
 * const addMember    = useAddCompositeMember();
 * const removeMember = useRemoveCompositeMember();
 * const reorder      = useReorderCompositeMembers();
 *
 * // Add a member
 * await addMember.mutateAsync({
 *   compositeId: 'composite:my-plugin',
 *   collectionId: 'default',
 *   payload: { artifact_id: 'skill:canvas-design' },
 * });
 *
 * // Remove a member by UUID
 * await removeMember.mutateAsync({
 *   compositeId: 'composite:my-plugin',
 *   memberUuid: 'a1b2c3d4-…',
 * });
 *
 * // Reorder members
 * await reorder.mutateAsync({
 *   compositeId: 'composite:my-plugin',
 *   payload: {
 *     members: [
 *       { artifact_id: 'skill:canvas-design', position: 0 },
 *       { artifact_id: 'skill:code-review', position: 1 },
 *     ],
 *   },
 * });
 * ```
 */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import {
  addCompositeMember,
  removeCompositeMember,
  reorderCompositeMembers,
  type MembershipCreatePayload,
  type MembershipReorderPayload,
  type MembershipResponse,
  type CompositeResponse,
} from '@/lib/api/composites';
import { useToastNotification } from './use-toast-notification';
import { compositeKeys } from './useImportComposite';

// ---------------------------------------------------------------------------
// Variable types
// ---------------------------------------------------------------------------

export interface AddCompositeMemberVariables {
  compositeId: string;
  collectionId: string;
  payload: MembershipCreatePayload;
}

export interface RemoveCompositeMemberVariables {
  compositeId: string;
  /** Stable UUID of the child artifact (from MembershipResponse.child_artifact_uuid). */
  memberUuid: string;
}

export interface ReorderCompositeMembersVariables {
  compositeId: string;
  payload: MembershipReorderPayload;
}

// ---------------------------------------------------------------------------
// useAddCompositeMember
// ---------------------------------------------------------------------------

/**
 * Mutation hook for adding a child artifact to a composite.
 *
 * Invalidates the composite detail on success so the full membership list
 * (with accurate server-assigned UUIDs and positions) is refreshed.
 */
export function useAddCompositeMember(): UseMutationResult<
  MembershipResponse,
  Error,
  AddCompositeMemberVariables,
  { previous: CompositeResponse | undefined }
> {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation({
    mutationFn: ({ compositeId, collectionId, payload }) =>
      addCompositeMember(compositeId, collectionId, payload),

    onMutate: async ({ compositeId }) => {
      const detailKey = compositeKeys.detail(compositeId);
      await queryClient.cancelQueries({ queryKey: detailKey });
      const previous = queryClient.getQueryData<CompositeResponse>(detailKey);
      return { previous };
    },

    onSuccess: (_data, variables) => {
      // Refresh the detail to get accurate UUIDs and positions from the server
      queryClient.invalidateQueries({
        queryKey: compositeKeys.detail(variables.compositeId),
      });
      // Keep member_count in the list view in sync
      queryClient.invalidateQueries({
        queryKey: compositeKeys.list(variables.collectionId),
      });
    },

    onError: (error, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(compositeKeys.detail(variables.compositeId), context.previous);
      }
      showError(error, 'Failed to add member');
    },
  });
}

// ---------------------------------------------------------------------------
// useRemoveCompositeMember
// ---------------------------------------------------------------------------

/**
 * Mutation hook for removing a child artifact from a composite by UUID.
 *
 * Optimistic update: removes the membership from the detail cache immediately
 * and restores it if the server call fails.
 */
export function useRemoveCompositeMember(): UseMutationResult<
  void,
  Error,
  RemoveCompositeMemberVariables,
  { previous: CompositeResponse | undefined }
> {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation({
    mutationFn: ({ compositeId, memberUuid }) => removeCompositeMember(compositeId, memberUuid),

    onMutate: async ({ compositeId, memberUuid }) => {
      const detailKey = compositeKeys.detail(compositeId);
      await queryClient.cancelQueries({ queryKey: detailKey });
      const previous = queryClient.getQueryData<CompositeResponse>(detailKey);

      // Optimistically remove the membership from the detail cache
      if (previous) {
        const updatedMemberships = previous.memberships.filter(
          (m) => m.child_artifact_uuid !== memberUuid
        );
        queryClient.setQueryData<CompositeResponse>(detailKey, {
          ...previous,
          memberships: updatedMemberships,
          member_count: updatedMemberships.length,
        });
      }

      return { previous };
    },

    onSuccess: (_data, variables) => {
      // Confirm the removal — member_count must stay accurate
      queryClient.invalidateQueries({
        queryKey: compositeKeys.detail(variables.compositeId),
      });
      // Propagate the updated member_count to list views
      queryClient.invalidateQueries({
        queryKey: compositeKeys.all,
      });
    },

    onError: (error, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(compositeKeys.detail(variables.compositeId), context.previous);
      }
      showError(error, 'Failed to remove member');
    },
  });
}

// ---------------------------------------------------------------------------
// useReorderCompositeMembers
// ---------------------------------------------------------------------------

/**
 * Mutation hook for bulk-reordering members within a composite.
 *
 * Applies positions immediately in the detail cache (optimistic update) and
 * rolls back if the server rejects the change.
 */
export function useReorderCompositeMembers(): UseMutationResult<
  MembershipResponse[],
  Error,
  ReorderCompositeMembersVariables,
  { previous: CompositeResponse | undefined }
> {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation({
    mutationFn: ({ compositeId, payload }) => reorderCompositeMembers(compositeId, payload),

    onMutate: async ({ compositeId, payload }) => {
      const detailKey = compositeKeys.detail(compositeId);
      await queryClient.cancelQueries({ queryKey: detailKey });
      const previous = queryClient.getQueryData<CompositeResponse>(detailKey);

      // Optimistically apply the new positions
      if (previous) {
        const positionMap = new Map(payload.members.map((m) => [m.artifact_id, m.position]));

        const updatedMemberships = previous.memberships.map((m) => {
          const childId = m.child_artifact?.id;
          if (childId && positionMap.has(childId)) {
            return { ...m, position: positionMap.get(childId) ?? m.position };
          }
          return m;
        });

        // Sort ascending by position (nulls last)
        updatedMemberships.sort((a, b) => {
          if (a.position == null) return 1;
          if (b.position == null) return -1;
          return a.position - b.position;
        });

        queryClient.setQueryData<CompositeResponse>(detailKey, {
          ...previous,
          memberships: updatedMemberships,
        });
      }

      return { previous };
    },

    onSuccess: (updatedMemberships, variables) => {
      // Replace optimistic data with the server-authoritative response
      const detailKey = compositeKeys.detail(variables.compositeId);
      const current = queryClient.getQueryData<CompositeResponse>(detailKey);
      if (current) {
        queryClient.setQueryData<CompositeResponse>(detailKey, {
          ...current,
          memberships: updatedMemberships,
          member_count: updatedMemberships.length,
        });
      }
    },

    onError: (error, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(compositeKeys.detail(variables.compositeId), context.previous);
      }
      showError(error, 'Failed to reorder members');
    },
  });
}
