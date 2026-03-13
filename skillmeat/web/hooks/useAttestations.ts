/**
 * React Query hooks for attestation records.
 *
 * useAttestations — infinite-scroll query for paginated attestation list.
 *   Fetches from GET /api/v1/attestations (list_attestations endpoint).
 *   Stale time: 30 seconds (interactive/monitoring — attestations are audit
 *   data that should reflect recent mutations quickly).
 *
 * useCreateAttestation — mutation for POST /api/v1/attestations.
 *   On success, invalidates attestation, BOM snapshot, and activity history
 *   query keys so all related UI refreshes automatically.
 */

import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Attestation } from '@/types/bom';
import { apiRequest } from '@/lib/api';
import { bomSnapshotKeys } from './useBomSnapshot';
import { artifactActivityHistoryKeys } from './useArtifactActivityHistory';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AttestationPageInfo {
  /** Opaque cursor pointing to the last item on this page. */
  end_cursor: string | null;
  /** True when more records exist after this page. */
  has_next_page: boolean;
}

export interface AttestationPage {
  items: Attestation[];
  page_info: AttestationPageInfo;
}

export interface UseAttestationsOptions {
  /** Filter by owner scope: 'user', 'team', or 'enterprise'. */
  ownerScope?: string;
  /** Filter by artifact identifier in 'type:name' format. */
  artifactId?: string;
  /** Maximum records per page (1–200). Default 50. */
  limit?: number;
  /** When false, the query will not execute. Default true. */
  enabled?: boolean;
}

export interface CreateAttestationRequest {
  /** Artifact identifier in 'type:name' format. */
  artifact_id: string;
  /** Owner scope override. When omitted the caller's principal type is used. */
  owner_scope?: string;
  /** RBAC roles to assert for this attestation. */
  roles?: string[];
  /** Permission scopes covered by this attestation. */
  scopes?: string[];
  /** Visibility policy: 'private', 'team', or 'public'. Default 'private'. */
  visibility?: string;
  /** Free-text notes for offline / manual attestation workflows. */
  notes?: string;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const attestationKeys = {
  all: ['attestations'] as const,
  lists: () => [...attestationKeys.all, 'list'] as const,
  list: (filters: Omit<UseAttestationsOptions, 'enabled' | 'limit'>) =>
    [...attestationKeys.lists(), filters] as const,
};

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

async function fetchAttestationPage(
  options: UseAttestationsOptions,
  cursor: string | undefined
): Promise<AttestationPage> {
  const params = new URLSearchParams();

  if (options.ownerScope) {
    params.set('owner_scope', options.ownerScope);
  }
  if (options.artifactId) {
    params.set('artifact_id', options.artifactId);
  }
  if (options.limit != null) {
    params.set('limit', String(options.limit));
  }
  if (cursor) {
    params.set('cursor', cursor);
  }

  const qs = params.toString();
  const path = qs ? `/attestations?${qs}` : '/attestations';

  return apiRequest<AttestationPage>(path);
}

// ---------------------------------------------------------------------------
// useAttestations — infinite query
// ---------------------------------------------------------------------------

/**
 * Cursor-paginated hook for the attestation record list.
 *
 * Supports filtering by owner_scope and artifact_id, with optional page size
 * control. Uses infinite query so callers can load more pages on demand.
 *
 * @example
 * ```tsx
 * const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
 *   useAttestations({ artifactId: 'skill:my-skill', limit: 20 });
 *
 * const attestations = data?.pages.flatMap((page) => page.items) ?? [];
 * ```
 */
export function useAttestations(options: UseAttestationsOptions = {}) {
  const { enabled = true, limit, ownerScope, artifactId } = options;

  const filters = { ownerScope, artifactId };

  return useInfiniteQuery({
    queryKey: [...attestationKeys.list(filters), limit],
    queryFn: ({ pageParam }) =>
      fetchAttestationPage(options, pageParam as string | undefined),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: AttestationPage) =>
      lastPage.page_info.has_next_page
        ? (lastPage.page_info.end_cursor ?? undefined)
        : undefined,
    enabled,
    staleTime: 30 * 1000,       // 30 seconds — interactive/monitoring
    gcTime: 5 * 60 * 1000,      // 5 minutes
  });
}

// ---------------------------------------------------------------------------
// useCreateAttestation — mutation
// ---------------------------------------------------------------------------

/**
 * Mutation hook to create a manual attestation record.
 *
 * Calls POST /api/v1/attestations. On success, invalidates:
 *   - All attestation list queries
 *   - BOM snapshot queries (attestation count may appear in BOM summary)
 *   - Artifact activity history queries (attestation creates an activity event)
 *
 * @example
 * ```tsx
 * const { mutateAsync: createAttestation, isPending } = useCreateAttestation();
 *
 * await createAttestation({
 *   artifact_id: 'skill:my-skill',
 *   visibility: 'private',
 *   roles: ['owner'],
 * });
 * ```
 */
export function useCreateAttestation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateAttestationRequest) =>
      apiRequest<Attestation>('/attestations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      }),
    onSuccess: () => {
      // Invalidate all attestation lists — new record affects all filter variants
      queryClient.invalidateQueries({ queryKey: attestationKeys.lists() });

      // Invalidate BOM snapshot — signing/attestation state may have changed
      queryClient.invalidateQueries({ queryKey: bomSnapshotKeys.all });

      // Invalidate activity history — attestation creation emits an activity event
      queryClient.invalidateQueries({ queryKey: artifactActivityHistoryKeys.all });
    },
  });
}
