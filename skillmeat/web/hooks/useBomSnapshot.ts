/**
 * React Query hook for fetching the BOM (Bill of Materials) snapshot.
 *
 * Fetches from GET /api/v1/bom/snapshot.
 * Returns the most recent point-in-time BOM snapshot for the caller's scope.
 * Snapshots are owner-scoped; the response reflects only artifacts visible
 * to the authenticated caller.
 *
 * Stale time: 5 minutes (standard browsing category — snapshot data changes
 * infrequently and is generated explicitly by the user).
 */

import { useQuery } from '@tanstack/react-query';
import type { BomSnapshot } from '@/types/bom';
import { apiRequest } from '@/lib/api';

// ---------------------------------------------------------------------------
// Response shape (mirrors BomSnapshotResponse from bom.py)
// ---------------------------------------------------------------------------

export interface BomSnapshotResponse {
  /** Auto-incrementing snapshot primary key. */
  id: number;
  /** Project scope for this snapshot, if any. */
  project_id?: string | null;
  /** Git commit SHA associated with this snapshot, if any. */
  commit_sha?: string | null;
  /** Owner context (user / team / enterprise). */
  owner_type: string;
  /** ISO-8601 UTC timestamp of snapshot creation. */
  created_at: string;
  /** Deserialized BOM document. */
  bom: BomSnapshot;
  /** Hex-encoded Ed25519 signature (present when include_signatures=true). */
  signature?: string | null;
  /** Signature algorithm identifier. */
  signature_algorithm?: string | null;
  /** SHA-256 fingerprint of the signing key. */
  signing_key_id?: string | null;
}

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------

export interface UseBomSnapshotOptions {
  /** Optional project scope filter. Omit for collection-level snapshot. */
  projectId?: string;
  /** Include memory-item artifact entries in the BOM. Default false. */
  includeMemoryItems?: boolean;
  /** Include Ed25519 signature fields. Default false. */
  includeSignatures?: boolean;
  /** When false, the query will not execute. Default true. */
  enabled?: boolean;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const bomSnapshotKeys = {
  all: ['bom-snapshot'] as const,
  snapshot: (options: Omit<UseBomSnapshotOptions, 'enabled'>) =>
    [...bomSnapshotKeys.all, options] as const,
};

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

async function fetchBomSnapshot(
  options: Omit<UseBomSnapshotOptions, 'enabled'>
): Promise<BomSnapshotResponse> {
  const params = new URLSearchParams();

  if (options.projectId) {
    params.set('project_id', options.projectId);
  }
  if (options.includeMemoryItems) {
    params.set('include_memory_items', 'true');
  }
  if (options.includeSignatures) {
    params.set('include_signatures', 'true');
  }

  const qs = params.toString();
  const path = qs ? `/bom/snapshot?${qs}` : '/bom/snapshot';

  return apiRequest<BomSnapshotResponse>(path);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Fetches the most recent BOM snapshot for the caller's owner scope.
 *
 * Returns 404 when no snapshot has been generated yet; callers should handle
 * the `isError` state and show an appropriate empty state.
 *
 * @example
 * ```tsx
 * const { data, isLoading, isError } = useBomSnapshot({ projectId: '/path/to/project' });
 *
 * if (isLoading) return <Skeleton />;
 * if (isError) return <BOMEmptyState />;
 * return <BOMSummaryCard data={data.bom} />;
 * ```
 */
export function useBomSnapshot(options: UseBomSnapshotOptions = {}) {
  const { enabled = true, projectId, includeMemoryItems, includeSignatures } = options;

  const queryOptions = { projectId, includeMemoryItems, includeSignatures };

  return useQuery({
    queryKey: bomSnapshotKeys.snapshot(queryOptions),
    queryFn: () => fetchBomSnapshot(queryOptions),
    enabled,
    staleTime: 5 * 60 * 1000,  // 5 minutes — standard browsing
    gcTime: 15 * 60 * 1000,    // 15 minutes
    retry: (failureCount, error) => {
      // Do not retry 404 — it means no snapshot exists yet
      if (error instanceof Error && error.message.includes('404')) return false;
      return failureCount < 2;
    },
  });
}
