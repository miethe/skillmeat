'use client';

import { Suspense, useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Plus, Grid3x3, List, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EntityLifecycleProvider, useEntityLifecycle } from '@/components/entity/EntityLifecycleProvider';
import { EntityList } from '@/components/entity/entity-list';
import { EntityForm } from '@/components/entity/entity-form';
import { EntityTabs } from './components/entity-tabs';
import { EntityFilters } from './components/entity-filters';
import { EntityDetailPanel } from './components/entity-detail-panel';
import { AddEntityDialog } from './components/add-entity-dialog';
import { Entity, EntityType, EntityStatus } from '@/types/entity';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

function ManagePageContent() {
  const searchParams = useSearchParams();
  const activeEntityType = (searchParams.get('type') as EntityType) || 'skill';

  const {
    entities,
    isLoading,
    setTypeFilter,
    setStatusFilter,
    setSearchQuery,
    searchQuery,
    statusFilter,
    deleteEntity,
    updateEntity,
  } = useEntityLifecycle();

  // Local state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<Entity | null>(null);
  const [tagFilter, setTagFilter] = useState<string[]>([]);

  // Update type filter when tab changes
  useEffect(() => {
    setTypeFilter(activeEntityType);
  }, [activeEntityType, setTypeFilter]);

  // Filter entities by tags client-side
  const filteredEntities = tagFilter.length > 0
    ? entities.filter((entity) =>
        tagFilter.some((tag) => entity.tags?.includes(tag))
      )
    : entities;

  const handleEntityClick = (entity: Entity) => {
    setSelectedEntity(entity);
    setDetailPanelOpen(true);
  };

  const handleEdit = (entity: Entity) => {
    setEditingEntity(entity);
  };

  const handleDelete = async (entity: Entity) => {
    if (confirm(`Are you sure you want to delete ${entity.name}?`)) {
      try {
        await deleteEntity(entity.id);
      } catch (error) {
        console.error('Delete failed:', error);
        alert('Failed to delete entity');
      }
    }
  };

  const handleDeploy = (entity: Entity) => {
    // Navigate to deploy page or open deploy dialog
    console.log('Deploy entity:', entity);
  };

  const handleSync = (entity: Entity) => {
    // Handle sync
    console.log('Sync entity:', entity);
  };

  const handleViewDiff = (entity: Entity) => {
    // Open diff viewer
    console.log('View diff:', entity);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold">Entity Management</h1>
            <p className="text-muted-foreground mt-1">
              Manage your skills, commands, agents, MCP servers, and hooks
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* View mode toggle */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  {viewMode === 'grid' ? <Grid3x3 className="h-4 w-4" /> : <List className="h-4 w-4" />}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuRadioGroup value={viewMode} onValueChange={(v) => setViewMode(v as 'grid' | 'list')}>
                  <DropdownMenuRadioItem value="grid">
                    <Grid3x3 className="h-4 w-4 mr-2" />
                    Grid
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="list">
                    <List className="h-4 w-4 mr-2" />
                    List
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Add button */}
            <Button onClick={() => setAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add New
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <EntityTabs>
          {(entityType) => (
            <div className="flex flex-col h-full">
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
              <div className="px-4 py-2 text-sm text-muted-foreground border-b">
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
                  onEntityClick={handleEntityClick}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onDeploy={handleDeploy}
                  onSync={handleSync}
                  onViewDiff={handleViewDiff}
                />
              </div>
            </div>
          )}
        </EntityTabs>
      </div>

      {/* Detail Panel */}
      <EntityDetailPanel
        entity={selectedEntity}
        open={detailPanelOpen}
        onClose={() => {
          setDetailPanelOpen(false);
          setSelectedEntity(null);
        }}
      />

      {/* Add Dialog */}
      <AddEntityDialog
        entityType={activeEntityType}
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
      />

      {/* Edit Dialog */}
      {editingEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-background rounded-lg shadow-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <EntityForm
              mode="edit"
              entity={editingEntity}
              onSuccess={() => setEditingEntity(null)}
              onCancel={() => setEditingEntity(null)}
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
      <Suspense fallback={
        <div className="flex items-center justify-center h-screen">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }>
        <ManagePageContent />
      </Suspense>
    </EntityLifecycleProvider>
  );
}
