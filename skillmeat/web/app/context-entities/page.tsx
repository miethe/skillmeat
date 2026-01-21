'use client';

import { useState } from 'react';
import { Plus, FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

// Import context entity components
import { ContextEntityCard } from '@/components/context/context-entity-card';
import { ContextEntityFilters } from '@/components/context/context-entity-filters';
import { ContextEntityDetail } from '@/components/context/context-entity-detail';
import { ContextEntityEditor } from '@/components/context/context-entity-editor';
import { DeployToProjectDialog } from '@/components/context/deploy-to-project-dialog';

// Import hooks
import {
  useContextEntities,
  useCreateContextEntity,
  useDeleteContextEntity,
  useToast,
} from '@/hooks';

// Import types
import type {
  ContextEntity,
  ContextEntityFilters as FilterType,
  CreateContextEntityRequest,
} from '@/types/context-entity';

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex h-full items-center justify-center py-12">
      <div className="text-center">
        <FileText className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">
          {hasFilters ? 'No entities match filters' : 'No context entities'}
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {hasFilters
            ? "Try adjusting your filters to find what you're looking for."
            : 'Create your first context entity to get started with Claude Code project configuration.'}
        </p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="space-y-3 rounded-lg border p-4">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <div className="flex gap-2 pt-2">
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-6 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ContextEntitiesPage() {
  const { toast } = useToast();

  // Filter state
  const [filters, setFilters] = useState<FilterType>({});

  // Modal state
  const [selectedEntity, setSelectedEntity] = useState<ContextEntity | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isDeployOpen, setIsDeployOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<ContextEntity | null>(null);

  // Data fetching with cursor-based pagination
  const [paginationCursor, setPaginationCursor] = useState<string | undefined>(undefined);
  const { data, isLoading, error, refetch } = useContextEntities({
    ...filters,
    after: paginationCursor,
  });

  // Mutations
  const createEntity = useCreateContextEntity();
  const deleteEntity = useDeleteContextEntity();

  // Event handlers
  const handlePreview = (entity: ContextEntity) => {
    setSelectedEntity(entity);
    setIsDetailOpen(true);
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    setTimeout(() => setSelectedEntity(null), 300);
  };

  const handleDeploy = (entity: ContextEntity) => {
    setSelectedEntity(entity);
    setIsDeployOpen(true);
  };

  const handleDeployClose = () => {
    setIsDeployOpen(false);
    setTimeout(() => setSelectedEntity(null), 300);
  };

  const handleEdit = (entity: ContextEntity) => {
    setEditingEntity(entity);
    setIsEditorOpen(true);
  };

  const handleCreateNew = () => {
    setEditingEntity(null);
    setIsEditorOpen(true);
  };

  const handleEditorClose = () => {
    setIsEditorOpen(false);
    setTimeout(() => setEditingEntity(null), 300);
  };

  const handleEditorSuccess = () => {
    setIsEditorOpen(false);
    setEditingEntity(null);
    refetch();
    toast({
      title: editingEntity ? 'Entity updated' : 'Entity created',
      description: editingEntity
        ? 'Successfully updated context entity'
        : 'Successfully created new context entity',
    });
  };

  const handleDelete = async (entity: ContextEntity) => {
    if (!confirm(`Are you sure you want to delete "${entity.name}"?`)) {
      return;
    }

    try {
      await deleteEntity.mutateAsync(entity.id);
      toast({
        title: 'Entity deleted',
        description: `Successfully deleted "${entity.name}"`,
      });
      refetch();
    } catch (err) {
      toast({
        title: 'Delete failed',
        description: err instanceof Error ? err.message : 'Could not delete entity',
        variant: 'destructive',
      });
    }
  };

  const handleLoadMore = () => {
    if (data?.page_info.end_cursor) {
      setPaginationCursor(data.page_info.end_cursor);
    }
  };

  // Determine if filters are active
  const hasActiveFilters = Object.keys(filters).some(
    (key) => filters[key as keyof FilterType] !== undefined && key !== 'limit' && key !== 'after'
  );

  return (
    <div className="space-y-6 p-6">
      {/* Skip Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-background focus:px-4 focus:py-2 focus:outline focus:outline-2 focus:outline-primary"
      >
        Skip to main content
      </a>

      {/* Page Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Context Entities</h1>
          <p className="text-muted-foreground">
            Manage Claude Code project configuration artifacts: specs, rules, context files, and
            templates.
          </p>
        </div>
        <Button onClick={handleCreateNew} aria-label="Add new context entity">
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Add Entity
        </Button>
      </div>

      {/* Main Layout: Filters + Content */}
      <div className="flex gap-6">
        {/* Filters Sidebar */}
        <nav aria-label="Filter context entities" className="w-64 flex-shrink-0">
          <div className="space-y-4 rounded-lg border bg-card p-4">
            <h2 className="text-sm font-semibold">Filters</h2>
            <ContextEntityFilters filters={filters} onFiltersChange={setFilters} />
          </div>
        </nav>

        {/* Content Area */}
        <main id="main-content" className="flex-1 space-y-4">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {isLoading ? (
                <Skeleton className="h-6 w-32" />
              ) : error ? (
                'Error loading entities'
              ) : (
                <>
                  {data?.items.length || 0} {data?.items.length === 1 ? 'Entity' : 'Entities'}
                </>
              )}
            </h2>
          </div>

          {/* Error State */}
          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <p className="text-sm text-destructive">
                Failed to load context entities. Please try again later.
              </p>
              <p className="mt-1 text-xs text-destructive/80">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div role="status" aria-live="polite" aria-label="Loading context entities">
              <LoadingSkeleton />
              <span className="sr-only">Loading context entities...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && (!data?.items || data.items.length === 0) && (
            <EmptyState hasFilters={hasActiveFilters} />
          )}

          {/* Entities Grid */}
          {!isLoading && !error && data?.items && data.items.length > 0 && (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.items.map((entity) => (
                  <ContextEntityCard
                    key={entity.id}
                    entity={entity}
                    onPreview={handlePreview}
                    onDeploy={handleDeploy}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                  />
                ))}
              </div>

              {/* Load More Button */}
              {data.page_info.has_next_page && (
                <div className="flex justify-center pt-6">
                  <Button
                    variant="outline"
                    onClick={handleLoadMore}
                    disabled={isLoading}
                    aria-label={
                      isLoading ? 'Loading more context entities' : 'Load more context entities'
                    }
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                        Loading more entities...
                      </>
                    ) : (
                      'Load More Entities'
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* Detail Modal */}
      {selectedEntity && (
        <ContextEntityDetail
          entity={selectedEntity}
          open={isDetailOpen}
          onClose={handleDetailClose}
          onEdit={() => {
            handleDetailClose();
            handleEdit(selectedEntity);
          }}
          onDeploy={() => {
            handleDetailClose();
            handleDeploy(selectedEntity);
          }}
          onDelete={async () => {
            await handleDelete(selectedEntity);
            handleDetailClose();
          }}
        />
      )}

      {/* Editor Dialog (Create/Edit) */}
      <ContextEntityEditor
        entity={editingEntity}
        open={isEditorOpen}
        onClose={handleEditorClose}
        onSuccess={handleEditorSuccess}
      />

      {/* Deploy Dialog */}
      {selectedEntity && (
        <DeployToProjectDialog
          entity={selectedEntity}
          open={isDeployOpen}
          onOpenChange={(open) => !open && handleDeployClose()}
          onSuccess={() => {
            handleDeployClose();
            toast({
              title: 'Entity deployed',
              description: `Successfully deployed "${selectedEntity.name}" to project`,
            });
          }}
        />
      )}
    </div>
  );
}
