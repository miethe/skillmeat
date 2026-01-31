'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { Grid3x3, List, Loader2, ArrowLeft, Package, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  EntityLifecycleProvider,
  useEntityLifecycle,
} from '@/components/entity/EntityLifecycleProvider';
import { EntityList } from '@/components/entity/entity-list';
import { EntityForm } from '@/components/entity/entity-form';
import { EntityTabs } from '@/app/manage/components/entity-tabs';
import { EntityFilters } from '@/app/manage/components/entity-filters';
import { ProjectArtifactModal } from '@/components/shared/ProjectArtifactModal';
import { DeployFromCollectionDialog } from './components/deploy-from-collection-dialog';
import { PullToCollectionDialog } from './components/pull-to-collection-dialog';
import { Entity, EntityType } from '@/types/entity';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useProject, useArtifacts } from '@/hooks';
import { mapArtifactToEntity } from '@/lib/api/entity-mapper';

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
  } = useEntityLifecycle();

  // Fetch all artifacts from collection to enrich project entities
  const { data: artifactsData } = useArtifacts();

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

  // Handle URL-based artifact selection (auto-open modal when navigating with artifact param)
  useEffect(() => {
    const artifactId = searchParams.get('artifact');
    if (artifactId && entities.length > 0 && !selectedEntity) {
      // Find the entity matching the artifact ID
      const entity = entities.find((e) => e.id === artifactId || e.name === artifactId);
      if (entity) {
        // Look up matching artifact from collection to get full data
        const matchingArtifact = artifactsData?.artifacts.find(
          (artifact) => artifact.name === entity.name && artifact.type === entity.type
        );
        // Use centralized mapper with project context
        // Merge collection artifact data with project entity data
        const enrichedEntity = matchingArtifact
          ? mapArtifactToEntity({ ...matchingArtifact, ...entity } as any, 'project')
          : entity;
        setSelectedEntity(enrichedEntity);
        setDetailPanelOpen(true);
      }
    }
  }, [searchParams, entities, selectedEntity, artifactsData]);

  // Filter entities by tags client-side
  const filteredEntities =
    tagFilter.length > 0
      ? entities.filter((entity) => tagFilter.some((tag) => entity.tags?.includes(tag)))
      : entities;

  // Memoize event handlers to prevent EntityList re-renders
  const handleEntityClick = useCallback(
    (entity: Entity) => {
      // Look up matching artifact from collection by name and type
      const matchingArtifact = artifactsData?.artifacts.find(
        (artifact) => artifact.name === entity.name && artifact.type === entity.type
      );

      // Use centralized mapper with project context
      // Merge collection artifact data with project entity data
      const enrichedEntity = matchingArtifact
        ? mapArtifactToEntity({ ...matchingArtifact, ...entity } as any, 'project')
        : entity;

      setSelectedEntity(enrichedEntity);
      setDetailPanelOpen(true);
    },
    [artifactsData]
  );

  const handleEdit = useCallback((entity: Entity) => {
    setEditingEntity(entity);
  }, []);

  const handleDelete = useCallback(
    async (entity: Entity) => {
      if (confirm(`Are you sure you want to remove ${entity.name} from this project?`)) {
        try {
          await deleteEntity(entity.id);
        } catch (error) {
          console.error('Delete failed:', error);
          alert('Failed to remove entity from project');
        }
      }
    },
    [deleteEntity]
  );

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
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="border-b p-6">
        <div className="mb-4 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push(`/projects/${projectId}`)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h1 className="text-3xl font-bold">Project Entity Management</h1>
            <p className="mt-1 text-muted-foreground">Manage entities deployed to this project</p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{projectPath}</p>
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

            {/* Deploy from Collection button */}
            <Button onClick={() => setDeployDialogOpen(true)}>
              <Package className="mr-2 h-4 w-4" />
              Add from Collection
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-4">
          <EntityTabs>
            {() => (
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
      <ProjectArtifactModal
        artifact={selectedEntity}
        open={detailPanelOpen}
        onClose={() => {
          setDetailPanelOpen(false);
          setSelectedEntity(null);
        }}
        currentProjectPath={projectPath}
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
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-background p-6 shadow-lg">
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
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="mb-2 text-2xl font-bold">Project Not Found</h2>
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
      <Suspense
        fallback={
          <div className="flex h-screen items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        }
      >
        <ProjectManagePageContent projectPath={projectPath} projectId={projectId} />
      </Suspense>
    </EntityLifecycleProvider>
  );
}
