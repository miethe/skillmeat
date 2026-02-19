/**
 * Mutation hooks for composite artifact import operations.
 *
 * Provides TanStack Query mutations for:
 *   - Importing a composite + its children atomically via POST /composites
 *   - Resolving per-member version conflicts via POST /composites/:id/members
 *
 * Architecture:
 *   - `useImportComposite`  — primary atomic import (creates composite + all members)
 *   - `useMutateCompositeMembers` — post-conflict mutation to add/overwrite individual members
 *   - `useResolveCompositeConflicts` — orchestrates conflict resolution after import fails 409
 *
 * Optimistic updates: composite list is optimistically updated with the new entry
 * and rolled back on failure. Individual member mutations are not optimistic (they
 * are applied after user interaction in the ConflictResolutionDialog).
 *
 * Stale times follow data-flow-patterns.md:
 *   - Standard browsing (composites list): 5 min
 *   - After mutation: invalidate composites + artifacts query keys
 *
 * Error handling:
 *   - All mutations display error toasts via `useToastNotification`
 *   - 409 Conflict responses surface the `conflicts` payload for the dialog
 *   - Network / server errors produce a generic error toast
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiRequest, ApiError } from '@/lib/api';
import { useToastNotification } from './use-toast-notification';
import type { ConflictResolution } from '@/components/deployment/conflict-resolution-dialog';

// ---------------------------------------------------------------------------
// Response / request shape mirrors skillmeat/api/schemas/composites.py
// ---------------------------------------------------------------------------

export interface MembershipResponse {
  collection_id: string;
  composite_id: string;
  child_artifact_uuid: string;
  relationship_type: string;
  pinned_version_hash: string | null;
  position: number | null;
  created_at: string;
  child_artifact: {
    id: string;
    uuid: string;
    name: string;
    type: string;
  } | null;
}

export interface CompositeImportResponse {
  id: string;
  collection_id: string;
  composite_type: string;
  display_name: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  memberships: MembershipResponse[];
  member_count: number;
}

/**
 * The 409 conflict body returned by the backend when a pinned hash for a
 * child artifact mismatches the currently-deployed version.
 *
 * Shape: { detail: "version_conflict", conflicts: VersionConflict[] }
 *
 * NOTE: The backend composites router does not yet emit this shape natively —
 * this type documents the expected future contract for when the import endpoint
 * performs hash validation. The ConflictResolutionDialog is ready to consume it.
 */
export interface ImportConflictError {
  detail: 'version_conflict';
  conflicts: ImportVersionConflict[];
}

export interface ImportVersionConflict {
  /** Child artifact name (type:name format) */
  artifactName: string;
  artifactType: string;
  /** Hash pinned by the composite definition */
  pinnedHash: string;
  /** Hash currently deployed in the project */
  currentHash: string;
  /** ISO 8601 timestamp when the conflict was detected */
  detectedAt: string;
}

/** Request body for POST /composites */
export interface CompositeImportRequest {
  composite_id: string;
  collection_id: string;
  composite_type?: 'plugin' | 'stack' | 'suite';
  display_name?: string;
  description?: string;
  /** Child artifact IDs in "type:name" format */
  initial_members?: string[];
  /** Optional hash to pin all initial members at */
  pinned_version_hash?: string | null;
}

/** Request body for POST /composites/:id/members */
export interface CompositeMemberAddRequest {
  artifact_id: string;
  relationship_type?: string;
  pinned_version_hash?: string | null;
  position?: number | null;
}

/**
 * Payload passed to `useResolveCompositeConflicts.mutate()`.
 * Maps each conflicting artifact name to the chosen resolution strategy.
 */
export interface ConflictResolutionPayload {
  compositeId: string;
  collectionId: string;
  /**
   * Resolution map from artifactName → ConflictResolution.
   * - `side-by-side`: install under a renamed alias (frontend keeps pinned hash, renames)
   * - `overwrite`: replace current deployment with the pinned hash
   */
  resolutions: Map<string, ConflictResolution>;
  /** Full list of conflicts (needed to look up pinnedHash per artifact) */
  conflicts: ImportVersionConflict[];
}

// ---------------------------------------------------------------------------
// Query key factories
// ---------------------------------------------------------------------------

export const compositeKeys = {
  all: ['composites'] as const,
  lists: () => [...compositeKeys.all, 'list'] as const,
  list: (collectionId: string) => [...compositeKeys.lists(), collectionId] as const,
  details: () => [...compositeKeys.all, 'detail'] as const,
  detail: (compositeId: string) => [...compositeKeys.details(), compositeId] as const,
  members: (compositeId: string) => [...compositeKeys.detail(compositeId), 'members'] as const,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Checks whether an ApiError response body matches the ImportConflictError shape.
 * Used to distinguish 409 version-conflict errors from other 409 responses.
 */
export function isVersionConflictError(err: unknown): err is ApiError & { body: ImportConflictError } {
  if (!(err instanceof ApiError)) return false;
  if (err.status !== 409) return false;
  // Cast through unknown to avoid TS overlap errors when comparing Record<string,unknown>
  // to the narrower ImportConflictError shape
  const body = err.body as unknown;
  if (body == null || typeof body !== 'object') return false;
  const bodyObj = body as Record<string, unknown>;
  return (
    bodyObj['detail'] === 'version_conflict' &&
    Array.isArray(bodyObj['conflicts'])
  );
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Fetch all composites for a collection.
 *
 * @param collectionId - Owning collection ID (e.g. "default")
 * @returns React Query result with `{ data: { items, total }, ... }`
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useComposites('default');
 * ```
 */
export function useComposites(collectionId: string) {
  return useQuery<{ items: CompositeImportResponse[]; total: number }, Error>({
    queryKey: compositeKeys.list(collectionId),
    queryFn: () =>
      apiRequest<{ items: CompositeImportResponse[]; total: number }>(
        `/composites?collection_id=${encodeURIComponent(collectionId)}`
      ),
    enabled: !!collectionId,
    staleTime: 5 * 60 * 1000, // 5 minutes — standard browsing per data-flow-patterns.md
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Atomically import a composite artifact and all its child members.
 *
 * Calls `POST /api/v1/composites` with the composite definition.
 * On success: invalidates composites list and artifacts query keys.
 * On 409 version-conflict: surfaces the conflict payload via `onConflict`.
 * On other errors: shows a toast notification.
 *
 * Optimistic update: inserts a placeholder composite entry into the list
 * cache and rolls back if the mutation fails.
 *
 * @param options.collectionId - Collection to scope optimistic cache update
 * @param options.onSuccess - Called with the created composite on success
 * @param options.onConflict - Called with conflict list when 409 is detected
 * @param options.onError - Called with error on non-conflict failure
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useImportComposite({
 *   collectionId: 'default',
 *   onSuccess: (composite) => console.log('Imported', composite.id),
 *   onConflict: (conflicts) => setConflictDialogOpen(true),
 * });
 *
 * mutate({
 *   composite_id: 'composite:my-plugin',
 *   collection_id: 'default',
 *   initial_members: ['skill:canvas-design', 'skill:code-review'],
 * });
 * ```
 */
export function useImportComposite({
  collectionId,
  onSuccess,
  onConflict,
  onError,
}: {
  collectionId: string;
  onSuccess?: (composite: CompositeImportResponse) => void;
  onConflict?: (conflicts: ImportVersionConflict[]) => void;
  onError?: (error: unknown) => void;
} = { collectionId: 'default' }) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToastNotification();

  return useMutation<CompositeImportResponse, unknown, CompositeImportRequest>({
    mutationFn: async (request) => {
      return apiRequest<CompositeImportResponse>('/composites', {
        method: 'POST',
        body: JSON.stringify(request),
      });
    },

    // Optimistic update: add a placeholder entry to the composites list cache.
    onMutate: async (request) => {
      const queryKey = compositeKeys.list(collectionId);

      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey });

      // Snapshot the previous list value for rollback
      const previousList = queryClient.getQueryData<{
        items: CompositeImportResponse[];
        total: number;
      }>(queryKey);

      // Optimistically insert the new composite as a pending entry
      const optimisticEntry: CompositeImportResponse = {
        id: request.composite_id,
        collection_id: request.collection_id,
        composite_type: request.composite_type ?? 'plugin',
        display_name: request.display_name ?? null,
        description: request.description ?? null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        memberships: [],
        member_count: request.initial_members?.length ?? 0,
      };

      if (previousList) {
        queryClient.setQueryData(queryKey, {
          items: [...previousList.items, optimisticEntry],
          total: previousList.total + 1,
        });
      }

      // Return context for rollback
      return { previousList, queryKey };
    },

    onSuccess: (composite) => {
      // Invalidate composites list and artifacts so all consumers refresh
      queryClient.invalidateQueries({ queryKey: compositeKeys.list(collectionId) });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['associations'] });

      // Seed the detail cache with the response
      queryClient.setQueryData(compositeKeys.detail(composite.id), composite);

      const displayName = composite.display_name ?? composite.id;
      showSuccess(
        'Composite imported',
        `${displayName} and ${composite.member_count} member${composite.member_count !== 1 ? 's' : ''} added to collection.`
      );
      onSuccess?.(composite);
    },

    onError: (error, _variables, context) => {
      // Roll back the optimistic update on any failure
      if (context != null && typeof context === 'object') {
        const ctx = context as { previousList?: unknown; queryKey?: readonly unknown[] };
        if (ctx.queryKey && ctx.previousList !== undefined) {
          queryClient.setQueryData(ctx.queryKey, ctx.previousList);
        }
      }

      // Surface conflict errors to the dialog; show toast for everything else
      if (isVersionConflictError(error)) {
        onConflict?.((error.body as ImportConflictError).conflicts);
        return;
      }

      showError(error, 'Failed to import composite');
      onError?.(error);
    },
  });
}

/**
 * Add or overwrite a single child artifact membership on an existing composite.
 *
 * Used after conflict resolution to apply the user's chosen strategy:
 *   - `side-by-side`: calls POST /composites/:id/members with the pinned hash
 *   - `overwrite`:    calls POST /composites/:id/members without a pinned hash
 *                     (backend will overwrite the existing deployment)
 *
 * On success: invalidates composites detail and artifacts query keys.
 * On error: shows a toast notification.
 *
 * @example
 * ```tsx
 * const { mutate } = useMutateCompositeMembers('composite:my-plugin', 'default');
 * mutate({ artifact_id: 'skill:canvas-design', pinned_version_hash: 'abc123' });
 * ```
 */
export function useMutateCompositeMembers(compositeId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { showError } = useToastNotification();

  return useMutation<MembershipResponse, unknown, CompositeMemberAddRequest>({
    mutationFn: async (request) => {
      return apiRequest<MembershipResponse>(
        `/composites/${encodeURIComponent(compositeId)}/members?collection_id=${encodeURIComponent(collectionId)}`,
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      );
    },

    onSuccess: () => {
      // Refresh composite detail + the artifacts index
      queryClient.invalidateQueries({ queryKey: compositeKeys.detail(compositeId) });
      queryClient.invalidateQueries({ queryKey: compositeKeys.list(collectionId) });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['associations'] });
    },

    onError: (error) => {
      showError(error, 'Failed to update composite member');
    },
  });
}

/**
 * Orchestrate resolution of version conflicts detected during composite import.
 *
 * Accepts the Map<artifactName, resolution> produced by `ConflictResolutionDialog.onResolve`
 * and applies each resolution by calling `POST /composites/:id/members` for each
 * conflicting artifact.
 *
 * Resolution semantics:
 *   - `side-by-side`: pass `pinned_version_hash` — backend stores the pinned version
 *     under a composite-scoped alias without disturbing the global deployment.
 *   - `overwrite`: pass `pinned_version_hash: null` — backend replaces the current
 *     deployment hash with the composite's pinned hash.
 *
 * All member mutations are sent in parallel. A single failed resolution shows an error
 * toast but does not cancel the remaining resolutions.
 *
 * On full success: invalidates composites + artifacts caches and calls `onSuccess`.
 * On partial/full failure: calls `onError` with the collected errors.
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useResolveCompositeConflicts({
 *   onSuccess: () => toast.success('All conflicts resolved'),
 *   onError: (errs) => console.error(errs),
 * });
 *
 * // Called from ConflictResolutionDialog.onResolve
 * mutate({
 *   compositeId: 'composite:my-plugin',
 *   collectionId: 'default',
 *   resolutions: new Map([['canvas-design', 'overwrite'], ['code-review', 'side-by-side']]),
 *   conflicts: [...],
 * });
 * ```
 */
export function useResolveCompositeConflicts({
  onSuccess,
  onError,
}: {
  onSuccess?: () => void;
  onError?: (errors: unknown[]) => void;
} = {}) {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToastNotification();

  return useMutation<void, unknown, ConflictResolutionPayload>({
    mutationFn: async ({ compositeId, collectionId, resolutions, conflicts }) => {
      const memberEndpoint = `/composites/${encodeURIComponent(compositeId)}/members?collection_id=${encodeURIComponent(collectionId)}`;

      const errors: unknown[] = [];

      // Run all resolutions in parallel; collect errors rather than aborting
      await Promise.allSettled(
        conflicts
          .filter((c) => resolutions.has(c.artifactName))
          .map(async (conflict) => {
            const strategy = resolutions.get(conflict.artifactName)!;

            // For side-by-side: keep the pinned hash (installs alongside current).
            // For overwrite: null hash signals backend to apply the pinned version globally.
            const pinned_version_hash =
              strategy === 'side-by-side' ? conflict.pinnedHash : null;

            try {
              await apiRequest<MembershipResponse>(memberEndpoint, {
                method: 'POST',
                body: JSON.stringify({
                  artifact_id: conflict.artifactName,
                  pinned_version_hash,
                  relationship_type: 'contains',
                } satisfies CompositeMemberAddRequest),
              });
            } catch (err) {
              errors.push(err);
            }
          })
      );

      if (errors.length > 0) {
        // Surface partial failures — caller can inspect `onError`
        throw errors;
      }
    },

    onSuccess: (_data, { compositeId, collectionId }) => {
      queryClient.invalidateQueries({ queryKey: compositeKeys.detail(compositeId) });
      queryClient.invalidateQueries({ queryKey: compositeKeys.list(collectionId) });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['associations'] });

      showSuccess('Conflicts resolved', 'All version conflicts have been resolved successfully.');
      onSuccess?.();
    },

    onError: (errors) => {
      // errors is the thrown array from the mutationFn
      const errorList = Array.isArray(errors) ? errors : [errors];
      const firstErr = errorList[0];
      showError(firstErr, `Failed to resolve ${errorList.length} conflict${errorList.length !== 1 ? 's' : ''}`);
      onError?.(errorList);
    },
  });
}
