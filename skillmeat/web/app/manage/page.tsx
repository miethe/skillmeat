'use client';

import { Suspense, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Plus, Grid3x3, List, Loader2, RefreshCw, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { PageHeader } from '@/components/shared/page-header';
import { EntityLifecycleProvider, useEntityLifecycle, useReturnTo } from '@/hooks';
import { EntityList } from '@/components/entity/entity-list';
import { EntityForm } from '@/components/entity/entity-form';
import { EntityTabs } from './components/entity-tabs';
import {
  ManagePageFilters,
  type ManageStatusFilter,
} from '@/components/manage/manage-page-filters';
import {
  ArtifactOperationsModal,
  type OperationsModalTab,
} from '@/components/manage/artifact-operations-modal';
import { AddEntityDialog } from './components/add-entity-dialog';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import type { Artifact, ArtifactType } from '@/types';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

function ManagePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { returnTo } = useReturnTo();

  const {
    entities,
    isLoading,
    isRefetching,
    refetch,
    setTypeFilter,
    setStatusFilter,
    setSearchQuery,
  } = useEntityLifecycle();

  // ==========================================================================
  // URL State Management
  // ==========================================================================

  // Helper to update URL params without full page reload
  const updateUrlParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());

      Object.entries(updates).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      });

      const newUrl = params.toString() ? `${pathname}?${params.toString()}` : pathname;
      router.push(newUrl, { scroll: false });
    },
    [searchParams, pathname, router]
  );

  // Get URL params for deep linking - all filter state comes from URL
  const urlArtifactId = searchParams.get('artifact');
  const urlTab = searchParams.get('tab') as OperationsModalTab | null;
  const urlType = (searchParams.get('type') as ArtifactType) || 'skill';
  const urlSearch = searchParams.get('search') || '';
  const urlStatus = (searchParams.get('status') as ManageStatusFilter) || 'all';
  const urlProject = searchParams.get('project') || null;
  const urlTags = useMemo(() => {
    return searchParams.get('tags')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Local state (non-URL)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editingArtifact, setEditingArtifact] = useState<Artifact | null>(null);
  const [artifactToDelete, setArtifactToDelete] = useState<Artifact | null>(null);
  const [showDeletionDialog, setShowDeletionDialog] = useState(false);

  // Sync URL state to hook state for API filtering
  useEffect(() => {
    setTypeFilter(urlType);
  }, [urlType, setTypeFilter]);

  useEffect(() => {
    setSearchQuery(urlSearch);
  }, [urlSearch, setSearchQuery]);

  useEffect(() => {
    // Map ManageStatusFilter to EntityStatus for the hook
    // The hook expects: 'synced' | 'modified' | 'outdated' | 'conflict' | 'error' | null
    // ManageStatusFilter has: 'all' | 'needs-update' | 'has-drift' | 'deployed' | 'error'
    const statusMapping: Record<ManageStatusFilter, string | null> = {
      all: null,
      'needs-update': 'outdated',
      'has-drift': 'modified',
      deployed: 'synced',
      error: 'error',
    };
    setStatusFilter(statusMapping[urlStatus] as any);
  }, [urlStatus, setStatusFilter]);

  // Track pending artifact selection from URL to handle race condition
  // where entities may not be loaded when URL param is first read
  const pendingArtifactRef = useRef<string | null>(null);
  // Ref to track closing state to prevent race condition with URL-based auto-open
  const isClosingRef = useRef(false);

  // Handle URL-based artifact selection (auto-open modal when navigating with artifact param)
  useEffect(() => {
    const artifactId = urlArtifactId;

    // Store pending selection when we have an artifact param that's new
    if (artifactId && artifactId !== pendingArtifactRef.current) {
      pendingArtifactRef.current = artifactId;
    }

    // Clear pending if URL no longer has artifact param
    if (!artifactId) {
      pendingArtifactRef.current = null;
      return;
    }

    // Skip if we're in the process of closing (prevents race condition with async URL update)
    if (isClosingRef.current) return;

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
  }, [urlArtifactId, entities, selectedArtifact]);

  // Filter entities by tags and project client-side
  const filteredEntities = useMemo(() => {
    let result = entities;

    // Filter by tags from URL
    if (urlTags.length > 0) {
      result = result.filter((entity) => urlTags.some((tag) => entity.tags?.includes(tag)));
    }

    // Filter by project from URL
    if (urlProject) {
      result = result.filter((entity) => {
        // Check deployments for project path matching
        return entity.deployments?.some((d) => d.project_path?.includes(urlProject));
      });
    }

    return result;
  }, [entities, urlTags, urlProject]);

  // Compute available projects from all entity deployments
  const availableProjects = useMemo(() => {
    const projectSet = new Set<string>();
    entities.forEach((entity) => {
      entity.deployments?.forEach((d) => {
        if (d.project_path) {
          // Extract project name from path (last segment or meaningful name)
          const segments = d.project_path.split('/').filter(Boolean);
          const projectName = segments[segments.length - 1] || d.project_path;
          projectSet.add(projectName);
        }
      });
    });
    return Array.from(projectSet).sort();
  }, [entities]);

  // Compute context-aware available tags from entities matching current filters
  // (type/status/search applied by API, project applied here, but NOT tag filter)
  const availableTags = useMemo(() => {
    // Apply project filter first (same logic as filteredEntities)
    let result = entities;
    if (urlProject) {
      result = result.filter((entity) => {
        return entity.deployments?.some((d) => d.project_path?.includes(urlProject));
      });
    }

    // Compute tag counts from the filtered set
    const tagCounts = new Map<string, number>();
    result.forEach((entity) => {
      entity.tags?.forEach((tag) => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    return Array.from(tagCounts.entries())
      .map(([name, count]) => ({ name, artifact_count: count }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [entities, urlProject]);

  // ==========================================================================
  // Filter Change Handlers (update URL)
  // ==========================================================================

  const handleSearchChange = useCallback(
    (search: string) => {
      updateUrlParams({ search: search || null });
    },
    [updateUrlParams]
  );

  const handleStatusChange = useCallback(
    (status: ManageStatusFilter) => {
      updateUrlParams({ status: status === 'all' ? null : status });
    },
    [updateUrlParams]
  );

  const handleTypeChange = useCallback(
    (type: ArtifactType | 'all') => {
      updateUrlParams({ type: type === 'skill' ? null : type }); // skill is default
    },
    [updateUrlParams]
  );

  const handleProjectChange = useCallback(
    (project: string | null) => {
      updateUrlParams({ project });
    },
    [updateUrlParams]
  );

  const handleTagsChange = useCallback(
    (tags: string[]) => {
      updateUrlParams({ tags: tags.length > 0 ? tags.join(',') : null });
    },
    [updateUrlParams]
  );

  const handleClearAllFilters = useCallback(() => {
    updateUrlParams({
      search: null,
      status: null,
      type: null,
      project: null,
      tags: null,
    });
  }, [updateUrlParams]);

  // ==========================================================================
  // Modal Handlers with URL State
  // ==========================================================================

  // Memoize event handlers to prevent EntityList re-renders
  const handleArtifactClick = useCallback(
    (artifact: Artifact) => {
      setSelectedArtifact(artifact);
      setDetailPanelOpen(true);
      // Update URL with artifact ID (clear tab to start at default 'status' for operations modal)
      updateUrlParams({
        artifact: artifact.id,
        tab: null,
      });
    },
    [updateUrlParams]
  );

  const handleDetailClose = useCallback(() => {
    // Set closing flag FIRST to prevent race condition with auto-open useEffect
    isClosingRef.current = true;
    setDetailPanelOpen(false);
    setSelectedArtifact(null);
    // Clear artifact and tab from URL
    updateUrlParams({
      artifact: null,
      tab: null,
    });
    // Reset closing flag after a tick to allow URL to update
    setTimeout(() => {
      isClosingRef.current = false;
    }, 0);
  }, [updateUrlParams]);

  const handleTabChange = useCallback(
    (tab: OperationsModalTab) => {
      // Update URL with new tab
      updateUrlParams({
        tab: tab === 'status' ? null : tab, // Don't clutter URL with default tab
      });
    },
    [updateUrlParams]
  );

  const handleEdit = useCallback((artifact: Artifact) => {
    setEditingArtifact(artifact);
  }, []);

  const handleDeleteArtifact = useCallback((artifact: Artifact) => {
    setArtifactToDelete(artifact);
    setShowDeletionDialog(true);
  }, []);

  // Handler for delete from card - uses deletion dialog
  const handleDelete = useCallback(
    (artifact: Artifact) => {
      handleDeleteArtifact(artifact);
    },
    [handleDeleteArtifact]
  );

  // Handler for delete from modal - closes modal first then shows deletion dialog
  const handleDeleteFromModal = useCallback(() => {
    if (selectedArtifact) {
      // Close the modal first
      handleDetailClose();
      // Then open the deletion dialog
      setArtifactToDelete(selectedArtifact);
      setShowDeletionDialog(true);
    }
  }, [selectedArtifact, handleDetailClose]);

  const handleDeploy = useCallback(
    (artifact: Artifact) => {
      // Open artifact modal to deployments tab for deployment
      setSelectedArtifact(artifact);
      setDetailPanelOpen(true);
      updateUrlParams({
        artifact: artifact.id,
        tab: 'deployments',
      });
    },
    [updateUrlParams]
  );

  const handleSync = useCallback(
    (artifact: Artifact) => {
      // Open artifact modal to sync tab for sync operations
      setSelectedArtifact(artifact);
      setDetailPanelOpen(true);
      updateUrlParams({
        artifact: artifact.id,
        tab: 'sync',
      });
    },
    [updateUrlParams]
  );

  const handleViewDiff = useCallback(
    (artifact: Artifact) => {
      // Open artifact modal to sync tab which shows diff viewer
      setSelectedArtifact(artifact);
      setDetailPanelOpen(true);
      updateUrlParams({
        artifact: artifact.id,
        tab: 'sync',
      });
    },
    [updateUrlParams]
  );

  const handleRollback = useCallback(
    (artifact: Artifact) => {
      // Open artifact modal to history tab for rollback
      setSelectedArtifact(artifact);
      setDetailPanelOpen(true);
      updateUrlParams({
        artifact: artifact.id,
        tab: 'history',
      });
    },
    [updateUrlParams]
  );

  const handleManage = useCallback(
    (artifact: Artifact) => {
      // Open artifact modal to status tab (default) for management options
      setSelectedArtifact(artifact);
      setDetailPanelOpen(true);
      updateUrlParams({
        artifact: artifact.id,
        tab: null, // Default to status which has health overview
      });
    },
    [updateUrlParams]
  );

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="border-b p-6">
        <div className="mb-4 flex items-center justify-between">
          <PageHeader
            title="Health & Sync"
            description="Monitor sync status and manage deployments"
            icon={<Activity className="h-6 w-6" />}
          />
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
              {/* Filters - URL-driven state */}
              <ManagePageFilters
                search={urlSearch}
                status={urlStatus}
                type={urlType}
                project={urlProject}
                tags={urlTags}
                onSearchChange={handleSearchChange}
                onStatusChange={handleStatusChange}
                onTypeChange={handleTypeChange}
                onProjectChange={handleProjectChange}
                onTagsChange={handleTagsChange}
                onClearAll={handleClearAllFilters}
                availableProjects={availableProjects}
                availableTags={availableTags}
              />

              {/* Entity count */}
              <div className="border-b px-4 py-2 text-sm text-muted-foreground">
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </div>
                ) : (
                  `${filteredEntities.length} ${filteredEntities.length === 1 ? 'artifact' : 'artifacts'} found`
                )}
              </div>

              {/* Entity List with operations card variant for manage page */}
              <div className="flex-1 overflow-hidden">
                <EntityList
                  viewMode={viewMode}
                  cardVariant="operations"
                  entities={filteredEntities}
                  onEntityClick={handleArtifactClick}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onDeploy={handleDeploy}
                  onSync={handleSync}
                  onViewDiff={handleViewDiff}
                  onRollback={handleRollback}
                  onManage={handleManage}
                />
              </div>
            </div>
          )}
        </EntityTabs>
      </div>

      {/* Artifact Operations Modal - Operations-focused modal with status as default tab */}
      <ArtifactOperationsModal
        artifact={selectedArtifact}
        open={detailPanelOpen}
        onClose={handleDetailClose}
        initialTab={urlTab || 'status'}
        onTabChange={handleTabChange}
        returnTo={returnTo || undefined}
        onDelete={handleDeleteFromModal}
      />

      {/* Add Dialog */}
      <AddEntityDialog entityType={urlType} open={addDialogOpen} onOpenChange={setAddDialogOpen} />

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

      {/* Artifact Deletion Dialog */}
      {artifactToDelete && (
        <ArtifactDeletionDialog
          artifact={artifactToDelete}
          open={showDeletionDialog}
          onOpenChange={(open) => {
            setShowDeletionDialog(open);
            if (!open) setArtifactToDelete(null);
          }}
          context="collection"
          onSuccess={() => {
            setShowDeletionDialog(false);
            setArtifactToDelete(null);
            refetch();
          }}
        />
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
