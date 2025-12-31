/**
 * Source Detail Page
 *
 * Displays the artifact catalog for a GitHub source with filtering,
 * import functionality, and rescan actions.
 */

'use client';

import { useState, useMemo, useEffect } from 'react';
import { useParams, useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  Github,
  ExternalLink,
  Filter,
  Download,
  CheckSquare,
  Loader2,
  AlertTriangle,
  Search as SearchIcon,
  Pencil,
  Trash2,
  StickyNote,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { CatalogTabs } from './components/catalog-tabs';
import {
  useSource,
  useSourceCatalog,
  useRescanSource,
  useImportArtifacts,
} from '@/hooks/useMarketplaceSources';
import { EditSourceModal } from '@/components/marketplace/edit-source-modal';
import { DeleteSourceDialog } from '@/components/marketplace/delete-source-dialog';
import { CatalogEntryModal } from '@/components/CatalogEntryModal';
import { ConfidenceFilter } from '@/components/ConfidenceFilter';
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
}

function CatalogCard({
  entry,
  selected,
  onSelect,
  onImport,
  isImporting,
  onClick,
}: CatalogCardProps) {
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
  }[entry.status];

  const typeConfig: Record<ArtifactType, { label: string; color: string }> = {
    skill: { label: 'Skill', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
    command: { label: 'Command', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
    agent: { label: 'Agent', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    mcp_server: { label: 'MCP', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
    hook: { label: 'Hook', color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200' },
  };

  return (
    <Card
      className={cn(
        'relative transition-shadow hover:shadow-md cursor-pointer',
        selected && 'ring-2 ring-primary'
      )}
      onClick={onClick}
    >
      <div className="p-4 space-y-3">
        {/* Selection checkbox */}
        <div className="absolute top-3 right-3" onClick={(e) => e.stopPropagation()}>
          <Checkbox
            checked={selected}
            onCheckedChange={onSelect}
            disabled={entry.status === 'removed'}
          />
        </div>

        {/* Header */}
        <div className="pr-8">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className={typeConfig[entry.artifact_type].color}>
              {typeConfig[entry.artifact_type].label}
            </Badge>
            <Badge variant="outline" className={statusConfig.className}>
              {statusConfig.label}
            </Badge>
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
            <ExternalLink className="h-3 w-3" />
            View on GitHub
          </a>
        </div>

        {/* Actions */}
        {entry.status !== 'imported' && entry.status !== 'removed' && (
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
                <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Download className="mr-2 h-3 w-3" />
                Import
              </>
            )}
          </Button>
        )}

        {entry.status === 'imported' && entry.import_date && (
          <p className="text-xs text-muted-foreground text-center">
            Imported {new Date(entry.import_date).toLocaleDateString()}
          </p>
        )}
      </div>
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
  const [confidenceFilters, setConfidenceFilters] = useState(() => ({
    minConfidence: Number(searchParams.get('minConfidence')) || 50,
    maxConfidence: Number(searchParams.get('maxConfidence')) || 100,
    includeBelowThreshold: searchParams.get('includeBelowThreshold') === 'true',
  }));

  // Helper function to update URL parameters
  const updateURLParams = (newConfidenceFilters: typeof confidenceFilters, newFilters: typeof filters) => {
    const params = new URLSearchParams();

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

    // Add type and status filters
    if (newFilters.artifact_type) {
      params.set('type', newFilters.artifact_type);
    }
    if (newFilters.status) {
      params.set('status', newFilters.status);
    }

    const query = params.toString();
    router.replace(`${pathname}${query ? `?${query}` : ''}`, { scroll: false });
  };

  // Sync URL when filters change
  useEffect(() => {
    updateURLParams(confidenceFilters, filters);
  }, [confidenceFilters, filters]);

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

  // Flatten catalog pages
  const allEntries = useMemo(() => {
    return catalogData?.pages.flatMap((page) => page.items) || [];
  }, [catalogData]);

  // Filter by search (client-side)
  const filteredEntries = useMemo(() => {
    if (!searchQuery.trim()) return allEntries;
    const query = searchQuery.toLowerCase();
    return allEntries.filter(
      (entry) =>
        entry.name.toLowerCase().includes(query) ||
        entry.path.toLowerCase().includes(query)
    );
  }, [allEntries, searchQuery]);

  // Get counts from first page
  const countsByStatus = catalogData?.pages[0]?.counts_by_status || {};
  const countsByType = catalogData?.pages[0]?.counts_by_type || {};

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
            onClick={() => rescanMutation.mutate({})}
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

      {/* Filters Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2 relative">
          {/* Refetching indicator */}
          {catalogFetching && !catalogLoading && (
            <div className="absolute -top-6 left-0 flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Updating results...</span>
            </div>
          )}

          {/* Search */}
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search artifacts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 pl-9"
            />
          </div>

          {/* Type filter */}
          <CatalogTabs
            countsByType={catalogData?.pages?.[0]?.counts_by_type ?? {}}
            selectedType={filters.artifact_type ?? null}
            onTypeChange={(type) => setFilters(prev => ({ ...prev, artifact_type: type as ArtifactType | undefined }))}
          />

          {/* Confidence filter */}
          <ConfidenceFilter
            minConfidence={confidenceFilters.minConfidence}
            maxConfidence={confidenceFilters.maxConfidence}
            includeBelowThreshold={confidenceFilters.includeBelowThreshold}
            onMinChange={(v) => setConfidenceFilters(prev => ({ ...prev, minConfidence: v }))}
            onMaxChange={(v) => setConfidenceFilters(prev => ({ ...prev, maxConfidence: v }))}
            onIncludeBelowThresholdChange={(v) =>
              setConfidenceFilters(prev => ({ ...prev, includeBelowThreshold: v }))
            }
          />

          {/* Clear filters */}
          {(filters.artifact_type || filters.status ||
            confidenceFilters.minConfidence !== 50 ||
            confidenceFilters.maxConfidence !== 100 ||
            confidenceFilters.includeBelowThreshold) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFilters({});
                setConfidenceFilters({
                  minConfidence: 50,
                  maxConfidence: 100,
                  includeBelowThreshold: false,
                });
              }}
            >
              Clear filters
            </Button>
          )}
        </div>

        {/* Bulk actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSelectAll}
            disabled={importableCount === 0}
          >
            <CheckSquare className="mr-2 h-4 w-4" />
            {selectedEntries.size === importableCount ? 'Deselect All' : 'Select All'}
          </Button>
          {selectedEntries.size > 0 && (
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
          )}
        </div>
      </div>

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

      {/* Catalog Grid */}
      {catalogLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <CatalogCardSkeleton key={i} />
          ))}
        </div>
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
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredEntries.map((entry) => (
                <CatalogCard
                  key={entry.id}
                  entry={entry}
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
      />
    </div>
  );
}
