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
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { ParameterEditorModal } from '@/components/discovery/ParameterEditorModal';
import { TagFilterBar } from '@/components/ui/tag-filter-popover';
import {
  EntityLifecycleProvider,
  useCollectionContext,
  useArtifacts,
  useInfiniteCollectionArtifacts,
  useIntersectionObserver,
  useEditArtifactParameters,
  useToast,
} from '@/hooks';
import { Skeleton } from '@/components/ui/skeleton';
import type { Artifact, ArtifactFilters } from '@/types/artifact';
import type { Entity } from '@/types/entity';
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
 * @returns Full Artifact object or enriched fallback
 */
function enrichArtifactSummary(
  summary: { name: string; type: string; version?: string | null; source: string },
  allArtifacts: Artifact[],
  collectionInfo?: { id: string; name: string }
): Artifact {
  // Try to find matching full artifact by name and type
  const fullArtifact = allArtifacts.find(a => a.name === summary.name && a.type === summary.type);

  if (fullArtifact) {
    // If we have collection context and the full artifact lacks it, add it
    if (collectionInfo && !fullArtifact.collection) {
      return { ...fullArtifact, collection: collectionInfo };
    }
    return fullArtifact;
  }

  // Fallback: Convert summary to Artifact-like structure with defaults
  // This ensures cards still render even if full data isn't available
  return {
    id: `${summary.type}:${summary.name}`,
    name: summary.name,
    type: summary.type as any,
    scope: 'user',
    status: 'active',
    version: summary.version || undefined,
    source: summary.source,
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

// Helper function to convert Artifact to Entity for the modal
function artifactToEntity(artifact: Artifact): Entity {
  const statusMap: Record<string, Entity['status']> = {
    active: 'synced',
    outdated: 'outdated',
    conflict: 'conflict',
    error: 'conflict',
  };

  // Use artifact's collection name, or 'default' if not available
  // Note: 'discovered' is only for marketplace artifacts on /marketplace page
  // On /collection page, artifacts should always have a collection context
  const collectionName = artifact.collection?.name || 'default';

  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,
    collection: collectionName,
    status: statusMap[artifact.status] || 'synced',
    tags: artifact.metadata?.tags || [],
    description: artifact.metadata?.description,
    version: artifact.version || artifact.metadata?.version,
    source: artifact.source || 'unknown',
    deployedAt: artifact.createdAt,
    modifiedAt: artifact.updatedAt,
    aliases: artifact.aliases || [],
    // Collections array for the Collections tab in unified entity modal
    // Priority: artifact.collections (array) > artifact.collection (single) > empty array
    // TODO: Backend needs to populate artifact.collections with ALL collections the artifact belongs to
    collections: artifact.collections && artifact.collections.length > 0
      ? artifact.collections.map(collection => ({
          id: collection.id,
          name: collection.name,
          artifact_count: collection.artifact_count || 0,
        }))
      : artifact.collection
        ? [
            {
              id: artifact.collection.id,
              name: artifact.collection.name,
              artifact_count: 0, // Not available in artifact context
            },
          ]
        : [],
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
  const {
    selectedCollectionId,
    currentCollection,
    isLoadingCollection,
    setSelectedCollectionId,
  } = useCollectionContext();

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
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // State for artifact actions from dropdown menu
  const [artifactToDelete, setArtifactToDelete] = useState<Artifact | null>(null);
  const [artifactToEdit, setArtifactToEdit] = useState<Artifact | null>(null);
  const [showDeletionDialog, setShowDeletionDialog] = useState(false);
  const [showParameterEditor, setShowParameterEditor] = useState(false);

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
  // When a specific collection is selected, use infinite scroll pagination
  // When "All Collections" or no selection, use general artifacts endpoint
  const {
    data: infiniteCollectionData,
    isLoading: isLoadingInfiniteArtifacts,
    error: infiniteCollectionError,
    refetch: refetchInfiniteArtifacts,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteCollectionArtifacts(
    isSpecificCollection ? selectedCollectionId : undefined,
    { limit: 20, enabled: isSpecificCollection }
  );

  // Fetch all artifacts (used for "All Collections" mode and for enriching collection artifacts)
  const {
    data: allArtifactsData,
    isLoading: isLoadingAllArtifacts,
    error: allArtifactsError,
    refetch: refetchAllArtifacts,
  } = useArtifacts(filters, { field: sortField as any, order: sortOrder });

  // Set up intersection observer for infinite scroll
  const { targetRef, isIntersecting } = useIntersectionObserver<HTMLDivElement>({
    rootMargin: '200px',
    enabled: isSpecificCollection && hasNextPage && !isFetchingNextPage,
  });

  // Trigger fetch when intersection observer detects scroll near bottom
  useEffect(() => {
    if (isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [isIntersecting, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Select the appropriate loading state and error based on selection
  const isLoadingArtifacts = isSpecificCollection
    ? isLoadingInfiniteArtifacts
    : isLoadingAllArtifacts;
  const error = isSpecificCollection ? infiniteCollectionError : allArtifactsError;
  const refetch = isSpecificCollection ? refetchInfiniteArtifacts : refetchAllArtifacts;

  // Get total count for display (from first page's page_info)
  const totalCount = isSpecificCollection
    ? infiniteCollectionData?.pages[0]?.page_info.total_count ?? 0
    : allArtifactsData?.artifacts?.length ?? 0;

  // Initialize lastUpdated on first load
  useEffect(() => {
    const hasData = isSpecificCollection ? infiniteCollectionData : allArtifactsData;
    if (hasData && !lastUpdated) {
      setLastUpdated(new Date());
    }
  }, [infiniteCollectionData, allArtifactsData, isSpecificCollection, lastUpdated]);

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

  // Apply client-side search, tag filter, and sort
  const filteredArtifacts = useMemo(() => {
    // Handle different response shapes:
    // - Specific collection (infinite scroll): pages array with items
    // - All collections: artifacts array
    let artifacts: Artifact[] = [];

    if (isSpecificCollection && infiniteCollectionData?.pages) {
      // Collection-specific view with infinite scroll: Flatten pages and enrich
      const allSummaries = infiniteCollectionData.pages.flatMap(page => page.items);
      const fullArtifacts = allArtifactsData?.artifacts ?? [];

      // Build collection info from current context to ensure artifacts have collection set
      const collectionInfo = currentCollection
        ? { id: currentCollection.id, name: currentCollection.name }
        : undefined;

      // Enrich each summary with full data from catalog, including collection context
      artifacts = allSummaries.map(summary => enrichArtifactSummary(summary, fullArtifacts, collectionInfo));

      // Deduplicate by ID to prevent React key conflicts
      const seen = new Set<string>();
      artifacts = artifacts.filter(artifact => {
        if (seen.has(artifact.id)) {
          return false;
        }
        seen.add(artifact.id);
        return true;
      });
    } else if (!isSpecificCollection && allArtifactsData?.artifacts) {
      // All collections view: Already have full Artifact objects
      artifacts = allArtifactsData.artifacts ?? [];
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
  }, [isSpecificCollection, infiniteCollectionData, allArtifactsData, currentCollection, searchQuery, selectedTags, sortField, sortOrder]);

  const handleArtifactClick = (artifact: Artifact) => {
    // Artifact is now always a full Artifact object due to enrichment in filteredArtifacts
    setSelectedEntity(artifactToEntity(artifact));
    setIsDetailOpen(true);
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    setTimeout(() => setSelectedEntity(null), 300);
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
        artifactCount={filteredArtifacts.length}
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
      />

      {/* Tag Filter Bar - Shows active tag filters */}
      {selectedTags.length > 0 && (
        <div className="border-b px-6 py-2 bg-muted/10">
          <TagFilterBar selectedTags={selectedTags} onChange={handleTagsChange} />
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
            {/* Artifact count indicator for specific collections with pagination */}
            {isSpecificCollection && totalCount > 0 && (
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
                onEdit={handleEditFromDropdown}
                onDelete={handleDeleteFromDropdown}
              />
            )}

            {/* Infinite scroll trigger element - only for specific collections */}
            {isSpecificCollection && (
              <div
                ref={targetRef}
                className="flex justify-center py-8"
                aria-hidden="true"
              >
                {isFetchingNextPage && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span className="text-sm">Loading more artifacts...</span>
                  </div>
                )}
                {!hasNextPage && filteredArtifacts.length > 0 && filteredArtifacts.length === totalCount && (
                  <span className="text-sm text-muted-foreground">
                    All {totalCount} artifacts loaded
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Entity Detail Modal */}
      <UnifiedEntityModal
        entity={selectedEntity}
        open={isDetailOpen}
        onClose={handleDetailClose}
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
      <CreateCollectionDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />

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
