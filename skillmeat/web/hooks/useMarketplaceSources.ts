/**
 * React Query hooks for GitHub marketplace sources
 *
 * These hooks provide data fetching, caching, and mutations for
 * GitHub source management, catalog browsing, and artifact import.
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { useToast } from './use-toast';
import { apiRequest } from '@/lib/api';
import { inferUrl } from '@/lib/api/marketplace';
import type {
  GitHubSource,
  GitHubSourceListResponse,
  CreateSourceRequest,
  UpdateSourceRequest,
  CatalogEntry,
  CatalogListResponse,
  CatalogFilters,
  ScanRequest,
  ScanResult,
  ImportRequest,
  ImportResult,
  UpdateCatalogEntryNameRequest,
} from '@/types/marketplace';

// Query keys factory
export const sourceKeys = {
  all: ['marketplace-sources'] as const,
  lists: () => [...sourceKeys.all, 'list'] as const,
  list: (cursor?: string) => [...sourceKeys.lists(), cursor] as const,
  details: () => [...sourceKeys.all, 'detail'] as const,
  detail: (id: string) => [...sourceKeys.details(), id] as const,
  catalogs: () => [...sourceKeys.all, 'catalog'] as const,
  catalog: (id: string, filters?: CatalogFilters, limit?: number) =>
    [...sourceKeys.catalogs(), id, filters, limit] as const,
};

// ============================================================================
// Sources CRUD
// ============================================================================

/**
 * Fetch all GitHub sources with infinite scroll pagination
 */
export function useSources(limit = 50) {
  return useInfiniteQuery({
    queryKey: sourceKeys.lists(),
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams();
      if (pageParam) params.append('cursor', pageParam);
      params.append('limit', limit.toString());
      return apiRequest<GitHubSourceListResponse>(`/marketplace/sources?${params}`);
    },
    getNextPageParam: (lastPage) =>
      lastPage.page_info.has_next_page ? lastPage.page_info.end_cursor : undefined,
    initialPageParam: undefined as string | undefined,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Fetch single source by ID
 */
export function useSource(sourceId: string) {
  return useQuery({
    queryKey: sourceKeys.detail(sourceId),
    queryFn: () => apiRequest<GitHubSource>(`/marketplace/sources/${sourceId}`),
    enabled: !!sourceId,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Create new GitHub source
 */
export function useCreateSource() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateSourceRequest) =>
      apiRequest<GitHubSource>('/marketplace/sources', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (source) => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
      toast({
        title: 'Source added',
        description: `Added ${source.owner}/${source.repo_name}`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to add source',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Update GitHub source
 */
export function useUpdateSource(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: UpdateSourceRequest) =>
      apiRequest<GitHubSource>(`/marketplace/sources/${sourceId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: (source) => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.detail(sourceId) });
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
      toast({
        title: 'Source updated',
        description: `Updated ${source.owner}/${source.repo_name}`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update source',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Delete GitHub source
 */
export function useDeleteSource() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (sourceId: string) =>
      apiRequest<void>(`/marketplace/sources/${sourceId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
      toast({
        title: 'Source deleted',
        description: 'GitHub source has been removed',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to delete source',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// ============================================================================
// Scan Operations
// ============================================================================

/**
 * Trigger source rescan
 */
export function useRescanSource(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data?: ScanRequest) =>
      apiRequest<ScanResult>(`/marketplace/sources/${sourceId}/rescan`, {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.detail(sourceId) });
      queryClient.invalidateQueries({ queryKey: sourceKeys.catalogs() });

      if (result.status === 'success') {
        // Build description with dedup counts (P4.4a)
        const parts = [`${result.new_count} new, ${result.updated_count} updated`];

        // Add deduplication info if present
        if (result.duplicates_within_source || result.duplicates_cross_source) {
          const dedupParts = [];
          if (result.duplicates_within_source) {
            dedupParts.push(`${result.duplicates_within_source} within-source duplicates`);
          }
          if (result.duplicates_cross_source) {
            dedupParts.push(`${result.duplicates_cross_source} cross-source duplicates`);
          }
          parts.push(dedupParts.join(', '));
        }

        const description = `Found ${result.artifacts_found} artifacts (${parts.join('; ')})`;

        toast({
          title: 'Scan complete',
          description,
        });
      } else if (result.status === 'partial') {
        toast({
          title: 'Scan completed with warnings',
          description: `Found ${result.artifacts_found} artifacts. ${result.errors.length} errors occurred.`,
          variant: 'destructive',
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: 'Scan failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// ============================================================================
// Catalog Operations
// ============================================================================

/**
 * Fetch source catalog with filters and pagination
 *
 * @param staleTime - Optional override for query stale time in milliseconds.
 *   Defaults to 30 seconds (30_000). Pass a longer value (e.g. 5 * 60 * 1000)
 *   for read-heavy callers such as the plugin breakdown tab, so that subsequent
 *   renders get an instant cache hit instead of re-fetching all pages.
 */
export function useSourceCatalog(
  sourceId: string,
  filters?: CatalogFilters,
  limit = 50,
  staleTime = 30000,
) {
  return useInfiniteQuery({
    queryKey: sourceKeys.catalog(sourceId, filters, limit),
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams();
      if (pageParam) params.append('cursor', pageParam);
      params.append('limit', limit.toString());
      if (filters?.artifact_type) params.append('artifact_type', filters.artifact_type);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.min_confidence !== undefined) {
        params.append('min_confidence', filters.min_confidence.toString());
      }
      if (filters?.max_confidence !== undefined) {
        params.append('max_confidence', filters.max_confidence.toString());
      }
      if (filters?.include_below_threshold !== undefined) {
        params.append('include_below_threshold', filters.include_below_threshold.toString());
      }
      if (filters?.sort_by) {
        params.append('sort_by', filters.sort_by);
      }
      if (filters?.sort_order) {
        params.append('sort_order', filters.sort_order);
      }
      // Note: search is client-side filter for now
      return apiRequest<CatalogListResponse>(
        `/marketplace/sources/${sourceId}/artifacts?${params}`
      );
    },
    getNextPageParam: (lastPage) =>
      lastPage.page_info.has_next_page ? lastPage.page_info.end_cursor : undefined,
    initialPageParam: undefined as string | undefined,
    enabled: !!sourceId,
    staleTime,
  });
}

// ============================================================================
// Import Operations
// ============================================================================

/**
 * Import artifacts from catalog to collection
 */
export function useImportArtifacts(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: ImportRequest) =>
      apiRequest<ImportResult>(`/marketplace/sources/${sourceId}/import`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] }); // Invalidate artifacts list
      queryClient.invalidateQueries({ queryKey: ['collections'] }); // Invalidate collection page (infinite-artifacts)

      const message = [
        result.imported_count > 0 && `${result.imported_count} imported`,
        result.skipped_count > 0 && `${result.skipped_count} skipped`,
        result.error_count > 0 && `${result.error_count} failed`,
      ]
        .filter(Boolean)
        .join(', ');

      toast({
        title: 'Import complete',
        description: message || 'No artifacts were processed',
        variant: result.error_count > 0 ? 'destructive' : 'default',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Import failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Bulk select helper - import all matching entries
 */
export function useImportAllMatching(sourceId: string) {
  const { data } = useSourceCatalog(sourceId, { status: 'new' });
  const importMutation = useImportArtifacts(sourceId);

  const importAll = (strategy: ImportRequest['conflict_strategy'] = 'skip') => {
    const allEntries = data?.pages.flatMap((page) => page.items) || [];
    const entryIds = allEntries.map((entry) => entry.id);

    if (entryIds.length === 0) {
      return;
    }

    return importMutation.mutateAsync({
      entry_ids: entryIds,
      conflict_strategy: strategy,
    });
  };

  return {
    importAll,
    isLoading: importMutation.isPending,
    totalNew: data?.pages[0]?.counts_by_status.new || 0,
  };
}

// ============================================================================
// Catalog Entry Updates
// ============================================================================

/**
 * Update catalog entry name
 */
export function useUpdateCatalogEntryName(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ entryId, name }: { entryId: string; name: string }) =>
      apiRequest<CatalogEntry>(`/marketplace/sources/${sourceId}/artifacts/${entryId}`, {
        method: 'PATCH',
        body: JSON.stringify({ name } as UpdateCatalogEntryNameRequest),
      }),
    onSuccess: (entry) => {
      queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
      toast({
        title: 'Name updated',
        description: `Renamed to ${entry.name}`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update name',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// ============================================================================
// Exclusion Operations
// ============================================================================

interface ExcludeEntryRequest {
  excluded: boolean;
  reason?: string;
}

/**
 * Mark a catalog entry as excluded
 */
export function useExcludeCatalogEntry(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ entryId, reason }: { entryId: string; reason?: string }) =>
      apiRequest<CatalogEntry>(`/marketplace/sources/${sourceId}/artifacts/${entryId}/exclude`, {
        method: 'PATCH',
        body: JSON.stringify({ excluded: true, reason } as ExcludeEntryRequest),
      }),
    onSuccess: (entry) => {
      queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
      toast({
        title: 'Entry excluded',
        description: `${entry.name} has been excluded from the catalog`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to exclude entry',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Restore an excluded catalog entry
 */
export function useRestoreCatalogEntry(sourceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (entryId: string) =>
      apiRequest<CatalogEntry>(`/marketplace/sources/${sourceId}/artifacts/${entryId}/exclude`, {
        method: 'PATCH',
        body: JSON.stringify({ excluded: false } as ExcludeEntryRequest),
      }),
    onSuccess: (entry) => {
      queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
      toast({
        title: 'Entry restored',
        description: `${entry.name} has been restored to the catalog`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to restore entry',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// ============================================================================
// URL Inference Operations
// ============================================================================

/**
 * Infer repository structure from GitHub URL
 */
export function useInferUrl() {
  return useMutation({
    mutationFn: async (url: string) => inferUrl(url),
  });
}
