'use client';

import { useState, useEffect, useMemo, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Package, Loader2 } from 'lucide-react';
import { CollectionHeader } from '@/components/collection/collection-header';
import { CollectionToolbar } from '@/components/collection/collection-toolbar';
import { ArtifactGrid } from '@/components/collection/artifact-grid';
import { ArtifactList } from '@/components/collection/artifact-list';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import { EditCollectionDialog } from '@/components/collection/edit-collection-dialog';
import { CreateCollectionDialog } from '@/components/collection/create-collection-dialog';
import { MoveCopyDialog } from '@/components/collection/move-copy-dialog';
import { AddToGroupDialog } from '@/components/collection/add-to-group-dialog';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { ParameterEditorModal } from '@/components/discovery/ParameterEditorModal';
import { TagFilterBar } from '@/components/ui/tag-filter-popover';
import {
  EntityLifecycleProvider,
  useCollectionContext,
  useInfiniteArtifacts,
  useInfiniteCollectionArtifacts,
  useIntersectionObserver,
  useEditArtifactParameters,
  useToast,
} from '@/hooks';
import { Skeleton } from '@/components/ui/skeleton';
import type { Artifact, ArtifactFilters } from '@/types/artifact';
import type { ArtifactParameters } from '@/types/discovery';

type ViewMode = 'grid' | 'list' | 'grouped';

/**
 * Enrich ArtifactSummary with full Artifact data
 *
 * When viewing a specific collection, the API returns lightweight ArtifactSummary objects.
 * This function enriches them with full Artifact data from the catalog for consistent UI rendering.
 *
 * @param summary - Lightweight artifact summary from collection endpoint
 * @param allArtifacts - Full artifact list from catalog
 * @param collectionInfo - Optional collection context to attach
 * @returns Full Artifact object or enriched fallback
 */
function enrichArtifactSummary(
  summary: { name: string; type: string; version?: string | null; source: string },
  allArtifacts: Artifact[],
  collectionInfo?: { id: string; name: string }
): Artifact {
  // Try to find matching full artifact by name and type
  const fullArtifact = allArtifacts.find((a) => a.name === summary.name && a.type === summary.type);

  if (fullArtifact) {
    // If we have collection context and the full artifact lacks it, add it
    if (collectionInfo && !fullArtifact.collection) {
      return { ...fullArtifact, collection: collectionInfo };
    }
    return fullArtifact;
  }

  // Fallback: Convert summary to Artifact-like structure with defaults
  // This ensures cards still render even if full data isn't available
  // Note: source may be in "type:name" format if backend doesn't have the real source
  // We detect this and leave source empty rather than showing the ID format
  const artifactId = `${summary.type}:${summary.name}`;
  const isSourceMissingOrSynthetic =
    !summary.source || summary.source === artifactId || summary.source === summary.name;

  return {
    id: artifactId,
    name: summary.name,
    type: summary.type as any,
    scope: 'user',
    status: 'active',
    version: summary.version || undefined,
    // If source looks like the ID format, don't use it - prefer undefined
    source: isSourceMissingOrSynthetic ? undefined : summary.source,
    metadata: {
      title: summary.name,
      description: '',
      tags: [],
    },
    upstreamStatus: {
      hasUpstream: false,
      isOutdated: false,
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: 0,
      usageCount: 0,
    },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    aliases: [],
    collection: collectionInfo,
  };
}

function CollectionPageSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
      </div>
      <div className="border-b bg-muted/30 px-6 py-3">
        <Skeleton className="h-10 w-full" />
      </div>
      <div className="flex-1 overflow-auto p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex h-full items-center justify-center py-12">
      <div className="text-center">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function CollectionPageContent() {
  const { selectedCollectionId, currentCollection, isLoadingCollection, setSelectedCollectionId } =
    useCollectionContext();

  const { toast } = useToast();
  const searchParams = useSearchParams();
  const router = useRouter();

  // View mode with localStorage persistence
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  // Sync from localStorage after mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('collection-view-mode');
      if (stored && ['grid', 'list', 'grouped'].includes(stored)) {
        setViewMode(stored as ViewMode);
      }
    }
  }, []);

  // Persist view mode changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('collection-view-mode', viewMode);
    }
  }, [viewMode]);

  // Filters, search, sort state
  const [filters, setFilters] = useState<ArtifactFilters>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('confidence');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Tag filtering from URL
  const selectedTags = useMemo(() => {
    return searchParams.get('tags')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Refresh state
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Modal state
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // State for artifact actions from dropdown menu
  const [artifactToDelete, setArtifactToDelete] = useState<Artifact | null>(null);
  const [artifactToEdit, setArtifactToEdit] = useState<Artifact | null>(null);
  const [showDeletionDialog, setShowDeletionDialog] = useState(false);
  const [showParameterEditor, setShowParameterEditor] = useState(false);

  // State for Move/Copy dialog
  const [showMoveCopyDialog, setShowMoveCopyDialog] = useState(false);
  const [artifactForCollection, setArtifactForCollection] = useState<Artifact | null>(null);

  // State for Manage Groups dialog
  const [showGroupsDialog, setShowGroupsDialog] = useState(false);
  const [artifactForGroups, setArtifactForGroups] = useState<Artifact | null>(null);

  // Hook for editing artifact parameters
  const { mutateAsync: updateParameters } = useEditArtifactParameters();

  // Handler for Edit action from dropdown
  const handleEditFromDropdown = (artifact: Artifact) => {
    setArtifactToEdit(artifact);
    setShowParameterEditor(true);
  };

  // Handler for Delete action from dropdown
  const handleDeleteFromDropdown = (artifact: Artifact) => {
    setArtifactToDelete(artifact);
    setShowDeletionDialog(true);
  };

  // Handler for Move to Collection action from dropdown
  const handleMoveToCollection = (artifact: Artifact) => {
    setArtifactForCollection(artifact);
    setShowMoveCopyDialog(true);
  };

  // Handler for Manage Groups action from dropdown
  const handleManageGroups = (artifact: Artifact) => {
    setArtifactForGroups(artifact);
    setShowGroupsDialog(true);
  };

  // Handler to save parameters (same pattern as unified-entity-modal.tsx)
  const handleSaveParameters = async (parameters: ArtifactParameters) => {
    if (!artifactToEdit) return;

    try {
      await updateParameters({
        artifactId: artifactToEdit.id,
        parameters,
      });

      toast({
        title: 'Parameters Updated',
        description: `Successfully updated parameters for ${artifactToEdit.name}`,
      });

      setShowParameterEditor(false);
      setArtifactToEdit(null);
      refetch(); // Refresh artifact list
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to update parameters',
        variant: 'destructive',
      });
    }
  };

  // Determine if viewing a specific collection or "All Collections"
  const isSpecificCollection = !!selectedCollectionId && selectedCollectionId !== 'all';

  // Conditionally fetch artifacts based on selected collection
  // Both views use infinite scroll pagination for better performance

  // Fetch artifacts for a specific collection (with infinite scroll)
  const {
    data: infiniteCollectionData,
    isLoading: isLoadingCollectionArtifacts,
    error: collectionError,
    refetch: refetchCollectionArtifacts,
    fetchNextPage: fetchNextCollectionPage,
    hasNextPage: hasNextCollectionPage,
    isFetchingNextPage: isFetchingNextCollectionPage,
  } = useInfiniteCollectionArtifacts(isSpecificCollection ? selectedCollectionId : undefined, {
    limit: 20,
    enabled: isSpecificCollection,
  });

  // Fetch all artifacts with infinite scroll (for "All Collections" mode)
  // Also used to enrich collection artifacts with full metadata
  const {
    data: infiniteAllArtifactsData,
    isLoading: isLoadingAllArtifacts,
    error: allArtifactsError,
    refetch: refetchAllArtifacts,
    fetchNextPage: fetchNextAllPage,
    hasNextPage: hasNextAllPage,
    isFetchingNextPage: isFetchingNextAllPage,
  } = useInfiniteArtifacts({
    limit: 20,
    artifact_type: filters.type !== 'all' ? filters.type : undefined,
    enabled: true, // Always fetch to support enrichment
  });

  // Unified pagination state based on current view
  const fetchNextPage = isSpecificCollection ? fetchNextCollectionPage : fetchNextAllPage;
  const hasNextPage = isSpecificCollection ? hasNextCollectionPage : hasNextAllPage;
  const isFetchingNextPage = isSpecificCollection
    ? isFetchingNextCollectionPage
    : isFetchingNextAllPage;

  // Set up intersection observer for infinite scroll (works for BOTH views)
  const { targetRef, isIntersecting } = useIntersectionObserver<HTMLDivElement>({
    rootMargin: '200px',
    enabled: hasNextPage && !isFetchingNextPage,
  });

  // Trigger fetch when intersection observer detects scroll near bottom
  useEffect(() => {
    if (isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
      // When viewing a specific collection, also fetch more full artifacts for enrichment
      // This ensures metadata is available for artifacts beyond the initial page
      if (isSpecificCollection && hasNextAllPage && !isFetchingNextAllPage) {
        fetchNextAllPage();
      }
    }
  }, [
    isIntersecting,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isSpecificCollection,
    hasNextAllPage,
    isFetchingNextAllPage,
    fetchNextAllPage,
  ]);

  // Select the appropriate loading state and error based on selection
  const isLoadingArtifacts = isSpecificCollection
    ? isLoadingCollectionArtifacts
    : isLoadingAllArtifacts;
  const error = isSpecificCollection ? collectionError : allArtifactsError;
  const refetch = isSpecificCollection ? refetchCollectionArtifacts : refetchAllArtifacts;

  // Get total count for display (from first page's page_info)
  const totalCount = isSpecificCollection
    ? (infiniteCollectionData?.pages[0]?.page_info.total_count ?? 0)
    : (infiniteAllArtifactsData?.pages[0]?.page_info.total_count ?? 0);

  // Initialize lastUpdated on first load
  useEffect(() => {
    const hasData = isSpecificCollection ? infiniteCollectionData : infiniteAllArtifactsData;
    if (hasData && !lastUpdated) {
      setLastUpdated(new Date());
    }
  }, [infiniteCollectionData, infiniteAllArtifactsData, isSpecificCollection, lastUpdated]);

  // Handle tag selection changes
  const handleTagsChange = (tags: string[]) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tags.length > 0) {
      params.set('tags', tags.join(','));
    } else {
      params.delete('tags');
    }
    router.push(`?${params.toString()}`);
  };

  // Helper function to map API artifact response to Artifact type
  const mapApiArtifactToArtifact = (apiArtifact: {
    id: string;
    name: string;
    type: string;
    source: string;
    version?: string;
    tags?: string[];
    aliases?: string[];
    origin?: string;
    origin_source?: string | null;
    metadata?: {
      title?: string;
      description?: string;
      license?: string;
      author?: string;
      version?: string;
      tags?: string[];
    };
    upstream?: {
      tracking_enabled: boolean;
      current_sha?: string;
      upstream_sha?: string;
      update_available: boolean;
      has_local_modifications: boolean;
    };
    added: string;
    updated: string;
    collection?: { id: string; name: string };
    collections?: Array<{ id: string; name: string; artifact_count?: number }>;
  }): Artifact => {
    const metadata = apiArtifact.metadata || {};
    const upstream = apiArtifact.upstream;
    const isOutdated = upstream?.update_available ?? false;

    // Merge tags from artifact level and metadata level
    const artifactTags = apiArtifact.tags || [];
    const metadataTags = metadata.tags || [];
    const mergedTags: string[] = [];
    const seenTags = new Set<string>();
    for (const tag of [...artifactTags, ...metadataTags]) {
      const normalized = tag?.trim();
      if (!normalized || seenTags.has(normalized)) continue;
      seenTags.add(normalized);
      mergedTags.push(normalized);
    }

    return {
      id: apiArtifact.id,
      name: apiArtifact.name,
      type: apiArtifact.type as any,
      scope: apiArtifact.source === 'local' ? 'local' : 'user',
      status: isOutdated ? 'outdated' : 'active',
      version: apiArtifact.version || metadata.version,
      source: apiArtifact.source,
      origin: apiArtifact.origin,
      origin_source: apiArtifact.origin_source || undefined,
      metadata: {
        title: metadata.title || apiArtifact.name,
        description: metadata.description || '',
        license: metadata.license,
        author: metadata.author,
        version: metadata.version || apiArtifact.version,
        tags: mergedTags,
      },
      upstreamStatus: {
        hasUpstream: Boolean(upstream?.tracking_enabled),
        upstreamUrl:
          apiArtifact.source?.startsWith('http') || apiArtifact.source?.includes('github.com')
            ? apiArtifact.source
            : undefined,
        upstreamVersion: upstream?.upstream_sha,
        currentVersion: upstream?.current_sha || apiArtifact.version,
        isOutdated,
        lastChecked: apiArtifact.updated,
      },
      usageStats: {
        totalDeployments: 0,
        activeProjects: 0,
        lastUsed: apiArtifact.updated,
        usageCount: 0,
      },
      createdAt: apiArtifact.added,
      updatedAt: apiArtifact.updated,
      aliases: apiArtifact.aliases || [],
      collection: apiArtifact.collection,
      collections: apiArtifact.collections,
    };
  };

  // Apply client-side search, tag filter, and sort
  const filteredArtifacts = useMemo(() => {
    // Handle different response shapes:
    // - Specific collection (infinite scroll): pages array with items (lightweight summaries)
    // - All collections (infinite scroll): pages array with items (full artifacts)
    let artifacts: Artifact[] = [];

    if (isSpecificCollection && infiniteCollectionData?.pages) {
      // Collection-specific view with infinite scroll: Flatten pages and enrich
      const allSummaries = infiniteCollectionData.pages.flatMap((page) => page.items);

      // Get full artifacts from infiniteAllArtifactsData for enrichment
      const fullArtifacts: Artifact[] = infiniteAllArtifactsData?.pages
        ? infiniteAllArtifactsData.pages.flatMap((page) => page.items.map(mapApiArtifactToArtifact))
        : [];

      // Build collection info from current context to ensure artifacts have collection set
      const collectionInfo = currentCollection
        ? { id: currentCollection.id, name: currentCollection.name }
        : undefined;

      // Enrich each summary with full data from catalog, including collection context
      artifacts = allSummaries.map((summary) =>
        enrichArtifactSummary(summary, fullArtifacts, collectionInfo)
      );

      // Deduplicate by ID to prevent React key conflicts
      const seen = new Set<string>();
      artifacts = artifacts.filter((artifact) => {
        if (seen.has(artifact.id)) {
          return false;
        }
        seen.add(artifact.id);
        return true;
      });
    } else if (!isSpecificCollection && infiniteAllArtifactsData?.pages) {
      // All collections view with infinite scroll: Flatten pages and map to Artifact type
      artifacts = infiniteAllArtifactsData.pages.flatMap((page) =>
        page.items.map(mapApiArtifactToArtifact)
      );

      // Deduplicate by ID
      const seen = new Set<string>();
      artifacts = artifacts.filter((artifact) => {
        if (seen.has(artifact.id)) {
          return false;
        }
        seen.add(artifact.id);
        return true;
      });
    }

    // Type filter
    if (filters.type && filters.type !== 'all') {
      artifacts = artifacts.filter((artifact) => artifact.type === filters.type);
    }

    // Status filter
    if (filters.status && filters.status !== 'all') {
      artifacts = artifacts.filter((artifact) => artifact.status === filters.status);
    }

    // Scope filter
    if (filters.scope && filters.scope !== 'all') {
      artifacts = artifacts.filter((artifact) => artifact.scope === filters.scope);
    }

    // Search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      artifacts = artifacts.filter((a) => {
        const nameMatch = a.name.toLowerCase().includes(query);
        const descMatch = a.metadata?.description?.toLowerCase().includes(query);
        const tagMatch = a.metadata?.tags?.some((tag: string) => tag.toLowerCase().includes(query));
        return nameMatch || descMatch || tagMatch;
      });
    }

    // Tag filter
    if (selectedTags.length > 0) {
      artifacts = artifacts.filter((artifact) => {
        return artifact.metadata?.tags?.some((tag: string) => selectedTags.includes(tag)) ?? false;
      });
    }

    // Apply client-side sorting (confidence sorting requires client-side since backend doesn't support it)
    if (sortField === 'confidence') {
      artifacts = [...artifacts].sort((a, b) => {
        const aConfidence = a.score?.confidence ?? 0;
        const bConfidence = b.score?.confidence ?? 0;
        return sortOrder === 'asc' ? aConfidence - bConfidence : bConfidence - aConfidence;
      });
    } else if (sortField === 'name') {
      artifacts = [...artifacts].sort((a, b) => {
        const comparison = a.name.localeCompare(b.name);
        return sortOrder === 'asc' ? comparison : -comparison;
      });
    } else if (sortField === 'updatedAt') {
      artifacts = [...artifacts].sort((a, b) => {
        const aDate = new Date(a.updatedAt).getTime();
        const bDate = new Date(b.updatedAt).getTime();
        return sortOrder === 'asc' ? aDate - bDate : bDate - aDate;
      });
    } else if (sortField === 'usageCount') {
      artifacts = [...artifacts].sort((a, b) => {
        const aUsage = a.usageStats?.usageCount ?? 0;
        const bUsage = b.usageStats?.usageCount ?? 0;
        return sortOrder === 'asc' ? aUsage - bUsage : bUsage - aUsage;
      });
    }

    return artifacts;
  }, [
    isSpecificCollection,
    infiniteCollectionData,
    infiniteAllArtifactsData,
    currentCollection,
    filters,
    searchQuery,
    selectedTags,
    sortField,
    sortOrder,
  ]);

  // Compute unique tags with counts from ALL loaded artifacts (before tag filtering)
  // This is used by TagFilterPopover instead of fetching from the database Tag table
  const availableTags = useMemo(() => {
    // Get all artifacts before tag filtering is applied
    let allArtifacts: Artifact[] = [];

    if (isSpecificCollection && infiniteCollectionData?.pages) {
      const allSummaries = infiniteCollectionData.pages.flatMap((page) => page.items);
      const fullArtifacts: Artifact[] = infiniteAllArtifactsData?.pages
        ? infiniteAllArtifactsData.pages.flatMap((page) => page.items.map(mapApiArtifactToArtifact))
        : [];
      const collectionInfo = currentCollection
        ? { id: currentCollection.id, name: currentCollection.name }
        : undefined;
      allArtifacts = allSummaries.map((summary) =>
        enrichArtifactSummary(summary, fullArtifacts, collectionInfo)
      );
    } else if (!isSpecificCollection && infiniteAllArtifactsData?.pages) {
      allArtifacts = infiniteAllArtifactsData.pages.flatMap((page) =>
        page.items.map(mapApiArtifactToArtifact)
      );
    }

    // Count tags across all artifacts
    const tagCounts = new Map<string, number>();
    allArtifacts.forEach((artifact) => {
      const tags = artifact.metadata?.tags || [];
      tags.forEach((tag: string) => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    // Convert to array format expected by TagFilterPopover
    return Array.from(tagCounts.entries())
      .map(([name, count]) => ({ name, artifact_count: count }))
      .sort((a, b) => b.artifact_count - a.artifact_count); // Sort by count descending
  }, [
    infiniteCollectionData?.pages,
    infiniteAllArtifactsData?.pages,
    isSpecificCollection,
    currentCollection,
  ]);

  const handleArtifactClick = (artifact: Artifact) => {
    setSelectedArtifact(artifact);
    setIsDetailOpen(true);
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    setTimeout(() => setSelectedArtifact(null), 300);
  };

  const handleSortChange = (field: string, order: 'asc' | 'desc') => {
    setSortField(field);
    setSortOrder(order);
  };

  const handleCollectionClick = (collectionId: string) => {
    setSelectedCollectionId(collectionId);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refetch();
      setLastUpdated(new Date());
      toast({
        title: 'Collection refreshed',
        description: 'Successfully updated artifact collection',
      });
    } catch (err) {
      toast({
        title: 'Refresh failed',
        description: 'Could not refresh collection. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  // Loading state
  if (isLoadingCollection) {
    return <CollectionPageSkeleton />;
  }

  // Determine if "All Collections" mode
  const isAllCollections = !selectedCollectionId;

  return (
    <div className="flex h-full flex-col">
      <CollectionHeader
        collection={currentCollection}
        artifactCount={totalCount}
        isAllCollections={isAllCollections}
        onEdit={currentCollection ? () => setShowEditDialog(true) : undefined}
        onDelete={currentCollection ? () => setShowEditDialog(true) : undefined}
        onCreate={() => setShowCreateDialog(true)}
      />

      <CollectionToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        filters={filters}
        onFiltersChange={setFilters}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sortField={sortField}
        sortOrder={sortOrder}
        onSortChange={handleSortChange}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        lastUpdated={lastUpdated}
        selectedTags={selectedTags}
        onTagsChange={handleTagsChange}
        availableTags={availableTags}
      />

      {/* Tag Filter Bar - Shows active tag filters */}
      {selectedTags.length > 0 && (
        <div className="border-b bg-muted/10 px-6 py-2">
          <TagFilterBar
            selectedTags={selectedTags}
            onChange={handleTagsChange}
            availableTags={availableTags}
          />
        </div>
      )}

      <div className="flex-1 overflow-auto p-6">
        {/* Error State */}
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              Failed to load artifacts. Please try again later.
            </p>
          </div>
        )}

        {/* Loading State */}
        {!error && isLoadingArtifacts && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!error && !isLoadingArtifacts && filteredArtifacts.length === 0 && (
          <EmptyState
            title={
              searchQuery || selectedTags.length > 0
                ? 'No results found'
                : isSpecificCollection
                  ? 'No artifacts in this collection'
                  : 'No artifacts'
            }
            description={
              searchQuery || selectedTags.length > 0
                ? 'Try adjusting your search or filters'
                : isSpecificCollection
                  ? 'Add artifacts to this collection to get started'
                  : 'Add artifacts to get started'
            }
          />
        )}

        {/* Artifacts View */}
        {!error && !isLoadingArtifacts && filteredArtifacts.length > 0 && (
          <>
            {/* Artifact count indicator with pagination info (works for BOTH views) */}
            {totalCount > 0 && (
              <div className="mb-4 text-sm text-muted-foreground">
                Showing {filteredArtifacts.length} of {totalCount} artifacts
                {hasNextPage && ' (scroll for more)'}
              </div>
            )}

            {viewMode === 'grid' ? (
              <ArtifactGrid
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
                showCollectionBadge={isAllCollections}
                onCollectionClick={handleCollectionClick}
                onMoveToCollection={handleMoveToCollection}
                onManageGroups={handleManageGroups}
                onEdit={handleEditFromDropdown}
                onDelete={handleDeleteFromDropdown}
              />
            ) : viewMode === 'list' ? (
              <ArtifactList
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
                showCollectionColumn={isAllCollections}
                onCollectionClick={handleCollectionClick}
                onMoveToCollection={handleMoveToCollection}
                onManageGroups={handleManageGroups}
                onEdit={handleEditFromDropdown}
                onDelete={handleDeleteFromDropdown}
              />
            ) : (
              // Grouped view placeholder for Phase 5
              // For now, show grid view
              <ArtifactGrid
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
                showCollectionBadge={isAllCollections}
                onCollectionClick={handleCollectionClick}
                onMoveToCollection={handleMoveToCollection}
                onManageGroups={handleManageGroups}
                onEdit={handleEditFromDropdown}
                onDelete={handleDeleteFromDropdown}
              />
            )}

            {/* Infinite scroll trigger element - works for BOTH views */}
            <div ref={targetRef} className="flex justify-center py-8" aria-hidden="true">
              {isFetchingNextPage && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="text-sm">Loading more artifacts...</span>
                </div>
              )}
              {!hasNextPage && filteredArtifacts.length > 0 && totalCount > 0 && (
                <span className="text-sm text-muted-foreground">
                  All {totalCount} artifacts loaded
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Artifact Detail Modal */}
      <UnifiedEntityModal
        artifact={selectedArtifact}
        open={isDetailOpen}
        onClose={handleDetailClose}
        onNavigateToSource={(sourceId, artifactPath) => {
          setIsDetailOpen(false);
          setSelectedArtifact(null);
          router.push(`/marketplace/sources/${sourceId}?artifact=${encodeURIComponent(artifactPath)}`);
        }}
        onNavigateToDeployment={(projectPath, artifactId) => {
          setIsDetailOpen(false);
          setSelectedArtifact(null);
          const encodedPath = btoa(projectPath);
          router.push(`/projects/${encodedPath}/manage?artifact=${encodeURIComponent(artifactId)}`);
        }}
      />

      {/* Edit Collection Dialog */}
      {currentCollection && (
        <EditCollectionDialog
          collection={currentCollection}
          open={showEditDialog}
          onOpenChange={setShowEditDialog}
          onSuccess={() => refetch()}
          onDelete={() => refetch()}
        />
      )}

      {/* Create Collection Dialog */}
      <CreateCollectionDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />

      {/* Artifact Parameter Editor - triggered from dropdown */}
      {artifactToEdit && (
        <ParameterEditorModal
          artifact={{
            name: artifactToEdit.name,
            type: artifactToEdit.type,
            source: artifactToEdit.source,
            version: artifactToEdit.version,
            scope: artifactToEdit.scope,
            tags: artifactToEdit.metadata?.tags,
            aliases: artifactToEdit.aliases,
          }}
          open={showParameterEditor}
          onClose={() => {
            setShowParameterEditor(false);
            setArtifactToEdit(null);
          }}
          onSave={handleSaveParameters}
        />
      )}

      {/* Artifact Deletion Dialog - triggered from dropdown */}
      {artifactToDelete && (
        <ArtifactDeletionDialog
          artifact={artifactToDelete}
          open={showDeletionDialog}
          onOpenChange={(open) => {
            setShowDeletionDialog(open);
            if (!open) setArtifactToDelete(null);
          }}
          onSuccess={() => {
            setShowDeletionDialog(false);
            setArtifactToDelete(null);
            refetch(); // Refresh artifact list
          }}
        />
      )}

      {/* Move/Copy to Collection Dialog */}
      {artifactForCollection && (
        <MoveCopyDialog
          open={showMoveCopyDialog}
          onOpenChange={(open) => {
            setShowMoveCopyDialog(open);
            if (!open) setArtifactForCollection(null);
          }}
          artifacts={[artifactForCollection]}
          sourceCollectionId={artifactForCollection.collection?.id}
          onSuccess={() => refetch()}
        />
      )}

      {/* Add to Group Dialog - Now works for both specific collection and All Collections view */}
      {/* When viewing a specific collection, collectionId is passed directly */}
      {/* When viewing All Collections, no collectionId is passed and dialog shows collection picker */}
      {artifactForGroups && (
        <AddToGroupDialog
          open={showGroupsDialog}
          onOpenChange={(open) => {
            setShowGroupsDialog(open);
            if (!open) setArtifactForGroups(null);
          }}
          artifact={artifactForGroups}
          collectionId={isSpecificCollection ? selectedCollectionId : undefined}
          onSuccess={() => refetch()}
        />
      )}
    </div>
  );
}

export default function CollectionPage() {
  return (
    <EntityLifecycleProvider mode="collection">
      <Suspense
        fallback={
          <div className="flex h-screen items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        }
      >
        <CollectionPageContent />
      </Suspense>
    </EntityLifecycleProvider>
  );
}
