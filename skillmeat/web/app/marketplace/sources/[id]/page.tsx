/**
 * Source Detail Page
 *
 * Displays the artifact catalog for a GitHub source with filtering,
 * import functionality, and rescan actions.
 */

'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import { ExcludeArtifactDialog } from '@/components/marketplace/exclude-artifact-dialog';
import { DirectoryMapModal } from '@/components/marketplace/DirectoryMapModal';
import { useParams, useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  Github,
  ExternalLink,
  Filter,
  Download,
  Loader2,
  AlertTriangle,
  Pencil,
  Trash2,
  StickyNote,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ExcludedArtifactsList } from './components/excluded-list';
import { SourceToolbar, useViewMode } from './components/source-toolbar';
import { CatalogList } from './components/catalog-list';
import type { SortOption, ViewMode } from './components/source-toolbar';
import {
  useSource,
  useSourceCatalog,
  useRescanSource,
  useImportArtifacts,
  useExcludeCatalogEntry,
  useUpdateSource,
} from '@/hooks/useMarketplaceSources';
import { EditSourceModal } from '@/components/marketplace/edit-source-modal';
import { DeleteSourceDialog } from '@/components/marketplace/delete-source-dialog';
import { CatalogEntryModal } from '@/components/CatalogEntryModal';
import { ScoreBadge } from '@/components/ScoreBadge';
import type { CatalogEntry, CatalogFilters, ArtifactType, CatalogStatus } from '@/types/marketplace';

// ============================================================================
// Sub-components
// ============================================================================

interface CatalogCardProps {
  entry: CatalogEntry;
  selected: boolean;
  onSelect: (selected: boolean) => void;
  onImport: () => void;
  isImporting: boolean;
  onClick?: () => void;
  sourceId: string;
}

function CatalogCard({
  entry,
  selected,
  onSelect,
  onImport,
  isImporting,
  onClick,
  sourceId,
}: CatalogCardProps) {
  const [excludeDialogOpen, setExcludeDialogOpen] = useState(false);
  const excludeMutation = useExcludeCatalogEntry(sourceId);
  const statusConfig = {
    new: {
      label: 'New',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    updated: {
      label: 'Updated',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
    },
    imported: {
      label: 'Imported',
      className: 'border-gray-500 text-gray-700 bg-gray-50 dark:bg-gray-950',
    },
    removed: {
      label: 'Removed',
      className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950 line-through',
    },
    excluded: {
      label: 'Excluded',
      className: 'border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-800',
    },
  }[entry.status];

  const typeConfig: Record<ArtifactType, { label: string; color: string }> = {
    skill: { label: 'Skill', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
    command: { label: 'Command', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
    agent: { label: 'Agent', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    mcp: { label: 'MCP', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
    mcp_server: { label: 'MCP', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
    hook: { label: 'Hook', color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200' },
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <Card
      className={cn(
        'relative transition-shadow hover:shadow-md cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        selected && 'ring-2 ring-primary'
      )}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`View details for ${entry.name} ${entry.artifact_type}`}
    >
      <div className="p-4 space-y-3">
        {/* Selection checkbox */}
        <div className="absolute top-3 right-3" onClick={(e) => e.stopPropagation()}>
          <Checkbox
            checked={selected}
            onCheckedChange={onSelect}
            disabled={entry.status === 'removed'}
            aria-label={`Select ${entry.name} for import`}
          />
        </div>

        {/* Header */}
        <div className="pr-8">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <Badge variant="outline" className={typeConfig[entry.artifact_type].color}>
              {typeConfig[entry.artifact_type].label}
            </Badge>
            <Badge variant="outline" className={statusConfig.className}>
              {statusConfig.label}
            </Badge>
            {/* Duplicate Badge (P4.3c) */}
            {entry.status === 'excluded' && entry.is_duplicate && (
              <Badge
                variant="outline"
                className="border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950"
                title={
                  entry.duplicate_reason === 'within_source'
                    ? `Duplicate within this source${entry.duplicate_of ? `: ${entry.duplicate_of}` : ''}`
                    : entry.duplicate_reason === 'cross_source'
                    ? 'Duplicate from another source or collection'
                    : 'Marked as duplicate'
                }
              >
                Duplicate
              </Badge>
            )}
          </div>
          <h3 className="font-semibold truncate">{entry.name}</h3>
          <p className="text-xs text-muted-foreground truncate">{entry.path}</p>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs">
          <ScoreBadge
            confidence={entry.confidence_score}
            size="sm"
            breakdown={entry.score_breakdown}
          />

          <a
            href={entry.upstream_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
            View on GitHub
          </a>
        </div>

        {/* Actions */}
        {entry.status !== 'imported' && entry.status !== 'removed' && entry.status !== 'excluded' && (
          <>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={(e) => {
                e.stopPropagation();
                onImport();
              }}
              disabled={isImporting}
            >
              {isImporting ? (
                <>
                  <Loader2 className="mr-2 h-3 w-3 animate-spin" aria-hidden="true" />
                  Importing...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-3 w-3" aria-hidden="true" />
                  Import
                </>
              )}
            </Button>
            <button
              type="button"
              className="w-full text-sm text-muted-foreground hover:underline cursor-pointer mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm"
              onClick={(e) => {
                e.stopPropagation();
                setExcludeDialogOpen(true);
              }}
              aria-label={`Mark ${entry.name} as not an artifact`}
            >
              Not an artifact
            </button>
          </>
        )}

        {entry.status === 'imported' && entry.import_date && (
          <p className="text-xs text-muted-foreground text-center">
            Imported {new Date(entry.import_date).toLocaleDateString()}
          </p>
        )}
      </div>

      <ExcludeArtifactDialog
        entry={entry}
        open={excludeDialogOpen}
        onOpenChange={setExcludeDialogOpen}
        onConfirm={() => {
          excludeMutation.mutate({ entryId: entry.id });
          setExcludeDialogOpen(false);
        }}
        isLoading={excludeMutation.isPending}
      />
    </Card>
  );
}

function CatalogCardSkeleton() {
  return (
    <Card>
      <div className="p-4 space-y-3">
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="flex justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-28" />
        </div>
        <Skeleton className="h-8 w-full" />
      </div>
    </Card>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export default function SourceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const sourceId = params.id as string;

  // Initialize state from URL parameters
  const [filters, setFilters] = useState<CatalogFilters>(() => ({
    artifact_type: (searchParams.get('type') as ArtifactType) || undefined,
    status: (searchParams.get('status') as CatalogStatus) || undefined,
  }));
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEntries, setSelectedEntries] = useState<Set<string>>(new Set());
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<CatalogEntry | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [directoryMapModalOpen, setDirectoryMapModalOpen] = useState(false);
  const [treeData, setTreeData] = useState<any[]>([]);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [treeError, setTreeError] = useState<string>();
  const [confidenceFilters, setConfidenceFilters] = useState(() => ({
    minConfidence: Number(searchParams.get('minConfidence')) || 50,
    maxConfidence: Number(searchParams.get('maxConfidence')) || 100,
    includeBelowThreshold: searchParams.get('includeBelowThreshold') === 'true',
  }));
  const [showOnlyDuplicates, setShowOnlyDuplicates] = useState(() =>
    searchParams.get('showOnlyDuplicates') === 'true'
  );
  const [sortOption, setSortOption] = useState<SortOption>(() => {
    const param = searchParams.get('sort');
    if (param === 'confidence-asc' || param === 'confidence-desc' ||
        param === 'name-asc' || param === 'name-desc' || param === 'date-added') {
      return param;
    }
    return 'confidence-desc'; // default to high confidence first
  });
  const [lastScanResult, setLastScanResult] = useState<any>(null);
  const [isMappingsOpen, setIsMappingsOpen] = useState(false);

  // Pagination state from URL
  const [currentPage, setCurrentPage] = useState(() => {
    const pageParam = searchParams.get('page');
    return pageParam ? Math.max(1, parseInt(pageParam, 10)) : 1;
  });
  const [itemsPerPage, setItemsPerPage] = useState(() => {
    const limitParam = searchParams.get('limit');
    const limit = limitParam ? parseInt(limitParam, 10) : 25;
    // Ensure valid limit value
    return [10, 25, 50, 100].includes(limit) ? limit : 25;
  });

  // View mode with localStorage persistence
  const [viewMode, setViewMode] = useViewMode();

  // Helper function to update URL parameters
  const updateURLParams = useCallback((
    newConfidenceFilters: typeof confidenceFilters,
    newFilters: typeof filters,
    newSortOption: SortOption,
    newShowOnlyDuplicates: boolean,
    newPage: number,
    newLimit: number
  ) => {
    const params = new URLSearchParams();

    // Add pagination params only if different from defaults
    if (newPage !== 1) {
      params.set('page', newPage.toString());
    }
    if (newLimit !== 25) {
      params.set('limit', newLimit.toString());
    }

    // Add confidence filters only if different from defaults
    if (newConfidenceFilters.minConfidence !== 50) {
      params.set('minConfidence', newConfidenceFilters.minConfidence.toString());
    }
    if (newConfidenceFilters.maxConfidence !== 100) {
      params.set('maxConfidence', newConfidenceFilters.maxConfidence.toString());
    }
    if (newConfidenceFilters.includeBelowThreshold) {
      params.set('includeBelowThreshold', 'true');
    }

    // Add duplicate filter (P4.4b)
    if (newShowOnlyDuplicates) {
      params.set('showOnlyDuplicates', 'true');
    }

    // Add type and status filters
    if (newFilters.artifact_type) {
      params.set('type', newFilters.artifact_type);
    }
    if (newFilters.status) {
      params.set('status', newFilters.status);
    }

    // Add sort option only if different from default
    if (newSortOption !== 'confidence-desc') {
      params.set('sort', newSortOption);
    }

    const query = params.toString();
    router.replace(`${pathname}${query ? `?${query}` : ''}`, { scroll: false });
  }, [router, pathname]);

  // Sync URL when filters or pagination change
  useEffect(() => {
    updateURLParams(confidenceFilters, filters, sortOption, showOnlyDuplicates, currentPage, itemsPerPage);
  }, [confidenceFilters, filters, sortOption, showOnlyDuplicates, currentPage, itemsPerPage]);

  // Reset to page 1 when filters change (but not when page/limit change)
  useEffect(() => {
    setCurrentPage(1);
  }, [confidenceFilters, filters, sortOption, showOnlyDuplicates, searchQuery]);

  // Data fetching
  const { data: source, isLoading: sourceLoading, error: sourceError } = useSource(sourceId);

  // Merge filters with confidence filters for API
  const mergedFilters: CatalogFilters = {
    ...filters,
    min_confidence: confidenceFilters.minConfidence,
    max_confidence: confidenceFilters.maxConfidence,
    include_below_threshold: confidenceFilters.includeBelowThreshold,
  };

  const {
    data: catalogData,
    isLoading: catalogLoading,
    isFetching: catalogFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useSourceCatalog(sourceId, mergedFilters);
  const rescanMutation = useRescanSource(sourceId);
  const importMutation = useImportArtifacts(sourceId);
  const updateSourceMutation = useUpdateSource(sourceId);

  // Flatten catalog pages with deduplication to prevent duplicate React keys
  const allEntries = useMemo(() => {
    if (!catalogData?.pages) return [];
    const seen = new Set<string>();
    return catalogData.pages
      .flatMap((page) => page.items)
      .filter((entry) => {
        if (seen.has(entry.id)) return false;
        seen.add(entry.id);
        return true;
      });
  }, [catalogData]);

  // Filter by search and sort (client-side)
  const filteredEntries = useMemo(() => {
    let entries = allEntries;

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      entries = entries.filter(
        (entry) =>
          entry.name.toLowerCase().includes(query) ||
          entry.path.toLowerCase().includes(query)
      );
    }

    // Sort based on sortOption
    return [...entries].sort((a, b) => {
      switch (sortOption) {
        case 'confidence-desc':
          return b.confidence_score - a.confidence_score;
        case 'confidence-asc':
          return a.confidence_score - b.confidence_score;
        case 'name-asc':
          return a.name.localeCompare(b.name);
        case 'name-desc':
          return b.name.localeCompare(a.name);
        case 'date-added':
          return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime();
        default:
          return b.confidence_score - a.confidence_score;
      }
    });
  }, [allEntries, searchQuery, sortOption]);

  // Separate excluded entries for the excluded list (P4.4b: filter duplicates)
  const excludedEntries = useMemo(() => {
    const excluded = allEntries.filter((entry) => entry.status === 'excluded');

    // Apply duplicate filter if enabled
    if (showOnlyDuplicates) {
      return excluded.filter((entry) => entry.is_duplicate === true);
    }

    return excluded;
  }, [allEntries, showOnlyDuplicates]);

  // Pagination calculations
  const totalFilteredCount = filteredEntries.length;
  const totalPages = Math.ceil(totalFilteredCount / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = Math.min(startIndex + itemsPerPage, totalFilteredCount);

  // Paginated entries for display
  const paginatedEntries = useMemo(() => {
    return filteredEntries.slice(startIndex, endIndex);
  }, [filteredEntries, startIndex, endIndex]);

  // Ensure current page is valid when data changes
  useEffect(() => {
    if (totalPages > 0 && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  // Fetch more pages if needed for pagination
  // Load more data when user navigates to a page beyond loaded data
  useEffect(() => {
    if (hasNextPage && endIndex >= allEntries.length && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, endIndex, allEntries.length, isFetchingNextPage, fetchNextPage]);

  // Get counts from first page
  const countsByStatus = catalogData?.pages[0]?.counts_by_status || {};

  // Get total count from first page (stays consistent across pagination)
  // This is the total number of catalog entries matching current filters
  const totalCount = catalogData?.pages[0]?.page_info?.total_count;

  // Selection handlers
  const handleSelectEntry = (entryId: string, selected: boolean) => {
    setSelectedEntries((prev) => {
      const next = new Set(prev);
      if (selected) {
        next.add(entryId);
      } else {
        next.delete(entryId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    const importableEntries = filteredEntries.filter(
      (e) => e.status === 'new' || e.status === 'updated'
    );
    if (selectedEntries.size === importableEntries.length) {
      setSelectedEntries(new Set());
    } else {
      setSelectedEntries(new Set(importableEntries.map((e) => e.id)));
    }
  };

  const handleImportSelected = async () => {
    if (selectedEntries.size === 0) return;

    await importMutation.mutateAsync({
      entry_ids: Array.from(selectedEntries),
      conflict_strategy: 'skip',
    });

    setSelectedEntries(new Set());
  };

  const handleImportSingle = async (entryId: string) => {
    await importMutation.mutateAsync({
      entry_ids: [entryId],
      conflict_strategy: 'skip',
    });
  };

  // Directory mapping handlers
  const handleOpenDirectoryMap = async () => {
    if (!source) return;

    setDirectoryMapModalOpen(true);
    setIsLoadingTree(true);
    setTreeError(undefined);

    try {
      // Fetch GitHub tree data
      const response = await fetch(
        `https://api.github.com/repos/${source.owner}/${source.repo_name}/git/trees/${source.ref}?recursive=1`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch repository tree: ${response.statusText}`);
      }

      const data = await response.json();
      setTreeData(data.tree || []);
    } catch (error) {
      setTreeError(error instanceof Error ? error.message : 'Failed to load directory tree');
    } finally {
      setIsLoadingTree(false);
    }
  };

  const handleConfirmMappings = async (mappings: Record<string, string>) => {
    await updateSourceMutation.mutateAsync({
      manual_map: mappings,
    });
  };

  const handleConfirmAndRescan = async (mappings: Record<string, string>) => {
    await updateSourceMutation.mutateAsync({
      manual_map: mappings,
    });
    const result = await rescanMutation.mutateAsync({
      manual_map: mappings,
    });
    setLastScanResult(result);
  };

  // Store scan result when rescan completes (P4.3b)
  const handleRescan = async () => {
    const result = await rescanMutation.mutateAsync({});
    setLastScanResult(result);
  };

  // Pagination handlers
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleItemsPerPageChange = (value: string) => {
    const newLimit = parseInt(value, 10);
    setItemsPerPage(newLimit);
    setCurrentPage(1); // Reset to first page when changing items per page
  };

  // Generate page numbers to display (max 5 visible + ellipsis)
  const getPageNumbers = (): (number | 'ellipsis')[] => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages: (number | 'ellipsis')[] = [];

    if (currentPage <= 3) {
      // Near start: show 1 2 3 4 5 ... last
      pages.push(1, 2, 3, 4, 5);
      if (totalPages > 5) {
        pages.push('ellipsis', totalPages);
      }
    } else if (currentPage >= totalPages - 2) {
      // Near end: show 1 ... last-4 last-3 last-2 last-1 last
      pages.push(1, 'ellipsis');
      for (let i = totalPages - 4; i <= totalPages; i++) {
        if (i > 1) pages.push(i);
      }
    } else {
      // Middle: show 1 ... current-1 current current+1 ... last
      pages.push(1, 'ellipsis');
      pages.push(currentPage - 1, currentPage, currentPage + 1);
      pages.push('ellipsis', totalPages);
    }

    return pages;
  };

  // Loading state
  if (sourceLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-20 w-full" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <CatalogCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (sourceError || !source) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertTriangle className="mb-4 h-12 w-12 text-destructive" />
        <h2 className="text-lg font-semibold">Source not found</h2>
        <p className="text-muted-foreground">
          {sourceError instanceof Error ? sourceError.message : 'Unable to load source'}
        </p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push('/marketplace/sources')}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Sources
        </Button>
      </div>
    );
  }

  const importableCount = filteredEntries.filter(
    (e) => e.status === 'new' || e.status === 'updated'
  ).length;

  const excludedCount = filteredEntries.filter(
    (e) => e.status === 'excluded'
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Button
            variant="ghost"
            size="sm"
            className="mb-2 -ml-2"
            onClick={() => router.push('/marketplace/sources')}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Sources
          </Button>
          <div className="flex items-center gap-3">
            <Github className="h-8 w-8" />
            <div>
              <h1 className="text-2xl font-bold">
                {source.owner}/{source.repo_name}
              </h1>
              <p className="text-sm text-muted-foreground">
                {source.ref}
                {source.root_hint && ` • ${source.root_hint}`}
              </p>
              {/* Description */}
              {source.description && (
                <p className="mt-2 text-muted-foreground">
                  {source.description}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleRescan}
            disabled={rescanMutation.isPending}
          >
            <RefreshCw className={cn('mr-2 h-4 w-4', rescanMutation.isPending && 'animate-spin')} />
            {rescanMutation.isPending ? 'Scanning...' : 'Rescan'}
          </Button>
          <a
            href={source.repo_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline">
              <Github className="mr-2 h-4 w-4" />
              View Repo
            </Button>
          </a>
          <Button
            variant="outline"
            onClick={() => setEditModalOpen(true)}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(countsByStatus).map(([status, count]) => (
          <Badge
            key={status}
            variant="outline"
            className={cn(
              'cursor-pointer',
              filters.status === status && 'ring-2 ring-primary'
            )}
            onClick={() =>
              setFilters((prev) => ({
                ...prev,
                status: prev.status === status ? undefined : (status as CatalogStatus),
              }))
            }
          >
            {status}: {count}
          </Badge>
        ))}
      </div>

      {/* Manual Mappings Display (P4.3a) - Collapsible */}
      {source.manual_map && Object.keys(source.manual_map).length > 0 && (
        <Collapsible open={isMappingsOpen} onOpenChange={setIsMappingsOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
              aria-label={isMappingsOpen ? 'Collapse directory mappings' : 'Expand directory mappings'}
            >
              {isMappingsOpen ? (
                <ChevronUp className="h-4 w-4" aria-hidden="true" />
              ) : (
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              )}
              View Mappings ({Object.keys(source.manual_map).length})
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3">
            <Card className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-medium mb-1">Directory Mappings</h3>
                  <p className="text-sm text-muted-foreground">
                    Manual artifact type mappings for specific directories
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleOpenDirectoryMap}
                  >
                    <Pencil className="mr-2 h-4 w-4" />
                    Edit Mappings
                  </Button>
                </div>
              </div>
              <div className="grid gap-2">
                {Object.entries(source.manual_map).map(([directory, artifactType]) => (
                  <div
                    key={directory}
                    className="flex items-center justify-between p-2 rounded-md bg-muted/50"
                  >
                    <code className="text-sm font-mono">{directory}</code>
                    <Badge variant="secondary">{artifactType}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Scan Result with Dedup Stats (P4.3b) */}
      {lastScanResult && (
        <Card className="p-4 border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800">
          <div className="space-y-3">
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <h3 className="font-medium mb-1">Scan Completed Successfully</h3>
                <p className="text-sm text-muted-foreground">
                  {new Date(lastScanResult.scanned_at).toLocaleString()}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setLastScanResult(null)}
              >
                Dismiss
              </Button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="text-center p-2 bg-white dark:bg-gray-900 rounded">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {lastScanResult.artifacts_found}
                </div>
                <div className="text-xs text-muted-foreground">Total Found</div>
              </div>
              <div className="text-center p-2 bg-white dark:bg-gray-900 rounded">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {lastScanResult.new_count}
                </div>
                <div className="text-xs text-muted-foreground">New</div>
              </div>
              <div className="text-center p-2 bg-white dark:bg-gray-900 rounded">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {lastScanResult.updated_count}
                </div>
                <div className="text-xs text-muted-foreground">Updated</div>
              </div>
              <div className="text-center p-2 bg-white dark:bg-gray-900 rounded">
                <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {lastScanResult.unchanged_count}
                </div>
                <div className="text-xs text-muted-foreground">Unchanged</div>
              </div>
            </div>

            {/* Deduplication Stats */}
            {(lastScanResult.duplicates_within_source > 0 || lastScanResult.duplicates_cross_source > 0) && (
              <div className="border-t pt-3">
                <h4 className="text-sm font-medium mb-2">Deduplication</h4>
                <div className="grid grid-cols-2 gap-3">
                  {lastScanResult.duplicates_within_source > 0 && (
                    <div className="text-center p-2 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded">
                      <div className="text-xl font-bold text-yellow-700 dark:text-yellow-400">
                        {lastScanResult.duplicates_within_source}
                      </div>
                      <div className="text-xs text-muted-foreground">Within-Source Duplicates</div>
                    </div>
                  )}
                  {lastScanResult.duplicates_cross_source > 0 && (
                    <div className="text-center p-2 bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 rounded">
                      <div className="text-xl font-bold text-purple-700 dark:text-purple-400">
                        {lastScanResult.duplicates_cross_source}
                      </div>
                      <div className="text-xs text-muted-foreground">Cross-Source Duplicates</div>
                    </div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {lastScanResult.total_detected} total detected, {lastScanResult.total_unique} unique artifacts added to catalog
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Source Toolbar */}
      <SourceToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedType={filters.artifact_type ?? null}
        onTypeChange={(type) => setFilters(prev => ({ ...prev, artifact_type: type as ArtifactType | undefined }))}
        countsByType={catalogData?.pages?.[0]?.counts_by_type ?? {}}
        sortOption={sortOption}
        onSortChange={setSortOption}
        minConfidence={confidenceFilters.minConfidence}
        maxConfidence={confidenceFilters.maxConfidence}
        onMinConfidenceChange={(v) => setConfidenceFilters(prev => ({ ...prev, minConfidence: v }))}
        onMaxConfidenceChange={(v) => setConfidenceFilters(prev => ({ ...prev, maxConfidence: v }))}
        includeBelowThreshold={confidenceFilters.includeBelowThreshold}
        onIncludeBelowThresholdChange={(v) =>
          setConfidenceFilters(prev => ({
            ...prev,
            includeBelowThreshold: v,
            minConfidence: v ? 1 : 50  // Set to 1% when on, 50% when off
          }))
        }
        showOnlyDuplicates={showOnlyDuplicates}
        onShowOnlyDuplicatesChange={setShowOnlyDuplicates}
        selectedCount={selectedEntries.size}
        totalSelectableCount={importableCount}
        allSelected={selectedEntries.size === importableCount && importableCount > 0}
        onSelectAll={handleSelectAll}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        hasActiveFilters={
          !!filters.artifact_type ||
          !!filters.status ||
          confidenceFilters.minConfidence !== 50 ||
          confidenceFilters.maxConfidence !== 100 ||
          confidenceFilters.includeBelowThreshold ||
          showOnlyDuplicates ||
          sortOption !== 'confidence-desc' ||
          searchQuery.trim() !== ''
        }
        onClearFilters={() => {
          setFilters({});
          setConfidenceFilters({
            minConfidence: 50,
            maxConfidence: 100,
            includeBelowThreshold: false,
          });
          setShowOnlyDuplicates(false);
          setSortOption('confidence-desc');
          setSearchQuery('');
        }}
        onMapDirectories={handleOpenDirectoryMap}
      />

      {/* Refetching indicator */}
      {catalogFetching && !catalogLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground px-4">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Updating results...</span>
        </div>
      )}

      {/* Bulk import action (shown when items selected) */}
      {selectedEntries.size > 0 && (
        <div className="flex items-center gap-2 px-4">
          <Button
            size="sm"
            onClick={handleImportSelected}
            disabled={importMutation.isPending}
          >
            {importMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Import {selectedEntries.size} selected
              </>
            )}
          </Button>
          {excludedCount > 0 && (
            <span className="text-sm text-muted-foreground">
              {excludedCount} excluded
            </span>
          )}
        </div>
      )}

      {/* Notes Section */}
      {source.notes && (
        <Card className="p-4">
          <div className="flex items-start gap-2">
            <StickyNote className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium mb-1">Notes</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {source.notes}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Artifact Count Indicator */}
      {!catalogLoading && filteredEntries.length > 0 && (
        <div className="flex items-center py-2 text-sm text-muted-foreground">
          <span>
            Showing {startIndex + 1}-{endIndex} of{' '}
            {totalFilteredCount.toLocaleString()} artifacts
            {totalCount && totalFilteredCount !== totalCount && (
              <> (filtered from {totalCount.toLocaleString()} total)</>
            )}
          </span>
        </div>
      )}

      {/* Catalog Grid/List */}
      {catalogLoading ? (
        viewMode === 'grid' ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <CatalogCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <CatalogList
            entries={[]}
            sourceId={sourceId}
            selectedEntries={selectedEntries}
            onSelectEntry={handleSelectEntry}
            onImportSingle={handleImportSingle}
            onEntryClick={(entry) => {
              setSelectedEntry(entry);
              setModalOpen(true);
            }}
            isImporting={importMutation.isPending}
            isLoading={true}
          />
        )
      ) : filteredEntries.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Filter className="mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="mb-2 text-lg font-semibold">No artifacts found</h3>
          <p className="text-sm text-muted-foreground">
            {allEntries.length === 0
              ? 'No artifacts detected in this repository. Try rescanning.'
              : 'Try adjusting your filters.'}
          </p>
        </div>
      ) : (
        <>
          <div className="max-h-[600px] overflow-y-auto">
            {viewMode === 'grid' ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {paginatedEntries.map((entry) => (
                  <CatalogCard
                    key={entry.id}
                    entry={entry}
                    sourceId={sourceId}
                    selected={selectedEntries.has(entry.id)}
                    onSelect={(selected) => handleSelectEntry(entry.id, selected)}
                    onImport={() => handleImportSingle(entry.id)}
                    isImporting={importMutation.isPending}
                    onClick={() => {
                      setSelectedEntry(entry);
                      setModalOpen(true);
                    }}
                  />
                ))}
              </div>
            ) : (
              <CatalogList
                entries={paginatedEntries}
                sourceId={sourceId}
                selectedEntries={selectedEntries}
                onSelectEntry={handleSelectEntry}
                onImportSingle={handleImportSingle}
                onEntryClick={(entry) => {
                  setSelectedEntry(entry);
                  setModalOpen(true);
                }}
                isImporting={importMutation.isPending}
              />
            )}
          </div>

          {/* Pagination Controls */}
          {totalPages > 0 && (
            <div className="sticky bottom-0 mt-6 -mx-6 px-6 py-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t border-border/40 shadow-[0_-2px_10px_rgba(0,0,0,0.05)] dark:shadow-[0_-2px_10px_rgba(0,0,0,0.2)]">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                {/* Items per page selector */}
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Show</span>
                  <Select
                    value={itemsPerPage.toString()}
                    onValueChange={handleItemsPerPageChange}
                  >
                    <SelectTrigger className="w-[80px] h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="25">25</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                  <span className="text-muted-foreground">per page</span>
                </div>

                {/* Page navigation */}
                <div className="flex items-center gap-1">
                  {/* Previous button */}
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 1}
                    onClick={() => handlePageChange(currentPage - 1)}
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>

                  {/* Page numbers */}
                  {getPageNumbers().map((pageNum, index) =>
                    pageNum === 'ellipsis' ? (
                      <span
                        key={`ellipsis-${index}`}
                        className="px-2 text-muted-foreground"
                        aria-hidden="true"
                      >
                        ...
                      </span>
                    ) : (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        aria-label={`Page ${pageNum}`}
                        aria-current={currentPage === pageNum ? 'page' : undefined}
                        className="min-w-[36px]"
                      >
                        {pageNum}
                      </Button>
                    )
                  )}

                  {/* Next button */}
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === totalPages}
                    onClick={() => handlePageChange(currentPage + 1)}
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>

                {/* Loading indicator when fetching more data */}
                {isFetchingNextPage && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Loading more...</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Excluded Artifacts List */}
      <ExcludedArtifactsList
        entries={excludedEntries}
        sourceId={sourceId}
      />

      {/* Edit Modal */}
      <EditSourceModal
        source={source}
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
      />

      {/* Delete Dialog */}
      <DeleteSourceDialog
        source={source}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onSuccess={() => router.push('/marketplace/sources')}
      />

      {/* Catalog Entry Modal */}
      <CatalogEntryModal
        entry={selectedEntry}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onImport={(entry) => handleImportSingle(entry.id)}
        isImporting={importMutation.isPending}
        onEntryUpdated={(updatedEntry) => setSelectedEntry(updatedEntry)}
      />

      {/* Directory Map Modal */}
      <DirectoryMapModal
        open={directoryMapModalOpen}
        onOpenChange={setDirectoryMapModalOpen}
        sourceId={sourceId}
        repoInfo={source ? {
          owner: source.owner,
          repo: source.repo_name,
          ref: source.ref,
        } : undefined}
        treeData={treeData}
        isLoadingTree={isLoadingTree}
        treeError={treeError}
        initialMappings={source?.manual_map || {}}
        onConfirm={handleConfirmMappings}
        onConfirmAndRescan={handleConfirmAndRescan}
      />
    </div>
  );
}
