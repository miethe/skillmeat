/**
 * React Query hook for artifact activity history (audit/provenance stream).
 *
 * Fetches from GET /api/v1/artifacts/activity — the raw append-only event log
 * written by ArtifactActivityService.  This is distinct from the merged
 * version-lineage timeline at /api/v1/artifacts/{id}/history.
 *
 * Uses useInfiniteQuery with cursor-based pagination.  Events are returned
 * newest-first (timestamp DESC, id DESC).
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import type { ActivityEvent } from '@/types/bom';
import { apiRequest } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseArtifactActivityHistoryOptions {
  /** Filter to events for a specific artifact (type:name format). */
  artifactId?: string;
  /** Filter by event type: create, update, delete, deploy, undeploy, sync. */
  eventType?: string;
  /** Filter by owner scope: user, team, enterprise. */
  ownerScope?: string;
  /** Filter by actor who triggered the event. */
  actorId?: string;
  /** Maximum events per page (1–200, default 50). */
  limit?: number;
  /** When false, the query will not execute. */
  enabled?: boolean;
}

interface ActivityPageInfo {
  endCursor: string | null;
  hasNextPage: boolean;
}

interface ActivityHistoryPage {
  items: ActivityEvent[];
  pageInfo: ActivityPageInfo;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const artifactActivityHistoryKeys = {
  all: ['artifact-activity-history'] as const,
  filtered: (filters: Omit<UseArtifactActivityHistoryOptions, 'enabled' | 'limit'>) =>
    [...artifactActivityHistoryKeys.all, filters] as const,
};

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

async function fetchArtifactActivityPage(
  options: UseArtifactActivityHistoryOptions,
  cursor: string | undefined
): Promise<ActivityHistoryPage> {
  const params = new URLSearchParams();

  if (options.artifactId) {
    params.set('artifact_id', options.artifactId);
  }
  if (options.eventType) {
    params.set('event_type', options.eventType);
  }
  if (options.ownerScope) {
    params.set('owner_scope', options.ownerScope);
  }
  if (options.actorId) {
    params.set('actor_id', options.actorId);
  }
  if (options.limit != null) {
    params.set('limit', String(options.limit));
  }
  if (cursor) {
    params.set('cursor', cursor);
  }

  const qs = params.toString();
  const path = qs ? `/artifacts/activity?${qs}` : '/artifacts/activity';

  return apiRequest<ActivityHistoryPage>(path);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Infinite-scroll hook for the artifact activity event stream.
 *
 * @example
 * ```tsx
 * const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
 *   useArtifactActivityHistory({ artifactId: 'skill:my-skill', limit: 20 });
 *
 * const events = data?.pages.flatMap((page) => page.items) ?? [];
 * ```
 */
export function useArtifactActivityHistory(
  options: UseArtifactActivityHistoryOptions = {}
) {
  const { enabled = true, limit, artifactId, eventType, ownerScope, actorId } = options;

  const filters = { artifactId, eventType, ownerScope, actorId };

  return useInfiniteQuery({
    queryKey: [...artifactActivityHistoryKeys.filtered(filters), limit],
    queryFn: ({ pageParam }) =>
      fetchArtifactActivityPage(options, pageParam as string | undefined),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: ActivityHistoryPage) =>
      lastPage.pageInfo.hasNextPage ? (lastPage.pageInfo.endCursor ?? undefined) : undefined,
    enabled: enabled,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}
