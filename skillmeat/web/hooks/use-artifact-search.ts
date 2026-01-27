/**
 * React Query hook for cross-source artifact search
 *
 * Provides FTS5-powered search across all marketplace catalog entries
 * with debounced input and pagination support.
 *
 * @example
 * ```tsx
 * const { query, setQuery, data, isLoading, error } = useArtifactSearch();
 *
 * return (
 *   <input value={query} onChange={(e) => setQuery(e.target.value)} />
 *   {data?.items.map(item => <ResultCard key={item.id} {...item} />)}
 * );
 * ```
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from '@/hooks';
import { apiRequest } from '@/lib/api';

// ============================================================================
// Types
// ============================================================================

export interface ArtifactSearchParams {
  query: string;
  type?: string; // artifact type filter
  minConfidence?: number;
  tags?: string[];
  limit?: number;
}

export interface ArtifactSearchResult {
  id: string;
  name: string;
  artifact_type: string;
  path: string;
  confidence_score: number;
  status: string;
  title?: string;
  description?: string;
  search_tags?: string[];
  title_snippet?: string; // FTS5 highlight snippet for title
  description_snippet?: string; // FTS5 highlight snippet for description
  source_id: string;
  source_owner: string;
  source_repo: string;
  upstream_url?: string;
  deep_match?: boolean;
  matched_file?: string;
}

export interface ArtifactSearchResponse {
  items: ArtifactSearchResult[];
  page_info: {
    has_next: boolean;
    cursor?: string;
  };
}

// ============================================================================
// Query Keys Factory
// ============================================================================

export const artifactSearchKeys = {
  all: ['artifact-search'] as const,
  searches: () => [...artifactSearchKeys.all, 'search'] as const,
  search: (params: ArtifactSearchParams) => [...artifactSearchKeys.searches(), params] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function searchArtifacts(params: ArtifactSearchParams): Promise<ArtifactSearchResponse> {
  const searchParams = new URLSearchParams();

  searchParams.append('q', params.query);

  if (params.type) {
    searchParams.append('type', params.type);
  }

  if (params.minConfidence !== undefined) {
    searchParams.append('min_confidence', params.minConfidence.toString());
  }

  if (params.tags && params.tags.length > 0) {
    params.tags.forEach((tag) => searchParams.append('tags', tag));
  }

  if (params.limit !== undefined) {
    searchParams.append('limit', params.limit.toString());
  }

  return apiRequest<ArtifactSearchResponse>(`/marketplace/catalog/search?${searchParams}`);
}

// ============================================================================
// Hooks
// ============================================================================

export interface UseArtifactSearchOptions {
  /** Artifact type filter */
  type?: string;
  /** Minimum confidence score filter */
  minConfidence?: number;
  /** Tags to filter by */
  tags?: string[];
  /** Maximum results per page */
  limit?: number;
  /** Debounce delay in milliseconds (default: 300) */
  debounceMs?: number;
  /** Minimum query length to trigger search (default: 2) */
  minQueryLength?: number;
}

export interface UseArtifactSearchReturn {
  /** Current query input value */
  query: string;
  /** Update the query input value */
  setQuery: (query: string) => void;
  /** Debounced query value used for API calls */
  debouncedQuery: string;
  /** Search results */
  data: ArtifactSearchResponse | undefined;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: Error | null;
  /** Whether the query is being fetched */
  isFetching: boolean;
  /** Whether the query has been fetched successfully */
  isSuccess: boolean;
  /** Refetch the search results */
  refetch: () => void;
}

/**
 * Search artifacts across all marketplace sources with FTS5
 *
 * Automatically debounces input and only triggers search when
 * query length meets minimum threshold.
 */
export function useArtifactSearch(options: UseArtifactSearchOptions = {}): UseArtifactSearchReturn {
  const {
    type,
    minConfidence,
    tags,
    limit,
    debounceMs = 300,
    minQueryLength = 2,
  } = options;

  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, debounceMs);

  const searchParams: ArtifactSearchParams = {
    query: debouncedQuery,
    type,
    minConfidence,
    tags,
    limit,
  };

  const queryResult = useQuery({
    queryKey: artifactSearchKeys.search(searchParams),
    queryFn: () => searchArtifacts(searchParams),
    enabled: debouncedQuery.length >= minQueryLength,
    staleTime: 30000, // 30 seconds
  });

  return {
    query,
    setQuery,
    debouncedQuery,
    data: queryResult.data,
    isLoading: queryResult.isLoading,
    error: queryResult.error,
    isFetching: queryResult.isFetching,
    isSuccess: queryResult.isSuccess,
    refetch: queryResult.refetch,
  };
}
