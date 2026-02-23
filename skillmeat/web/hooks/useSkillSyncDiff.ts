/**
 * Hook for fetching per-member version comparison rows for a skill artifact.
 *
 * Calls GET /api/v1/artifacts/{artifactId}/sync-diff which returns a flat list
 * of VersionComparisonRow objects — one for the parent skill and one per member.
 *
 * Only enabled for skill artifacts that have a collection set.
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface VersionComparisonRow {
  /** Type:name artifact identifier */
  artifact_id: string;
  /** Short name portion of the artifact */
  artifact_name: string;
  /** Artifact type (e.g. "skill", "command") */
  artifact_type: string;
  /** Version resolved from upstream source; null when not tracked remotely */
  source_version: string | null;
  /** Version currently in collection; null when not in collection */
  collection_version: string | null;
  /** Version deployed to the project; null when not deployed */
  deployed_version: string | null;
  /** True for child/member rows, false for the parent skill row */
  is_member: boolean;
  /** type:name of the parent skill; null for the parent row itself */
  parent_artifact_id: string | null;
}

export interface UseSkillSyncDiffOptions {
  artifactId: string;
  collection?: string;
  projectId?: string;
  /** Only fire the query when true (e.g. after tab expansion) */
  enabled?: boolean;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const skillSyncDiffKeys = {
  all: ['skill-sync-diff'] as const,
  detail: (artifactId: string, collection?: string, projectId?: string) =>
    [...skillSyncDiffKeys.all, artifactId, collection, projectId] as const,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Fetch per-member version comparison rows for a skill artifact.
 *
 * @param options.artifactId  - Artifact ID in "type:name" format (e.g. "skill:my-skill")
 * @param options.collection  - Collection name (uses active collection if omitted)
 * @param options.projectId   - Project identifier for deployed_version resolution
 * @param options.enabled     - Whether to run the query (default: true)
 *
 * @returns React Query result exposing `{ data, isLoading, error, refetch }`
 *          where `data` is an ordered list: [parentRow, ...memberRows]
 */
export function useSkillSyncDiff({
  artifactId,
  collection,
  projectId,
  enabled = true,
}: UseSkillSyncDiffOptions) {
  return useQuery<VersionComparisonRow[], Error>({
    queryKey: skillSyncDiffKeys.detail(artifactId, collection, projectId),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (collection) params.set('collection', collection);
      if (projectId) params.set('project_id', projectId);
      const qs = params.toString();
      return apiRequest<VersionComparisonRow[]>(
        `/artifacts/${encodeURIComponent(artifactId)}/sync-diff${qs ? `?${qs}` : ''}`
      );
    },
    enabled: !!artifactId && enabled,
    staleTime: 30_000, // 30s — interactive/monitoring cadence (same as diff queries)
    gcTime: 300_000,   // 5 min
    retry: false,
  });
}
