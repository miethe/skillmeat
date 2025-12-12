'use client';

import { useState, useEffect, useMemo } from 'react';
import { Package } from 'lucide-react';
import { CollectionHeader } from '@/components/collection/collection-header';
import { CollectionToolbar } from '@/components/collection/collection-toolbar';
import { ArtifactGrid } from '@/components/collection/artifact-grid';
import { ArtifactList } from '@/components/collection/artifact-list';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import { EntityLifecycleProvider } from '@/hooks/useEntityLifecycle';
import { useCollectionContext } from '@/hooks/use-collection-context';
import { useArtifacts } from '@/hooks/useArtifacts';
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
  } = useCollectionContext();

  // View mode with localStorage persistence
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    if (typeof window === 'undefined') return 'grid';
    const stored = localStorage.getItem('collection-view-mode');
    return (stored as ViewMode) || 'grid';
  });

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

  // Modal state
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Fetch artifacts using existing hook
  // Note: For now using useArtifacts since it returns full Artifact objects
  // In the future, this can be enhanced to filter by selectedCollectionId
  const { data, isLoading: isLoadingArtifacts, error, refetch } = useArtifacts(
    filters,
    { field: sortField as any, order: sortOrder }
  );

  // Apply client-side search and sort
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

    // Note: Sort is already handled by the useArtifacts hook
    // but we could add additional client-side sorting here if needed

    return artifacts;
  }, [data?.artifacts, searchQuery]);

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
        // TODO: Wire up edit/delete handlers when collection management is implemented
        onEdit={undefined}
        onDelete={undefined}
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
        onRefresh={() => refetch()}
      />

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
              searchQuery
                ? 'No artifacts match your search'
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
              />
            ) : viewMode === 'list' ? (
              <ArtifactList
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
              />
            ) : (
              // Grouped view placeholder for Phase 5
              // For now, show grid view
              <ArtifactGrid
                artifacts={filteredArtifacts}
                isLoading={false}
                onArtifactClick={handleArtifactClick}
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
    </div>
  );
}

export default function CollectionPage() {
  return (
    <EntityLifecycleProvider mode="collection">
      <CollectionPageContent />
    </EntityLifecycleProvider>
  );
}
