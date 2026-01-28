'use client';

import { Suspense, useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Plus, Grid3x3, List, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  EntityLifecycleProvider,
  useEntityLifecycle,
} from '@/components/entity/EntityLifecycleProvider';
import { EntityList } from '@/components/entity/entity-list';
import { EntityForm } from '@/components/entity/entity-form';
import { EntityTabs } from './components/entity-tabs';
import { EntityFilters } from './components/entity-filters';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import { AddEntityDialog } from './components/add-entity-dialog';
import type { Artifact, ArtifactType } from '@/types';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

function ManagePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeEntityType = (searchParams.get('type') as ArtifactType) || 'skill';

  const {
    entities,
    isLoading,
    isRefetching,
    refetch,
    setTypeFilter,
    setStatusFilter,
    setSearchQuery,
    searchQuery,
    statusFilter,
    deleteEntity,
  } = useEntityLifecycle();

  // Local state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editingArtifact, setEditingArtifact] = useState<Artifact | null>(null);
  const [tagFilter, setTagFilter] = useState<string[]>([]);

  // Update type filter when tab changes
  useEffect(() => {
    setTypeFilter(activeEntityType);
  }, [activeEntityType, setTypeFilter]);

  // Track pending artifact selection from URL to handle race condition
  // where entities may not be loaded when URL param is first read
  const pendingArtifactRef = useRef<string | null>(null);

  // Handle URL-based artifact selection (auto-open modal when navigating with artifact param)
  useEffect(() => {
    const artifactId = searchParams.get('artifact');

    // Store pending selection when we have an artifact param that's new
    if (artifactId && artifactId !== pendingArtifactRef.current) {
      pendingArtifactRef.current = artifactId;
    }

    // Clear pending if URL no longer has artifact param
    if (!artifactId) {
      pendingArtifactRef.current = null;
      return;
    }

    // Attempt to select when we have entities AND a pending selection AND no current selection
    if (pendingArtifactRef.current && entities.length > 0 && !selectedArtifact) {
      const artifact = entities.find(
        (e) => e.id === pendingArtifactRef.current || e.name === pendingArtifactRef.current
      );
      if (artifact) {
        setSelectedArtifact(artifact);
        setDetailPanelOpen(true);
        pendingArtifactRef.current = null; // Clear pending after successful selection
      }
    }
  }, [searchParams, entities, selectedArtifact]);

  // Filter entities by tags client-side
  const filteredEntities =
    tagFilter.length > 0
      ? entities.filter((entity) => tagFilter.some((tag) => entity.tags?.includes(tag)))
      : entities;

  // Memoize event handlers to prevent EntityList re-renders
  const handleArtifactClick = useCallback((artifact: Artifact) => {
    setSelectedArtifact(artifact);
    setDetailPanelOpen(true);
  }, []);

  const handleEdit = useCallback((artifact: Artifact) => {
    setEditingArtifact(artifact);
  }, []);

  const handleDelete = useCallback(
    async (artifact: Artifact) => {
      if (confirm(`Are you sure you want to delete ${artifact.name}?`)) {
        try {
          await deleteEntity(artifact.id);
        } catch (error) {
          console.error('Delete failed:', error);
          alert('Failed to delete artifact');
        }
      }
    },
    [deleteEntity]
  );

  const handleDeploy = useCallback((artifact: Artifact) => {
    // Open artifact modal to sync tab for deployment
    setSelectedArtifact(artifact);
    setDetailPanelOpen(true);
  }, []);

  const handleSync = useCallback((artifact: Artifact) => {
    // Open artifact modal to sync tab for sync operations
    setSelectedArtifact(artifact);
    setDetailPanelOpen(true);
  }, []);

  const handleViewDiff = useCallback((artifact: Artifact) => {
    // Open artifact modal to sync tab which shows diff viewer
    setSelectedArtifact(artifact);
    setDetailPanelOpen(true);
  }, []);

  const handleRollback = useCallback((artifact: Artifact) => {
    // Open artifact modal to history tab for rollback
    setSelectedArtifact(artifact);
    setDetailPanelOpen(true);
  }, []);

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="border-b p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Entity Management</h1>
            <p className="mt-1 text-muted-foreground">
              Manage your skills, commands, agents, MCP servers, and hooks
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Refresh button */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => refetch()}
              disabled={isRefetching}
              title="Refresh entities"
            >
              <RefreshCw className={cn('h-4 w-4', isRefetching && 'animate-spin')} />
            </Button>

            {/* View mode toggle */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  {viewMode === 'grid' ? (
                    <Grid3x3 className="h-4 w-4" />
                  ) : (
                    <List className="h-4 w-4" />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuRadioGroup
                  value={viewMode}
                  onValueChange={(v) => setViewMode(v as 'grid' | 'list')}
                >
                  <DropdownMenuRadioItem value="grid">
                    <Grid3x3 className="mr-2 h-4 w-4" />
                    Grid
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="list">
                    <List className="mr-2 h-4 w-4" />
                    List
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Add button */}
            <Button onClick={() => setAddDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add New
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <EntityTabs>
          {(_entityType) => (
            <div className="flex h-full flex-col">
              {/* Filters */}
              <EntityFilters
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                statusFilter={statusFilter}
                onStatusFilterChange={setStatusFilter}
                tagFilter={tagFilter}
                onTagFilterChange={setTagFilter}
              />

              {/* Entity count */}
              <div className="border-b px-4 py-2 text-sm text-muted-foreground">
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </div>
                ) : (
                  `${filteredEntities.length} ${filteredEntities.length === 1 ? 'entity' : 'entities'} found`
                )}
              </div>

              {/* Entity List */}
              <div className="flex-1 overflow-hidden">
                <EntityList
                  viewMode={viewMode}
                  entities={filteredEntities}
                  onEntityClick={handleArtifactClick}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onDeploy={handleDeploy}
                  onSync={handleSync}
                  onViewDiff={handleViewDiff}
                  onRollback={handleRollback}
                />
              </div>
            </div>
          )}
        </EntityTabs>
      </div>

      {/* Artifact Detail Modal */}
      <UnifiedEntityModal
        artifact={selectedArtifact}
        open={detailPanelOpen}
        onClose={() => {
          setDetailPanelOpen(false);
          setSelectedArtifact(null);
        }}
        onNavigateToSource={(sourceId, artifactPath) => {
          setDetailPanelOpen(false);
          setSelectedArtifact(null);
          router.push(`/marketplace/sources/${sourceId}?artifact=${encodeURIComponent(artifactPath)}`);
        }}
        onNavigateToDeployment={(projectPath, artifactId) => {
          setDetailPanelOpen(false);
          setSelectedArtifact(null);
          const encodedPath = btoa(projectPath);
          router.push(`/projects/${encodedPath}/manage?artifact=${encodeURIComponent(artifactId)}`);
        }}
      />

      {/* Add Dialog */}
      <AddEntityDialog
        entityType={activeEntityType}
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
      />

      {/* Edit Dialog */}
      {editingArtifact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-background p-6 shadow-lg">
            <EntityForm
              mode="edit"
              entity={editingArtifact}
              onSuccess={() => setEditingArtifact(null)}
              onCancel={() => setEditingArtifact(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function ManagePage() {
  return (
    <EntityLifecycleProvider mode="collection">
      <Suspense
        fallback={
          <div className="flex h-screen items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        }
      >
        <ManagePageContent />
      </Suspense>
    </EntityLifecycleProvider>
  );
}
