/**
 * React Query hook for fetching similar artifacts.
 *
 * Calls GET /api/v1/artifacts/{id}/similar and returns a ranked list of
 * artifacts that share content, structure, metadata, or semantic similarity
 * with the queried artifact.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useSimilarArtifacts(artifact.uuid, {
 *   limit: 10,
 *   minScore: 0.5,
 *   source: 'collection',
 * });
 *
 * if (isLoading) return <Spinner />;
 * return data?.items.map(item => <SimilarArtifactCard key={item.artifact_id} {...item} />);
 * ```
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type {
  SimilarArtifactsResponse,
  SimilarArtifactsOptions,
  SimilaritySource,
} from '@/types/similarity';

// ============================================================================
// Query Keys Factory
// ============================================================================

export const similarArtifactKeys = {
  all: ['similar-artifacts'] as const,
  lists: () => [...similarArtifactKeys.all, 'list'] as const,
  list: (
    artifactId: string,
    limit?: number,
    minScore?: number,
    source?: SimilaritySource
  ) => [...similarArtifactKeys.lists(), artifactId, limit, minScore, source] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function fetchSimilarArtifacts(
  artifactId: string,
  options: Required<Omit<SimilarArtifactsOptions, 'enabled'>>
): Promise<SimilarArtifactsResponse> {
  const params = new URLSearchParams();

  params.append('limit', String(options.limit));

  if (options.minScore !== undefined) {
    params.append('min_score', String(options.minScore));
  }

  if (options.source !== undefined) {
    params.append('source', options.source);
  }

  return apiRequest<SimilarArtifactsResponse>(
    `/artifacts/${encodeURIComponent(artifactId)}/similar?${params.toString()}`
  );
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Fetch similar artifacts for a given artifact ID.
 *
 * The query is disabled when `artifactId` is undefined or empty. Pass
 * `options.enabled = false` to suppress the query even when an ID is present.
 *
 * Query param mapping:
 *   options.minScore  → min_score  (snake_case in API)
 *   options.source    → source
 *   options.limit     → limit
 *
 * Stale time: 5 minutes (browsing tier per data-flow-patterns).
 */
export function useSimilarArtifacts(
  artifactId: string | undefined,
  options: SimilarArtifactsOptions = {}
) {
  const { limit = 10, minScore, source, enabled } = options;

  return useQuery({
    queryKey: similarArtifactKeys.list(artifactId ?? '', limit, minScore, source),
    queryFn: () =>
      fetchSimilarArtifacts(artifactId!, {
        limit,
        minScore: minScore as number,
        source: source as SimilaritySource,
      }),
    enabled: !!artifactId && enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes — browsing tier
  });
}
