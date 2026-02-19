/**
 * React Query hook for fetching artifact association (composite membership) data.
 *
 * Provides data fetching, caching, and state management for parent/child
 * artifact relationships defined by the composite membership table.
 *
 * Endpoint: GET /api/v1/artifacts/{artifactId}/associations
 * Schema: skillmeat/api/schemas/associations.py
 */

import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { AssociationsDTO } from '@/types/associations';

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const associationKeys = {
  all: ['associations'] as const,
  detail: (artifactId: string) => [...associationKeys.all, artifactId] as const,
};

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

async function fetchArtifactAssociations(artifactId: string): Promise<AssociationsDTO> {
  return apiRequest<AssociationsDTO>(
    `/artifacts/${encodeURIComponent(artifactId)}/associations`
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Fetch the parent and child associations for a single artifact.
 *
 * @param artifactId - Artifact ID in "type:name" format (e.g. "composite:my-plugin")
 * @returns React Query result exposing `{ data, isLoading, error, refetch }`
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useArtifactAssociations('composite:my-plugin');
 *
 * if (isLoading) return <Spinner />;
 * if (error) return <ErrorBanner error={error} />;
 *
 * return (
 *   <>
 *     <ParentList parents={data.parents} />
 *     <ChildList children={data.children} />
 *   </>
 * );
 * ```
 */
export function useArtifactAssociations(artifactId: string) {
  return useQuery<AssociationsDTO, Error>({
    queryKey: associationKeys.detail(artifactId),
    queryFn: () => fetchArtifactAssociations(artifactId),
    enabled: !!artifactId,
    staleTime: 5 * 60 * 1000, // 5 minutes — standard browsing stale time per data-flow-patterns.md
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });
}
