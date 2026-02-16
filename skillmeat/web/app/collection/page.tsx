'use client';

import { useState, useEffect, useMemo, Suspense, useCallback, useRef } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Package, Loader2, Library } from 'lucide-react';
import { PageHeader } from '@/components/shared/page-header';
import { CollectionHeader } from '@/components/collection/collection-header';
import { CollectionToolbar } from '@/components/collection/collection-toolbar';
import { ArtifactGrid } from '@/components/collection/artifact-grid';
import { ArtifactList } from '@/components/collection/artifact-list';
import { ArtifactBrowseCardSkeleton } from '@/components/collection/artifact-browse-card';
import {
  ArtifactDetailsModal,
  type ArtifactDetailsTab,
} from '@/components/collection/artifact-details-modal';
import { EditCollectionDialog } from '@/components/collection/edit-collection-dialog';
import { CreateCollectionDialog } from '@/components/collection/create-collection-dialog';
import { MoveCopyDialog } from '@/components/collection/move-copy-dialog';
import { AddToGroupDialog } from '@/components/collection/add-to-group-dialog';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { ParameterEditorModal } from '@/components/discovery/ParameterEditorModal';
import { ArtifactTypeTabs } from '@/components/shared/artifact-type-tabs';
import { ActiveFilterRow, type ActiveFilterItem } from '@/components/shared/active-filter-row';
import { GroupedArtifactView } from '@/components/collection/grouped-artifact-view';
import {
  EntityLifecycleProvider,
  useCollectionContext,
  useInfiniteArtifacts,
  useInfiniteCollectionArtifacts,
  useIntersectionObserver,
  useEditArtifactParameters,
  useToast,
  useReturnTo,
} from '@/hooks';
import { Skeleton } from '@/components/ui/skeleton';
import type { Artifact, ArtifactFilters } from '@/types/artifact';
import type { ArtifactParameters } from '@/types/discovery';
import { mapApiResponseToArtifact, type ArtifactResponse } from '@/lib/api/mappers';
import { mapArtifactsToEntities } from '@/lib/api/entity-mapper';
import type { FilterMode } from '@/components/collection/collection-toolbar';

type ViewMode = 'grid' | 'list' | 'grouped';

// ==========================================================================
// Filter Combination Logic
// ==========================================================================

/**
 * The filterMode (AND/OR) controls how values WITHIN each filter category
 * combine. Across categories, filters always combine with AND.
 *
 * - AND mode (within category): artifact must match ALL selected values
 *   e.g., Groups=["A","B"] with AND -> artifact must be in both A and B
 * - OR mode (within category): artifact must match ANY selected value
 *   e.g., Groups=["A","B"] with OR -> artifact in A or B
 *
 * For single-value fields (status, scope), AND with multiple selections
 * will match nothing (an artifact can't be both "active" and "modified"),
 * which is technically correct. The main value of AND mode is for
 * multi-value fields like groups, tags, and tools.
 */

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
            <ArtifactBrowseCardSkeleton key={i} />
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
    currentGroups,
    isLoadingCollection,
    setSelectedCollectionId,
    selectedGroupId,
    setSelectedGroupId,
  } = useCollectionContext();

  const { toast } = useToast();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { returnTo } = useReturnTo();

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

  // ==========================================================================
  // URL-Driven Filter State
  // ==========================================================================

  // Read filter state from URL params (single source of truth)
  const urlSearch = searchParams.get('search') || '';
  const urlType = searchParams.get('type') || 'all';
  const urlSort = searchParams.get('sort') || 'confidence';
  const urlOrder = (searchParams.get('order') as 'asc' | 'desc') || 'desc';
  const filterMode: FilterMode = (searchParams.get('filterMode') as FilterMode) || 'and';

  // Multi-select filters from URL (comma-separated)
  const selectedStatuses = useMemo(() => {
    return searchParams.get('status')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  const selectedScopes = useMemo(() => {
    return searchParams.get('scope')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  const selectedPlatforms = useMemo(() => {
    return searchParams.get('platform')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Tag filtering from URL
  const selectedTags = useMemo(() => {
    return searchParams.get('tags')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Tool filtering from URL
  const selectedTools = useMemo(() => {
    return searchParams.get('tools')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Group filtering from URL (multi-select, comma-separated)
  const selectedGroups = useMemo(() => {
    return searchParams.get('groups')?.split(',').filter(Boolean) || [];
  }, [searchParams]);

  // Derive filters object from URL state (for type filter and API queries)
  const filters: ArtifactFilters = useMemo(
    () => ({
      type: urlType !== 'all' ? (urlType as ArtifactFilters['type']) : undefined,
    }),
    [urlType]
  );

  // Use URL values directly for search and sort
  const searchQuery = urlSearch;
  const sortField = urlSort;
  const sortOrder = urlOrder;

  // Refresh state
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Modal state
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  // Ref to track closing state to prevent race condition with URL-based auto-open
  const isClosingRef = useRef(false);
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

  // ==========================================================================
  // URL State Management
  // ==========================================================================

  // Get URL params for deep linking
  const urlArtifactId = searchParams.get('artifact');
  const urlCollectionId = searchParams.get('collection');
  const urlTab = searchParams.get('tab') as ArtifactDetailsTab | null;

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

  // Sync collection/group selection from URL on initial load
  useEffect(() => {
    if (urlCollectionId && urlCollectionId !== selectedCollectionId) {
      setSelectedCollectionId(urlCollectionId);
    }
  }, [urlCollectionId, selectedCollectionId, setSelectedCollectionId]);

  // Sync first selected group to context for API optimization (single group_id query param)
  useEffect(() => {
    const firstGroup = selectedGroups.length === 1 ? (selectedGroups[0] ?? null) : null;
    if (firstGroup !== selectedGroupId) {
      setSelectedGroupId(firstGroup);
    }
  }, [selectedGroups, selectedGroupId, setSelectedGroupId]);

  // Sync URL when collection changes (one-way: context -> URL for collection only)
  // Group URL updates are handled directly by handleGroupClick / toolbar handlers
  useEffect(() => {
    const currentUrlCollection = searchParams.get('collection');

    if (selectedCollectionId !== currentUrlCollection) {
      updateUrlParams({
        collection: selectedCollectionId,
      });
    }
  }, [selectedCollectionId, searchParams, updateUrlParams]);

  // ==========================================================================
  // Event Handlers
  // ==========================================================================

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

  // Grouped mode requires a specific collection context.
  useEffect(() => {
    if (!isSpecificCollection && viewMode === 'grouped') {
      setViewMode('grid');
    }
  }, [isSpecificCollection, viewMode]);

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
    artifact_type: filters.type && filters.type !== 'all' ? filters.type : undefined,
    group_id: isSpecificCollection && selectedGroups.length === 1 ? selectedGroups[0] : undefined,
    include_groups: isSpecificCollection && selectedGroups.length > 0,
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
    artifact_type: filters.type && filters.type !== 'all' ? filters.type : undefined,
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

  // ==========================================================================
  // Filter Change Handlers (update URL - single source of truth)
  // ==========================================================================

  // Handle search changes
  const handleSearchChange = useCallback(
    (query: string) => {
      updateUrlParams({
        search: query || null, // Don't write empty string to URL
      });
    },
    [updateUrlParams]
  );

  // Handle filter object changes (type only - status/scope/platform are now multi-select)
  const handleFiltersChange = useCallback(
    (newFilters: ArtifactFilters) => {
      updateUrlParams({
        type: newFilters.type && newFilters.type !== 'all' ? newFilters.type : null,
      });
    },
    [updateUrlParams]
  );

  // Handle multi-select status filter changes
  const handleStatusesChange = useCallback(
    (statuses: string[]) => {
      updateUrlParams({
        status: statuses.length > 0 ? statuses.join(',') : null,
      });
    },
    [updateUrlParams]
  );

  // Handle multi-select scope filter changes
  const handleScopesChange = useCallback(
    (scopes: string[]) => {
      updateUrlParams({
        scope: scopes.length > 0 ? scopes.join(',') : null,
      });
    },
    [updateUrlParams]
  );

  // Handle multi-select platform filter changes
  const handlePlatformsChange = useCallback(
    (platforms: string[]) => {
      updateUrlParams({
        platform: platforms.length > 0 ? platforms.join(',') : null,
      });
    },
    [updateUrlParams]
  );

  // Handle type tab changes
  const handleTypeTabChange = useCallback(
    (type: 'all' | ArtifactFilters['type']) => {
      updateUrlParams({
        type: type && type !== 'all' ? type : null,
      });
    },
    [updateUrlParams]
  );

  // Handle sort changes
  const handleSortChange = useCallback(
    (field: string, order: 'asc' | 'desc') => {
      updateUrlParams({
        sort: field === 'confidence' ? null : field, // confidence is default, don't write to URL
        order: order === 'desc' ? null : order, // desc is default, don't write to URL
      });
    },
    [updateUrlParams]
  );

  // Handle tag selection changes
  const handleTagsChange = useCallback(
    (tags: string[]) => {
      updateUrlParams({
        tags: tags.length > 0 ? tags.join(',') : null,
      });
    },
    [updateUrlParams]
  );

  // Handle tool selection changes
  const handleToolsChange = useCallback(
    (tools: string[]) => {
      updateUrlParams({
        tools: tools.length > 0 ? tools.join(',') : null,
      });
    },
    [updateUrlParams]
  );

  // Handle clicking a tag badge on a card to add it to filters
  const handleTagClick = useCallback(
    (tagName: string) => {
      if (!selectedTags.includes(tagName)) {
        handleTagsChange([...selectedTags, tagName]);
      }
    },
    [selectedTags, handleTagsChange]
  );

  // Handle clicking a group badge on a card to toggle group in multi-select
  const handleGroupClick = useCallback(
    (groupId: string) => {
      const newGroups = selectedGroups.includes(groupId)
        ? selectedGroups.filter((g) => g !== groupId)
        : [...selectedGroups, groupId];
      updateUrlParams({ groups: newGroups.length > 0 ? newGroups.join(',') : null });
    },
    [selectedGroups, updateUrlParams]
  );

  // Handle group filter changes from toolbar (multi-select)
  const handleGroupsChange = useCallback(
    (groupIds: string[]) => {
      updateUrlParams({ groups: groupIds.length > 0 ? groupIds.join(',') : null });
    },
    [updateUrlParams]
  );

  // Handle filter mode (AND/OR) changes
  const handleFilterModeChange = useCallback(
    (mode: FilterMode) => {
      updateUrlParams({
        filterMode: mode === 'and' ? null : mode, // 'and' is default, don't write to URL
      });
    },
    [updateUrlParams]
  );

  // Clear ALL filters in a single URL update to avoid stale searchParams race condition
  const handleClearAllFilters = useCallback(() => {
    updateUrlParams({
      status: null,
      scope: null,
      platform: null,
      groups: null,
      tags: null,
      tools: null,
      search: null,
      filterMode: null,
      // Don't clear: type, sort, order, collection, view (navigation, not filters)
    });
  }, [updateUrlParams]);

  // Helper function to map API artifact response to Artifact type
  // Uses the centralized mapper from @/lib/api/mappers
  const mapApiArtifactToArtifact = (apiArtifact: ArtifactResponse): Artifact => {
    return mapApiResponseToArtifact(apiArtifact, 'collection');
  };

  // Stage 1: Apply type, status, scope, search filters (BEFORE tags and tools)
  const preTagFilterArtifacts = useMemo(() => {
    // Handle different response shapes:
    // - Specific collection (infinite scroll): pages array with items (lightweight summaries)
    // - All collections (infinite scroll): pages array with items (full artifacts)
    let artifacts: Artifact[] = [];

    if (isSpecificCollection && infiniteCollectionData?.pages) {
      // Collection-specific view with infinite scroll: Flatten pages and map
      const allSummaries = infiniteCollectionData.pages.flatMap((page) => page.items);

      // Map summaries to Artifact entities using centralized mapper
      artifacts = mapArtifactsToEntities(allSummaries, 'collection');

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

    // Type filter is always AND (it's a primary category selector, not a cross-category filter)
    if (filters.type && filters.type !== 'all') {
      artifacts = artifacts.filter((artifact) => artifact.type === filters.type);
    }

    // Search is always AND (narrows results regardless of filter mode)
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      artifacts = artifacts.filter((a) => {
        const nameMatch = a.name.toLowerCase().includes(query);
        const descMatch = a.description?.toLowerCase().includes(query);
        const tagMatch = a.tags?.some((tag: string) => tag.toLowerCase().includes(query));
        return nameMatch || descMatch || tagMatch;
      });
    }

    // Apply filter categories — always AND across categories.
    // The filterMode controls how values WITHIN each category combine:
    //   'and' -> .every() (artifact must match ALL selected values)
    //   'or'  -> .some()  (artifact must match ANY selected value)
    const withinMode = filterMode === 'and' ? 'every' : 'some';

    if (selectedStatuses.length > 0) {
      artifacts = artifacts.filter((artifact) =>
        selectedStatuses[withinMode]((s) => (artifact.syncStatus || '') === s)
      );
    }

    if (selectedScopes.length > 0) {
      artifacts = artifacts.filter((artifact) =>
        selectedScopes[withinMode]((s) => (artifact.scope || '') === s)
      );
    }

    if (selectedPlatforms.length > 0) {
      artifacts = artifacts.filter((artifact) => {
        const matchesPlatform = (p: string) => {
          if (p === 'universal') {
            return !artifact.targetPlatforms || artifact.targetPlatforms.length === 0;
          }
          return artifact.targetPlatforms?.includes(p) ?? false;
        };
        return selectedPlatforms[withinMode](matchesPlatform);
      });
    }

    if (selectedGroups.length > 1) {
      artifacts = artifacts.filter((artifact) =>
        selectedGroups[withinMode]((gId) =>
          artifact.groups?.some((g) => g.id === gId) ?? false
        )
      );
    }

    return artifacts;
  }, [
    isSpecificCollection,
    infiniteCollectionData,
    infiniteAllArtifactsData,
    filters,
    searchQuery,
    selectedStatuses,
    selectedScopes,
    selectedPlatforms,
    selectedGroups,
    filterMode,
  ]);

  // Compute available tags from artifacts matching current filters (excluding tag filter)
  const availableTags = useMemo(() => {
    const tagCounts = new Map<string, number>();
    preTagFilterArtifacts.forEach((artifact) => {
      artifact.tags?.forEach((tag: string) => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });
    return Array.from(tagCounts.entries())
      .map(([name, count]) => ({ name, artifact_count: count }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [preTagFilterArtifacts]);

  // Stage 2: Apply tag, tool filters and sort
  const filteredArtifacts = useMemo(() => {
    let artifacts = preTagFilterArtifacts;

    // Tag filter — AND/OR mode applies within this category too
    if (selectedTags.length > 0) {
      const tagWithinMode = filterMode === 'and' ? 'every' : 'some';
      artifacts = artifacts.filter((artifact) =>
        selectedTags[tagWithinMode]((tag) => artifact.tags?.includes(tag) ?? false)
      );
    }

    // Tool filter — AND/OR mode applies within this category too
    if (selectedTools.length > 0) {
      const toolWithinMode = filterMode === 'and' ? 'every' : 'some';
      artifacts = artifacts.filter((artifact) =>
        selectedTools[toolWithinMode]((tool) => artifact.tools?.includes(tool) ?? false)
      );
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
  }, [preTagFilterArtifacts, selectedTags, selectedTools, filterMode, sortField, sortOrder]);

  const hasActiveFilters = useMemo(
    () =>
      Boolean(
        searchQuery ||
          selectedTags.length > 0 ||
          selectedTools.length > 0 ||
          (filters.type && filters.type !== 'all') ||
          selectedStatuses.length > 0 ||
          selectedScopes.length > 0 ||
          selectedPlatforms.length > 0 ||
          selectedGroups.length > 0
      ),
    [
      searchQuery,
      selectedTags.length,
      selectedTools.length,
      filters.type,
      selectedStatuses.length,
      selectedScopes.length,
      selectedPlatforms.length,
      selectedGroups.length,
    ]
  );

  // Unified pagination trigger:
  // 1) normal infinite scroll when sentinel intersects,
  // 2) auto-paging while active filters have no loaded matches yet.
  useEffect(() => {
    const shouldFetchForScroll = isIntersecting && hasNextPage && !isFetchingNextPage;
    const shouldFetchForFilteredEmpty =
      hasActiveFilters &&
      filteredArtifacts.length === 0 &&
      hasNextPage &&
      !isFetchingNextPage &&
      !isLoadingArtifacts &&
      !error;

    if (!shouldFetchForScroll && !shouldFetchForFilteredEmpty) {
      return;
    }

    fetchNextPage();

    // Keep enrichment data in sync while paging specific collections.
    if (isSpecificCollection && hasNextAllPage && !isFetchingNextAllPage) {
      fetchNextAllPage();
    }
  }, [
    isIntersecting,
    hasActiveFilters,
    filteredArtifacts.length,
    hasNextPage,
    isFetchingNextPage,
    isLoadingArtifacts,
    error,
    fetchNextPage,
    isSpecificCollection,
    hasNextAllPage,
    isFetchingNextAllPage,
    fetchNextAllPage,
  ]);

  // Compute unique tools with counts from ALL loaded artifacts (before tool filtering)
  // This is used by ToolFilterPopover
  const availableTools = useMemo(() => {
    // Get all artifacts before tool filtering is applied
    let allArtifacts: Artifact[] = [];

    if (isSpecificCollection && infiniteCollectionData?.pages) {
      const allSummaries = infiniteCollectionData.pages.flatMap((page) => page.items);
      // Map summaries to Artifact entities using centralized mapper
      allArtifacts = mapArtifactsToEntities(allSummaries as any, 'collection');
    } else if (!isSpecificCollection && infiniteAllArtifactsData?.pages) {
      allArtifacts = infiniteAllArtifactsData.pages.flatMap((page) =>
        page.items.map(mapApiArtifactToArtifact)
      );
    }

    // Count tools across all artifacts
    const toolCounts = new Map<string, number>();
    allArtifacts.forEach((artifact) => {
      const tools = artifact.tools || [];
      tools.forEach((tool: string) => {
        toolCounts.set(tool, (toolCounts.get(tool) || 0) + 1);
      });
    });

    // Convert to array format expected by ToolFilterPopover
    return Array.from(toolCounts.entries())
      .map(([name, count]) => ({ name, artifact_count: count }))
      .sort((a, b) => b.artifact_count - a.artifact_count); // Sort by count descending
  }, [infiniteCollectionData?.pages, infiniteAllArtifactsData?.pages, isSpecificCollection]);

  const activeFilterItems = useMemo<ActiveFilterItem[]>(() => {
    const items: ActiveFilterItem[] = [];

    selectedStatuses.forEach((status) => {
      items.push({
        id: `status:${status}`,
        label: `Status: ${status}`,
        onRemove: () => handleStatusesChange(selectedStatuses.filter((s) => s !== status)),
      });
    });

    selectedScopes.forEach((scope) => {
      items.push({
        id: `scope:${scope}`,
        label: `Scope: ${scope}`,
        onRemove: () => handleScopesChange(selectedScopes.filter((s) => s !== scope)),
      });
    });

    selectedPlatforms.forEach((platform) => {
      items.push({
        id: `platform:${platform}`,
        label: `Platform: ${platform}`,
        onRemove: () => handlePlatformsChange(selectedPlatforms.filter((p) => p !== platform)),
      });
    });

    selectedTags.forEach((tag) => {
      items.push({
        id: `tag:${tag}`,
        label: tag,
        onRemove: () => handleTagsChange(selectedTags.filter((t) => t !== tag)),
      });
    });

    selectedTools.forEach((tool) => {
      items.push({
        id: `tool:${tool}`,
        label: `Tool: ${tool}`,
        onRemove: () => handleToolsChange(selectedTools.filter((t) => t !== tool)),
      });
    });

    if (isSpecificCollection) {
      selectedGroups.forEach((groupId) => {
        const group = currentGroups.find((g) => g.id === groupId);
        items.push({
          id: `group:${groupId}`,
          label: `Group: ${group?.name ?? groupId}`,
          onRemove: () => handleGroupsChange(selectedGroups.filter((g) => g !== groupId)),
        });
      });
    }

    return items;
  }, [
    selectedStatuses,
    selectedScopes,
    selectedPlatforms,
    selectedTags,
    selectedTools,
    selectedGroups,
    isSpecificCollection,
    currentGroups,
    handleStatusesChange,
    handleScopesChange,
    handlePlatformsChange,
    handleTagsChange,
    handleToolsChange,
    handleGroupsChange,
  ]);

  // ==========================================================================
  // Deep Link: Auto-open modal from URL artifact param
  // ==========================================================================

  useEffect(() => {
    // Skip if we're in the process of closing (prevents race condition with async URL update)
    if (isClosingRef.current) return;

    // Only process if we have a URL artifact ID, artifacts are loaded, and modal isn't already open
    if (urlArtifactId && filteredArtifacts.length > 0 && !isDetailOpen) {
      const artifact = filteredArtifacts.find(
        (a) => a.id === urlArtifactId || a.name === urlArtifactId
      );
      if (artifact) {
        setSelectedArtifact(artifact);
        setIsDetailOpen(true);
      }
    }
  }, [urlArtifactId, filteredArtifacts, isDetailOpen]);

  // ==========================================================================
  // Modal Handlers with URL State
  // ==========================================================================

  const handleArtifactClick = (artifact: Artifact) => {
    setSelectedArtifact(artifact);
    setIsDetailOpen(true);
    // Update URL with artifact ID (and clear tab to start at default)
    updateUrlParams({
      artifact: artifact.id,
      tab: null,
    });
  };

  const handleDetailClose = useCallback(() => {
    // Set closing flag FIRST to prevent race condition with auto-open useEffect
    isClosingRef.current = true;
    setIsDetailOpen(false);
    // Clear artifact and tab from URL
    updateUrlParams({
      artifact: null,
      tab: null,
    });
    setTimeout(() => setSelectedArtifact(null), 300);
    // Reset closing flag after a tick to allow URL to update
    setTimeout(() => {
      isClosingRef.current = false;
    }, 0);
  }, [updateUrlParams]);

  // Handler for Delete action from modal (must be after handleDetailClose)
  const handleDeleteFromModal = useCallback(() => {
    if (selectedArtifact) {
      // Close the modal first
      handleDetailClose();
      // Then open the deletion dialog
      setArtifactToDelete(selectedArtifact);
      setShowDeletionDialog(true);
    }
  }, [selectedArtifact, handleDetailClose]);

  const handleTabChange = (tab: ArtifactDetailsTab) => {
    // Update URL with new tab
    updateUrlParams({
      tab: tab === 'overview' ? null : tab, // Don't clutter URL with default tab
    });
  };

  const handleCollectionClick = (collectionId: string) => {
    setSelectedCollectionId(collectionId);
    // URL will update via the effect that watches selectedCollectionId
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
      {/* Page Header */}
      <div className="border-b bg-background px-6 py-4">
        <PageHeader
          title="Collections"
          description="Browse & Discover your artifact collection"
          icon={<Library className="h-6 w-6" />}
        />
      </div>

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
        onFiltersChange={handleFiltersChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        sortField={sortField}
        sortOrder={sortOrder}
        onSortChange={handleSortChange}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        lastUpdated={lastUpdated}
        selectedTags={selectedTags}
        onTagsChange={handleTagsChange}
        availableTags={availableTags}
        selectedTools={selectedTools}
        onToolsChange={handleToolsChange}
        availableTools={availableTools}
        selectedGroups={selectedGroups}
        onGroupsChange={handleGroupsChange}
        availableGroups={currentGroups}
        selectedStatuses={selectedStatuses}
        onStatusesChange={handleStatusesChange}
        selectedScopes={selectedScopes}
        onScopesChange={handleScopesChange}
        selectedPlatforms={selectedPlatforms}
        onPlatformsChange={handlePlatformsChange}
        showTypeFilter={false}
        allowGroupedView={isSpecificCollection}
        filterMode={filterMode}
        onFilterModeChange={handleFilterModeChange}
        onClearAllFilters={handleClearAllFilters}
      />

      {/* Active filters row */}
      <div className="border-b bg-muted/10 px-6 py-2">
        <ActiveFilterRow items={activeFilterItems} />
      </div>

      {/* Type tabs below filter bar and active-filters row */}
      <div className="border-b px-6 py-2">
        <ArtifactTypeTabs
          value={urlType as 'all' | ArtifactFilters['type']}
          onChange={handleTypeTabChange}
        />
      </div>

      {/* Result count line */}
      <div className="border-b px-6 py-2 text-sm text-muted-foreground">
        {isLoadingArtifacts
          ? 'Loading artifacts...'
          : `Showing ${filteredArtifacts.length} of ${totalCount} artifacts${hasNextPage ? ' (scroll for more)' : ''}`}
      </div>

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
              <ArtifactBrowseCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!error && !isLoadingArtifacts && filteredArtifacts.length === 0 && (
          <EmptyState
            title={
              searchQuery || selectedTags.length > 0 || selectedTools.length > 0
                ? 'No results found'
                : isSpecificCollection
                  ? 'No artifacts in this collection'
                  : 'No artifacts'
            }
            description={
              searchQuery || selectedTags.length > 0 || selectedTools.length > 0
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
                onTagClick={handleTagClick}
                onGroupClick={handleGroupClick}
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
            ) : isSpecificCollection && selectedCollectionId ? (
              <GroupedArtifactView
                collectionId={selectedCollectionId}
                artifacts={filteredArtifacts}
                onArtifactClick={handleArtifactClick}
                onMoveToCollection={handleMoveToCollection}
                onManageGroups={handleManageGroups}
                onEdit={handleEditFromDropdown}
                onDelete={handleDeleteFromDropdown}
              />
            ) : (
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
                onTagClick={handleTagClick}
                onGroupClick={handleGroupClick}
              />
            )}
          </>
        )}

        {/* Infinite scroll trigger element - keep mounted even in filtered-empty states */}
        {!error && !isLoadingArtifacts && (
          <div ref={targetRef} className="flex justify-center py-8">
            {isFetchingNextPage && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Loading more artifacts...</span>
              </div>
            )}
            {!isFetchingNextPage &&
              hasActiveFilters &&
              filteredArtifacts.length === 0 &&
              hasNextPage && (
                <span className="text-sm text-muted-foreground">
                  Searching additional pages for matching artifacts...
                </span>
              )}
            {!hasNextPage && filteredArtifacts.length > 0 && totalCount > 0 && (
              <span className="text-sm text-muted-foreground">
                All {totalCount} artifacts loaded
              </span>
            )}
          </div>
        )}
      </div>

      {/* Artifact Detail Modal - Discovery-focused modal */}
      <ArtifactDetailsModal
        artifact={selectedArtifact}
        open={isDetailOpen}
        onClose={handleDetailClose}
        initialTab={urlTab || 'overview'}
        onTabChange={handleTabChange}
        returnTo={returnTo || undefined}
        onDelete={handleDeleteFromModal}
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
            tags: artifactToEdit.tags,
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
          sourceCollectionId={
            artifactForCollection.collections?.[0]?.id || selectedCollectionId || undefined
          }
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
