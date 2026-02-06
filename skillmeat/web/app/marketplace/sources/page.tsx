/**
 * Marketplace Sources Page
 *
 * Displays all GitHub repository sources that can be scanned for artifacts.
 * Provides add, rescan, and manage functionality.
 *
 * Supports two search modes:
 * - Sources mode: Filter sources client-side by repository name
 * - Artifacts mode: Search across all catalog entries using FTS5
 *
 * Filter state is synchronized with URL query parameters for shareability
 * and browser navigation support.
 */

'use client';

import { useMemo, useCallback, Suspense, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Plus,
  RefreshCw,
  Search as SearchIcon,
  Loader2,
  Github,
  X,
  AlertCircle,
  FilterX,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { SourceCard, SourceCardSkeleton } from '@/components/marketplace/source-card';
import { SourceFilterBar, type FilterState } from '@/components/marketplace/source-filter-bar';
import { AddSourceModal } from '@/components/marketplace/add-source-modal';
import { EditSourceModal } from '@/components/marketplace/edit-source-modal';
import { DeleteSourceDialog } from '@/components/marketplace/delete-source-dialog';
import {
  RescanUpdatesDialog,
  type UpdatedImport,
} from '@/components/marketplace/rescan-updates-dialog';
import { SearchModeToggle, type SearchMode } from '@/components/marketplace/search-mode-toggle';
import {
  ArtifactSearchResults,
  ArtifactSearchResultsSkeleton,
} from '@/components/marketplace/artifact-search-results';
import { CatalogEntryModal } from '@/components/CatalogEntryModal';
import { useSources, sourceKeys, useArtifactSearch, type ArtifactSearchResult } from '@/hooks';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks';
import { apiRequest } from '@/lib/api';
import type {
  ScanResult,
  CatalogListResponse,
  GitHubSource,
  CatalogEntry,
  ArtifactType,
  CatalogStatus,
} from '@/types/marketplace';
import { useState } from 'react';

// ============================================================================
// URL State Utilities
// ============================================================================

/**
 * Parse filter state from URL search params
 */
function parseFiltersFromUrl(searchParams: URLSearchParams): FilterState {
  const filters: FilterState = {};

  const artifactType = searchParams.get('artifact_type');
  if (artifactType) {
    filters.artifact_type = artifactType;
  }

  const trustLevel = searchParams.get('trust_level');
  if (trustLevel) {
    filters.trust_level = trustLevel;
  }

  const tags = searchParams.get('tags');
  if (tags) {
    filters.tags = tags.split(',').filter(Boolean);
  }

  return filters;
}

/**
 * Serialize filter state to URL search params string
 */
function serializeFiltersToUrl(filters: FilterState, searchQuery: string): URLSearchParams {
  const params = new URLSearchParams();

  if (searchQuery.trim()) {
    params.set('q', searchQuery.trim());
  }

  if (filters.artifact_type) {
    params.set('artifact_type', filters.artifact_type);
  }

  if (filters.trust_level) {
    params.set('trust_level', filters.trust_level);
  }

  if (filters.tags && filters.tags.length > 0) {
    params.set('tags', filters.tags.join(','));
  }

  return params;
}

/**
 * Check if any filters or search query are active
 */
function hasActiveFilters(filters: FilterState, searchQuery: string): boolean {
  return !!(
    searchQuery.trim() ||
    filters.artifact_type ||
    filters.trust_level ||
    (filters.tags && filters.tags.length > 0)
  );
}

/**
 * Count the number of active filters (including search)
 */
function countActiveFilters(filters: FilterState, searchQuery: string): number {
  let count = 0;
  if (searchQuery.trim()) count += 1;
  if (filters.artifact_type) count += 1;
  if (filters.trust_level) count += 1;
  if (filters.tags && filters.tags.length > 0) count += filters.tags.length;
  return count;
}

// ============================================================================
// Error State Component
// ============================================================================

interface ErrorStateProps {
  error: Error;
  onRetry: () => void;
  isRetrying?: boolean;
}

function ErrorState({ error, onRetry, isRetrying }: ErrorStateProps) {
  return (
    <Alert variant="destructive" className="max-w-2xl" role="alert" aria-live="polite">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Failed to load sources</AlertTitle>
      <AlertDescription className="mt-2 space-y-3">
        <p>
          We encountered an error while loading your GitHub sources. This could be due to a network
          issue or the server being temporarily unavailable.
        </p>
        <p className="font-mono text-xs opacity-80">{error.message || 'Unknown error occurred'}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          disabled={isRetrying}
          className="mt-2"
          aria-label="Retry loading sources"
        >
          {isRetrying ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Retrying...
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </>
          )}
        </Button>
      </AlertDescription>
    </Alert>
  );
}

// ============================================================================
// Loading State Component
// ============================================================================

interface LoadingGridProps {
  count?: number;
}

function LoadingGrid({ count = 6 }: LoadingGridProps) {
  return (
    <div
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      aria-busy="true"
      aria-label="Loading source repositories"
    >
      {Array.from({ length: count }, (_, i) => (
        <SourceCardSkeleton key={i} />
      ))}
    </div>
  );
}

// ============================================================================
// Empty State Component
// ============================================================================

interface EmptyStateProps {
  isFiltered: boolean;
  onClearFilters: () => void;
  onAddSource: () => void;
}

function EmptyState({ isFiltered, onClearFilters, onAddSource }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Github className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden="true" />
      {isFiltered ? (
        <>
          <h3 className="mb-2 text-lg font-semibold">No matching sources</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            No sources match your current search and filter criteria. Try adjusting your filters or
            clearing them to see all sources.
          </p>
          <Button variant="outline" className="mt-4 gap-2" onClick={onClearFilters}>
            <FilterX className="h-4 w-4" aria-hidden="true" />
            Clear All Filters
          </Button>
        </>
      ) : (
        <>
          <h3 className="mb-2 text-lg font-semibold">No sources added yet</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            Add a GitHub repository to start discovering Claude Code artifacts like skills,
            commands, agents, and more.
          </p>
          <Button className="mt-4" onClick={onAddSource}>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            Add Your First Source
          </Button>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Filter Summary Component
// ============================================================================

interface FilterSummaryProps {
  totalCount: number;
  filteredCount: number;
  artifactCount: number;
  isFiltered: boolean;
  filterCount: number;
  onClearFilters: () => void;
}

function FilterSummary({
  totalCount,
  filteredCount,
  artifactCount,
  isFiltered,
  filterCount,
  onClearFilters,
}: FilterSummaryProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
      <span>
        {isFiltered ? (
          <>
            Showing {filteredCount} of {totalCount} sources
          </>
        ) : (
          <>{filteredCount} sources</>
        )}
      </span>
      <span aria-hidden="true">-</span>
      <span>{artifactCount} total artifacts</span>

      {/* Clear Filters Button - prominently displayed when filters are active */}
      {isFiltered && (
        <>
          <span aria-hidden="true">|</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearFilters}
            className="h-7 gap-1.5 px-2 text-muted-foreground hover:text-foreground"
            aria-label={`Clear ${filterCount} active filter${filterCount !== 1 ? 's' : ''}`}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Clear {filterCount} filter{filterCount !== 1 ? 's' : ''}
          </Button>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Inner Component (uses useSearchParams)
// ============================================================================

function MarketplaceSourcesPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Parse search mode from URL (defaults to 'sources')
  const searchMode = (searchParams.get('mode') as SearchMode) || 'sources';

  // Parse filters from URL
  const filters = useMemo(() => parseFiltersFromUrl(searchParams), [searchParams]);
  const searchQuery = searchParams.get('q') || '';

  // Artifact search hook (only active in artifacts mode)
  const artifactSearch = useArtifactSearch({
    debounceMs: 300,
    minQueryLength: 2,
  });

  // Sync URL query to artifact search state on mount/mode change
  useEffect(() => {
    if (searchMode === 'artifacts' && searchQuery && artifactSearch.query !== searchQuery) {
      artifactSearch.setQuery(searchQuery);
    }
  }, [searchMode, searchQuery, artifactSearch]);

  // Compute filter state
  const isFiltered = useMemo(() => hasActiveFilters(filters, searchQuery), [filters, searchQuery]);
  const activeFilterCount = useMemo(
    () => countActiveFilters(filters, searchQuery),
    [filters, searchQuery]
  );

  // Modal state (local only - not in URL)
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<GitHubSource | null>(null);
  const [rescanningSourceId, setRescanningSourceId] = useState<string | null>(null);
  const [updatesDialogOpen, setUpdatesDialogOpen] = useState(false);
  const [pendingUpdates, setPendingUpdates] = useState<{
    sourceId: string;
    sourceName: string;
    updates: UpdatedImport[];
  } | null>(null);

  // Catalog entry modal state for artifact search results
  const [catalogModalOpen, setCatalogModalOpen] = useState(false);
  const [selectedSearchResult, setSelectedSearchResult] = useState<CatalogEntry | null>(null);
  const [isImportingFromSearch, setIsImportingFromSearch] = useState(false);

  // Fetch sources
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
    isRefetching,
  } = useSources();

  // Rescan mutation (works for any source ID)
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Flatten pages
  const allSources = useMemo(() => {
    return data?.pages.flatMap((page) => page.items) || [];
  }, [data]);

  const rescanMutation = useMutation({
    mutationFn: ({ sourceId }: { sourceId: string }) =>
      apiRequest<ScanResult>(`/marketplace/sources/${sourceId}/rescan`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: async (result, { sourceId }) => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.detail(sourceId) });
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: sourceKeys.catalogs() });

      // Show standard toast for scan results
      if (result.status === 'success') {
        toast({
          title: 'Scan complete',
          description: `Found ${result.artifacts_found} artifacts (${result.new_count} new, ${result.updated_count} updated)`,
        });
      } else if (result.status === 'partial') {
        toast({
          title: 'Scan completed with warnings',
          description: `Found ${result.artifacts_found} artifacts. ${result.errors.length} errors occurred.`,
          variant: 'destructive',
        });
      }

      // Check for updated imports and show dialog
      if (result.updated_imports && result.updated_imports.length > 0) {
        try {
          // Fetch catalog entries for the updated imports
          const catalogResponse = await apiRequest<CatalogListResponse>(
            `/marketplace/sources/${sourceId}/artifacts?include_below_threshold=true&limit=100`
          );

          const updatedEntries = catalogResponse.items.filter((item) =>
            result.updated_imports?.includes(item.id)
          );

          if (updatedEntries.length > 0) {
            const updates: UpdatedImport[] = updatedEntries.map((entry) => ({
              entryId: entry.id,
              name: entry.name,
              artifactType: entry.artifact_type,
              // We don't track import_sha, so show "imported" as placeholder
              currentSha: 'imported',
              newSha: entry.detected_sha?.slice(0, 7) || 'latest',
              hasLocalChanges: false, // Would need diff API to determine this
              importId: entry.import_id || '',
            }));

            // Find source name from cached data
            const source = allSources.find((s) => s.id === sourceId);

            setPendingUpdates({
              sourceId,
              sourceName: source ? `${source.owner}/${source.repo_name}` : sourceId,
              updates,
            });
            setUpdatesDialogOpen(true);
          }
        } catch (err) {
          // Log error but don't fail the rescan - updates dialog is optional
          console.error('Failed to fetch updated import details:', err);
        }
      }

      setRescanningSourceId(null);
    },
    onError: (error: Error) => {
      toast({
        title: 'Scan failed',
        description: error.message,
        variant: 'destructive',
      });
      setRescanningSourceId(null);
    },
  });

  // Extract all unique tags and their counts from sources for the filter bar
  const { availableTags, tagCounts } = useMemo(() => {
    const countMap: Record<string, number> = {};
    allSources.forEach((source) => {
      source.tags?.forEach((tag) => {
        countMap[tag] = (countMap[tag] || 0) + 1;
      });
    });
    return {
      availableTags: Object.keys(countMap).sort(),
      tagCounts: countMap,
    };
  }, [allSources]);

  // Filter by search and filters (client-side filtering)
  const filteredSources = useMemo(() => {
    let result = allSources;

    // Apply search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (source) =>
          source.owner.toLowerCase().includes(query) ||
          source.repo_name.toLowerCase().includes(query)
      );
    }

    // Apply trust level filter
    if (filters.trust_level) {
      result = result.filter((source) => source.trust_level === filters.trust_level);
    }

    // Apply tag filters (source must have ALL selected tags)
    if (filters.tags && filters.tags.length > 0) {
      result = result.filter((source) => filters.tags!.every((tag) => source.tags?.includes(tag)));
    }

    // Apply artifact type filter (source must have at least one artifact of that type)
    if (filters.artifact_type) {
      result = result.filter((source) => {
        const counts = source.counts_by_type ?? { skill: source.artifact_count };
        return (counts[filters.artifact_type!] ?? 0) > 0;
      });
    }

    return result;
  }, [allSources, searchQuery, filters]);

  // URL update helper
  const updateUrl = useCallback(
    (newFilters: FilterState, newSearchQuery: string, newMode?: SearchMode) => {
      const params = serializeFiltersToUrl(newFilters, newSearchQuery);
      // Preserve mode in URL if specified or if already in artifacts mode
      const modeToUse = newMode ?? searchMode;
      if (modeToUse === 'artifacts') {
        params.set('mode', 'artifacts');
      }
      const search = params.toString();
      // Use replace to avoid polluting history for every keystroke
      router.replace(search ? `?${search}` : '/marketplace/sources', {
        scroll: false,
      });
    },
    [router, searchMode]
  );

  // Handler for search mode changes
  const handleModeChange = useCallback(
    (newMode: SearchMode) => {
      const params = new URLSearchParams();
      if (newMode === 'artifacts') {
        params.set('mode', 'artifacts');
        // Keep the search query when switching modes
        if (searchQuery.trim()) {
          params.set('q', searchQuery.trim());
        }
        // Also sync to artifact search input
        artifactSearch.setQuery(searchQuery);
      } else {
        // Switching to sources mode - keep filters and search
        if (searchQuery.trim()) {
          params.set('q', searchQuery.trim());
        }
        if (filters.artifact_type) {
          params.set('artifact_type', filters.artifact_type);
        }
        if (filters.trust_level) {
          params.set('trust_level', filters.trust_level);
        }
        if (filters.tags && filters.tags.length > 0) {
          params.set('tags', filters.tags.join(','));
        }
      }
      const search = params.toString();
      router.replace(search ? `?${search}` : '/marketplace/sources', {
        scroll: false,
      });
    },
    [router, searchQuery, filters, artifactSearch]
  );

  // Handler for filter changes
  const handleFilterChange = useCallback(
    (newFilters: FilterState) => {
      updateUrl(newFilters, searchQuery);
    },
    [updateUrl, searchQuery]
  );

  // Handler for search query changes
  const handleSearchChange = useCallback(
    (newQuery: string) => {
      updateUrl(filters, newQuery);
    },
    [updateUrl, filters]
  );

  // Handler for clicking a tag on a source card
  const handleTagClick = useCallback(
    (tag: string) => {
      const currentTags = filters.tags || [];
      // Toggle the tag: add if not present, remove if already present
      const newTags = currentTags.includes(tag)
        ? currentTags.filter((t) => t !== tag)
        : [...currentTags, tag];

      const newFilters: FilterState = {
        ...filters,
        tags: newTags.length > 0 ? newTags : undefined,
      };
      updateUrl(newFilters, searchQuery);
    },
    [filters, searchQuery, updateUrl]
  );

  // Handler for artifact search input changes
  const handleArtifactSearchChange = useCallback(
    (newQuery: string) => {
      artifactSearch.setQuery(newQuery);
      // Also sync to URL
      const params = new URLSearchParams();
      params.set('mode', 'artifacts');
      if (newQuery.trim()) {
        params.set('q', newQuery.trim());
      }
      const search = params.toString();
      router.replace(search ? `?${search}` : '/marketplace/sources?mode=artifacts', {
        scroll: false,
      });
    },
    [router, artifactSearch]
  );

  // Handler for clearing all filters and search
  const handleClearAll = useCallback(() => {
    // Preserve mode when clearing
    if (searchMode === 'artifacts') {
      artifactSearch.setQuery('');
      router.replace('/marketplace/sources?mode=artifacts', { scroll: false });
    } else {
      router.replace('/marketplace/sources', { scroll: false });
    }
  }, [router, searchMode, artifactSearch]);

  // Handler functions for modals
  const handleEdit = (source: GitHubSource) => {
    setSelectedSource(source);
    setEditModalOpen(true);
  };

  const handleDelete = (source: GitHubSource) => {
    setSelectedSource(source);
    setDeleteDialogOpen(true);
  };

  // Rescan handler
  const handleRescan = (sourceId: string) => {
    setRescanningSourceId(sourceId);
    rescanMutation.mutate({ sourceId });
  };

  // Handler to convert search result to CatalogEntry and open modal
  const handleSearchResultClick = (result: ArtifactSearchResult) => {
    // Convert ArtifactSearchResult to CatalogEntry format
    const catalogEntry: CatalogEntry = {
      id: result.id,
      source_id: result.source_id,
      artifact_type: result.artifact_type as ArtifactType,
      name: result.name,
      path: result.path,
      upstream_url:
        result.upstream_url ||
        `https://github.com/${result.source_owner}/${result.source_repo}/tree/HEAD/${result.path}`,
      detected_at: new Date().toISOString(), // Not available in search result
      confidence_score: result.confidence_score,
      status: result.status as CatalogStatus,
    };
    setSelectedSearchResult(catalogEntry);
    setCatalogModalOpen(true);
  };

  // Handler to import artifact from search result modal
  const handleImportFromSearch = async (entry: CatalogEntry) => {
    setIsImportingFromSearch(true);
    try {
      await apiRequest(`/marketplace/sources/${entry.source_id}/import`, {
        method: 'POST',
        body: JSON.stringify({
          entry_ids: [entry.id],
          conflict_strategy: 'skip',
        }),
      });
      toast({
        title: 'Import successful',
        description: `Imported ${entry.name} to your collection`,
      });
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: sourceKeys.catalogs() });
      // Update the entry status in the modal
      setSelectedSearchResult((prev) =>
        prev ? { ...prev, status: 'imported' as CatalogStatus } : null
      );
    } catch (error) {
      toast({
        title: 'Import failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setIsImportingFromSearch(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">GitHub Sources</h1>
          <p className="text-muted-foreground">
            Add and manage GitHub repositories to discover Claude Code artifacts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => refetch()} disabled={isLoading || isRefetching}>
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isLoading || isRefetching ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
          <Button onClick={() => setAddModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Source
          </Button>
        </div>
      </div>

      {/* Search Mode Toggle and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {/* Search Mode Toggle */}
        <SearchModeToggle mode={searchMode} onModeChange={handleModeChange} disabled={isLoading} />

        {/* Search Bar - different behavior based on mode */}
        <div className="flex flex-1 items-center gap-2">
          <div className="relative max-w-md flex-1">
            <SearchIcon
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            {searchMode === 'sources' ? (
              <Input
                placeholder="Search repositories..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9 pr-9"
                aria-label="Search repositories by owner or name"
              />
            ) : (
              <Input
                placeholder="Search artifacts across all sources..."
                value={artifactSearch.query}
                onChange={(e) => handleArtifactSearchChange(e.target.value)}
                className="pl-9 pr-9"
                aria-label="Search artifacts across all marketplace sources"
              />
            )}
            {/* Clear search button inside input */}
            {(searchMode === 'sources' ? searchQuery : artifactSearch.query) && (
              <button
                onClick={() =>
                  searchMode === 'sources' ? handleSearchChange('') : handleArtifactSearchChange('')
                }
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-sm text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label="Clear search"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Clear All Filters Button - always visible when filtered (sources mode only) */}
          {searchMode === 'sources' && isFiltered && (
            <Button
              variant="outline"
              size="default"
              onClick={handleClearAll}
              className="gap-2 whitespace-nowrap"
              aria-label={`Clear all ${activeFilterCount} active filters`}
            >
              <FilterX className="h-4 w-4" aria-hidden="true" />
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      {/* Filter Bar - only in sources mode */}
      {searchMode === 'sources' && availableTags.length > 0 && (
        <SourceFilterBar
          currentFilters={filters}
          onFilterChange={handleFilterChange}
          availableTags={availableTags}
          tagCounts={tagCounts}
        />
      )}

      {/* Conditional content based on search mode */}
      {searchMode === 'artifacts' ? (
        <>
          {/* Artifact Search Results */}
          {artifactSearch.isFetching && !artifactSearch.data && <ArtifactSearchResultsSkeleton />}

          {/* Loading indicator when fetching with existing data */}
          {artifactSearch.isFetching && artifactSearch.data && (
            <div
              className="flex items-center gap-2 text-sm text-muted-foreground"
              aria-live="polite"
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching...
            </div>
          )}

          {/* Error state for artifact search */}
          {artifactSearch.error && (
            <Alert variant="destructive" className="max-w-2xl" role="alert">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Search failed</AlertTitle>
              <AlertDescription>
                {artifactSearch.error.message || 'An error occurred while searching.'}
              </AlertDescription>
            </Alert>
          )}

          {/* Prompt to enter search query */}
          {!artifactSearch.query && !artifactSearch.data && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <SearchIcon className="mb-4 h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
              <h3 className="mb-2 text-lg font-medium text-muted-foreground">Search artifacts</h3>
              <p className="max-w-md text-sm text-muted-foreground/80">
                Enter a search term to find artifacts across all indexed sources.
              </p>
            </div>
          )}

          {/* Query too short message */}
          {artifactSearch.query &&
            artifactSearch.query.length < 2 &&
            !artifactSearch.isFetching && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <SearchIcon
                  className="mb-4 h-12 w-12 text-muted-foreground/50"
                  aria-hidden="true"
                />
                <h3 className="mb-2 text-lg font-medium text-muted-foreground">Keep typing...</h3>
                <p className="max-w-md text-sm text-muted-foreground/80">
                  Enter at least 2 characters to search.
                </p>
              </div>
            )}

          {/* Artifact search results */}
          {artifactSearch.isSuccess && artifactSearch.data && (
            <>
              {artifactSearch.data.items.length > 0 ? (
                <>
                  <div className="text-sm text-muted-foreground">
                    Found {artifactSearch.data.items.length} artifact
                    {artifactSearch.data.items.length !== 1 ? 's' : ''}
                  </div>
                  <ArtifactSearchResults
                    results={artifactSearch.data.items}
                    onResultClick={handleSearchResultClick}
                  />
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Info className="mb-4 h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
                  <h3 className="mb-2 text-lg font-medium text-muted-foreground">
                    No results found
                  </h3>
                  <p className="max-w-md text-sm text-muted-foreground/80">
                    No artifacts match your search. Artifact search requires indexing to be enabled
                    on sources. Switch to Sources mode to manage indexing settings.
                  </p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => handleModeChange('sources')}
                  >
                    Switch to Sources
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <>
          {/* Stats Summary with Clear Filters */}
          {!isLoading && !error && allSources.length > 0 && (
            <FilterSummary
              totalCount={allSources.length}
              filteredCount={filteredSources.length}
              artifactCount={filteredSources.reduce((sum, s) => sum + s.artifact_count, 0)}
              isFiltered={isFiltered}
              filterCount={activeFilterCount}
              onClearFilters={handleClearAll}
            />
          )}

          {/* Error State */}
          {error && (
            <ErrorState
              error={error instanceof Error ? error : new Error('Unknown error')}
              onRetry={() => refetch()}
              isRetrying={isRefetching}
            />
          )}

          {/* Loading State */}
          {isLoading && <LoadingGrid count={6} />}

          {/* Refetching Indicator - shows when refreshing with existing data */}
          {isRefetching && !isLoading && (
            <div
              className="flex items-center gap-2 text-sm text-muted-foreground"
              aria-live="polite"
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              Refreshing sources...
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && filteredSources.length === 0 && (
            <EmptyState
              isFiltered={isFiltered}
              onClearFilters={handleClearAll}
              onAddSource={() => setAddModalOpen(true)}
            />
          )}

          {/* Sources Grid */}
          {!isLoading && !error && filteredSources.length > 0 && (
            <>
              <div
                className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
                role="list"
                aria-label="GitHub source repositories"
              >
                {filteredSources.map((source) => (
                  <div key={source.id} role="listitem">
                    <SourceCard
                      source={source}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                      onRescan={handleRescan}
                      isRescanning={rescanningSourceId === source.id}
                      onTagClick={handleTagClick}
                    />
                  </div>
                ))}
              </div>

              {/* Load More */}
              {hasNextPage && (
                <div className="flex justify-center pt-6">
                  <Button
                    variant="outline"
                    onClick={() => fetchNextPage()}
                    disabled={isFetchingNextPage}
                  >
                    {isFetchingNextPage ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      'Load More'
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Add Source Modal */}
      <AddSourceModal
        open={addModalOpen}
        onOpenChange={setAddModalOpen}
        onSuccess={() => {
          setAddModalOpen(false);
          refetch();
        }}
      />

      {/* Edit Source Modal */}
      <EditSourceModal
        source={selectedSource}
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        onSuccess={() => {
          setEditModalOpen(false);
          setSelectedSource(null);
          refetch();
        }}
      />

      {/* Delete Source Dialog */}
      <DeleteSourceDialog
        source={selectedSource}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onSuccess={() => {
          setDeleteDialogOpen(false);
          setSelectedSource(null);
          refetch();
        }}
      />

      {/* Rescan Updates Dialog */}
      {pendingUpdates && (
        <RescanUpdatesDialog
          open={updatesDialogOpen}
          onOpenChange={(open) => {
            setUpdatesDialogOpen(open);
            if (!open) setPendingUpdates(null);
          }}
          sourceId={pendingUpdates.sourceId}
          sourceName={pendingUpdates.sourceName}
          updatedImports={pendingUpdates.updates}
          onSyncComplete={() => {
            queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
            queryClient.invalidateQueries({ queryKey: sourceKeys.catalogs() });
          }}
        />
      )}

      {/* Catalog Entry Modal for Search Results */}
      <CatalogEntryModal
        entry={selectedSearchResult}
        open={catalogModalOpen}
        onOpenChange={setCatalogModalOpen}
        onImport={handleImportFromSearch}
        isImporting={isImportingFromSearch}
      />
    </div>
  );
}

// ============================================================================
// Main Export with Suspense Boundary
// ============================================================================

/**
 * Marketplace Sources Page
 *
 * Wraps the inner component in Suspense because useSearchParams requires it
 * in Next.js 15 when the page doesn't have a loading.tsx file.
 */
export default function MarketplaceSourcesPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          {/* Header skeleton */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">GitHub Sources</h1>
              <p className="text-muted-foreground">
                Add and manage GitHub repositories to discover Claude Code artifacts
              </p>
            </div>
          </div>
          {/* Cards skeleton */}
          <LoadingGrid count={6} />
        </div>
      }
    >
      <MarketplaceSourcesPageInner />
    </Suspense>
  );
}
