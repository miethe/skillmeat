/**
 * Entity Picker Adapter Hooks
 *
 * Thin adapters that wrap domain hooks (useInfiniteArtifacts, useContextModules)
 * and normalize their return values into the uniform InfiniteDataResult<T> shape
 * expected by EntityPickerDialog.
 *
 * UEPD-1.3: useEntityPickerArtifacts
 * UEPD-2.2: useEntityPickerContextModules
 */

import { useMemo } from 'react';
import { useInfiniteArtifacts } from '@/hooks';
import { useContextModules } from '@/hooks';
import { mapApiResponseToArtifact } from '@/lib/api/mappers';
import type { Artifact } from '@/types/artifact';
import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';

// ============================================================================
// SHARED RESULT SHAPE
// ============================================================================

/**
 * Uniform result interface returned by all entity picker adapter hooks.
 * Matches the data contract expected by EntityPickerDialog.
 */
export interface InfiniteDataResult<T> {
  items: T[];
  isLoading: boolean;
  hasNextPage: boolean;
  fetchNextPage: () => void;
  isFetchingNextPage: boolean;
}

// ============================================================================
// UEPD-1.3: Artifact Adapter
// ============================================================================

export interface UseEntityPickerArtifactsParams {
  search: string;
  typeFilter?: string[];
}

/**
 * Adapter hook for artifact entity picker.
 *
 * Wraps useInfiniteArtifacts and normalizes it to InfiniteDataResult<Artifact>.
 * Passes search server-side; joins typeFilter array into comma-separated string
 * as required by the artifact_type param.
 */
export function useEntityPickerArtifacts(
  params: UseEntityPickerArtifactsParams
): InfiniteDataResult<Artifact> {
  const { search, typeFilter } = params;

  const artifactTypeParam = typeFilter && typeFilter.length > 0 ? typeFilter.join(',') : undefined;

  const query = useInfiniteArtifacts({
    search: search || undefined,
    artifact_type: artifactTypeParam,
    limit: 30,
  });

  const items = useMemo<Artifact[]>(() => {
    if (!query.data?.pages) return [];
    return query.data.pages.flatMap((page) =>
      page.items.map((item) => mapApiResponseToArtifact(item, 'collection'))
    );
  }, [query.data]);

  return {
    items,
    isLoading: query.isLoading,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
  };
}

// ============================================================================
// UEPD-2.2: Context Module Adapter
// ============================================================================

export interface UseEntityPickerContextModulesParams {
  search: string;
  typeFilter?: string[];
  /** Project ID required to scope context module queries. Query is disabled when absent. */
  projectId?: string;
}

/**
 * Adapter hook for context module entity picker.
 *
 * Wraps useContextModules (non-paginated) and normalizes it to
 * InfiniteDataResult<ContextModuleResponse> with a single-page shape.
 * Search and typeFilter are applied client-side since the API does not
 * support server-side filtering for context modules.
 *
 * hasNextPage is always false; fetchNextPage is a no-op.
 */
export function useEntityPickerContextModules(
  params: UseEntityPickerContextModulesParams
): InfiniteDataResult<ContextModuleResponse> {
  const { search, projectId } = params;

  const query = useContextModules(projectId ?? '', { limit: 100 });

  const items = useMemo<ContextModuleResponse[]>(() => {
    const raw = query.data?.items ?? [];
    if (!search) return raw;

    const searchLower = search.toLowerCase();
    return raw.filter(
      (m) =>
        m.name.toLowerCase().includes(searchLower) ||
        (m.description ?? '').toLowerCase().includes(searchLower)
    );
  }, [query.data, search]);

  return {
    items,
    isLoading: query.isLoading,
    hasNextPage: false,
    fetchNextPage: () => {},
    isFetchingNextPage: false,
  };
}
