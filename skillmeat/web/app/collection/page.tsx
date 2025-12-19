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
import { TagFilterBar } from '@/components/ui/tag-filter-popover';
import { EntityLifecycleProvider } from '@/hooks/useEntityLifecycle';
import { useCollectionContext } from '@/hooks/use-collection-context';
import { useArtifacts } from '@/hooks/useArtifacts';
import { useToast } from '@/hooks/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import type { Artifact, ArtifactFilters } from '@/types/artifact';
import type { Entity } from '@/types/entity';

type ViewMode = 'grid' | 'list' | 'grouped';

// Helper function to convert Artifact to Entity for the modal
function artifactToEntity(artifact: Artifact): Entity {
  const statusMap: Record<string, Entity['status']> = {
    active: 'synced',
    outdated: 'outdated',
    conflict: 'conflict',
    error: 'conflict',
  };

  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,
    collection: 'default',
    status: statusMap[artifact.status] || 'synced',
    tags: artifact.metadata.tags || [],
    description: artifact.metadata.description,
    version: artifact.version || artifact.metadata.version,
    source: artifact.source || 'unknown',
    deployedAt: artifact.createdAt,
    modifiedAt: artifact.updatedAt,
    aliases: artifact.aliases || [],
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
  const [sortField, setSortField] = useState('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

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

  // Fetch artifacts using existing hook
  // Note: For now using useArtifacts since it returns full Artifact objects
  // In the future, this can be enhanced to filter by selectedCollectionId
  const { data, isLoading: isLoadingArtifacts, error, refetch } = useArtifacts(
    filters,
    { field: sortField as any, order: sortOrder }
  );

  // Initialize lastUpdated on first load
  useEffect(() => {
    if (data && !lastUpdated) {
      setLastUpdated(new Date());
    }
  }, [data, lastUpdated]);

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
    let artifacts = data?.artifacts ?? [];

    // Search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      artifacts = artifacts.filter(
        (a) =>
          a.name.toLowerCase().includes(query) ||
          a.metadata.description?.toLowerCase().includes(query) ||
          a.metadata.tags?.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    // Tag filter
    if (selectedTags.length > 0) {
      artifacts = artifacts.filter((artifact) =>
        // Check if artifact has any of the selected tags
        artifact.metadata.tags?.some((tag) => selectedTags.includes(tag))
      );
    }

    // Note: Sort is already handled by the useArtifacts hook
    // but we could add additional client-side sorting here if needed

    return artifacts;
  }, [data?.artifacts, searchQuery, selectedTags]);

  const handleArtifactClick = (artifact: Artifact) => {
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
            title="No artifacts"
            description={
              searchQuery || selectedTags.length > 0
                ? 'No artifacts match your filters'
                : 'Add artifacts to get started'
            }
          />
        )}

        {/* Artifacts View */}
        {!error && !isLoadingArtifacts && filteredArtifacts.length > 0 && (
          <>
            {viewMode === 'grid' ? (
              <ArtifactGrid
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
                showCollectionBadge={isAllCollections}
                onCollectionClick={handleCollectionClick}
              />
            ) : viewMode === 'list' ? (
              <ArtifactList
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
                showCollectionColumn={isAllCollections}
                onCollectionClick={handleCollectionClick}
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
              />
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
