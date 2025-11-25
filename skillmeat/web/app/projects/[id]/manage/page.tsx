'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { Plus, Grid3x3, List, Loader2, ArrowLeft, Package, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { EntityLifecycleProvider, useEntityLifecycle } from '@/components/entity/EntityLifecycleProvider';
import { EntityList } from '@/components/entity/entity-list';
import { EntityForm } from '@/components/entity/entity-form';
import { EntityTabs } from '@/app/manage/components/entity-tabs';
import { EntityFilters } from '@/app/manage/components/entity-filters';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import { DeployFromCollectionDialog } from './components/deploy-from-collection-dialog';
import { PullToCollectionDialog } from './components/pull-to-collection-dialog';
import { Entity, EntityType, EntityStatus } from '@/types/entity';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useProject } from '@/hooks/useProjects';

interface ProjectManagePageContentProps {
  projectPath: string;
  projectId: string;
}

function ProjectManagePageContent({ projectPath, projectId }: ProjectManagePageContentProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeEntityType = (searchParams.get('type') as EntityType) || 'skill';

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
    updateEntity,
    syncEntity,
  } = useEntityLifecycle();

  // Local state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [deployDialogOpen, setDeployDialogOpen] = useState(false);
  const [pullDialogEntity, setPullDialogEntity] = useState<Entity | null>(null);
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

  // Memoize event handlers to prevent EntityList re-renders
  const handleEntityClick = useCallback((entity: Entity) => {
    setSelectedEntity(entity);
    setDetailPanelOpen(true);
  }, []);

  const handleEdit = useCallback((entity: Entity) => {
    setEditingEntity(entity);
  }, []);

  const handleDelete = useCallback(async (entity: Entity) => {
    if (confirm(`Are you sure you want to remove ${entity.name} from this project?`)) {
      try {
        await deleteEntity(entity.id);
      } catch (error) {
        console.error('Delete failed:', error);
        alert('Failed to remove entity from project');
      }
    }
  }, [deleteEntity]);

  const handleSync = useCallback(async (entity: Entity) => {
    setPullDialogEntity(entity);
  }, []);

  const handleViewDiff = useCallback((entity: Entity) => {
    // Open pull dialog in diff mode
    setPullDialogEntity(entity);
  }, []);

  const handleRollback = useCallback(async (entity: Entity) => {
    // Rollback will be handled by entity-actions component via RollbackDialog
    // This is just a placeholder in case we need to do something after rollback
    console.log('Rollback entity:', entity);
  }, []);

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b p-6">
        <div className="flex items-center gap-4 mb-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push(`/projects/${projectId}`)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h1 className="text-3xl font-bold">Project Entity Management</h1>
            <p className="text-muted-foreground mt-1">
              Manage entities deployed to this project
            </p>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              {projectPath}
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
              <RefreshCw className={cn("h-4 w-4", isRefetching && "animate-spin")} />
            </Button>

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

            {/* Deploy from Collection button */}
            <Button onClick={() => setDeployDialogOpen(true)}>
              <Package className="h-4 w-4 mr-2" />
              Add from Collection
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-4">
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
                    `${filteredEntities.length} ${filteredEntities.length === 1 ? 'entity' : 'entities'} deployed`
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
                    onSync={handleSync}
                    onViewDiff={handleViewDiff}
                    onRollback={handleRollback}
                  />
                </div>
              </div>
            )}
          </EntityTabs>
        </div>
      </div>

      {/* Entity Detail Modal */}
      <UnifiedEntityModal
        entity={selectedEntity}
        open={detailPanelOpen}
        onClose={() => {
          setDetailPanelOpen(false);
          setSelectedEntity(null);
        }}
      />

      {/* Deploy from Collection Dialog */}
      <DeployFromCollectionDialog
        projectPath={projectPath}
        open={deployDialogOpen}
        onOpenChange={setDeployDialogOpen}
        onSuccess={() => {
          setDeployDialogOpen(false);
        }}
      />

      {/* Pull to Collection Dialog */}
      {pullDialogEntity && (
        <PullToCollectionDialog
          entity={pullDialogEntity}
          projectPath={projectPath}
          open={!!pullDialogEntity}
          onOpenChange={(open) => {
            if (!open) {
              setPullDialogEntity(null);
            }
          }}
          onSuccess={() => {
            setPullDialogEntity(null);
          }}
        />
      )}

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

export default function ProjectManagePage() {
  const params = useParams();
  const projectId = params.id as string;

  // Fetch project details to get the path (avoid client-side atob which fails on URL-encoded base64)
  const { data: project, isLoading, error } = useProject(projectId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Project Not Found</h2>
          <p className="text-muted-foreground">
            The project you're looking for doesn't exist or couldn't be loaded.
          </p>
        </div>
      </div>
    );
  }

  // Get project path from API response (safe approach)
  const projectPath = project.path;

  return (
    <EntityLifecycleProvider mode="project" projectPath={projectPath}>
      <Suspense fallback={
        <div className="flex items-center justify-center h-screen">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }>
        <ProjectManagePageContent projectPath={projectPath} projectId={projectId} />
      </Suspense>
    </EntityLifecycleProvider>
  );
}
