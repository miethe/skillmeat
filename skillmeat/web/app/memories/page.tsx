'use client';

import { useState, useMemo, useCallback } from 'react';
import {
  Brain,
  Grid3x3,
  List,
  ChevronRight,
  Inbox,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import {
  useGlobalMemoryItems,
  useProjects,
  useMemorySelection,
  usePromoteMemoryItem,
  useDeprecateMemoryItem,
  useDeleteMemoryItem,
  useUpdateMemoryItem,
  useBulkPromoteMemoryItems,
  useBulkDeprecateMemoryItems,
  useBulkDeleteMemoryItems,
} from '@/hooks';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryType } from '@/sdk/models/MemoryType';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryFilterBar } from '@/components/memory/memory-filter-bar';
import { MemoryList } from '@/components/memory/memory-list';
import { MemoryCard } from '@/components/memory/memory-card';
import { MemoryGridCard, MemoryGridCardSkeleton } from '@/components/memory/memory-grid-card';
import { MemoryCardSkeleton } from '@/components/memory/memory-card-skeleton';
import { BatchActionBar } from '@/components/memory/batch-action-bar';
import { ConfirmActionDialog } from '@/components/memory/confirm-action-dialog';
import { MemoryFormModal } from '@/components/memory/memory-form-modal';
import { GlobalMemoryInbox } from '@/components/memory/global-memory-inbox';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Sort mapping: UI sort values -> API sort_by + sort_order
// ---------------------------------------------------------------------------

function parseSortValue(sortBy: string): { sortBy?: string; sortOrder?: 'asc' | 'desc' } {
  switch (sortBy) {
    case 'newest':
      return { sortBy: 'created_at', sortOrder: 'desc' };
    case 'oldest':
      return { sortBy: 'created_at', sortOrder: 'asc' };
    case 'confidence-desc':
      return { sortBy: 'confidence', sortOrder: 'desc' };
    case 'confidence-asc':
      return { sortBy: 'confidence', sortOrder: 'asc' };
    case 'most-used':
      return { sortBy: 'access_count', sortOrder: 'desc' };
    default:
      return {};
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function MemoriesPage() {
  // ---------------------------------------------------------------------------
  // Tab state
  // ---------------------------------------------------------------------------
  const [activeTab, setActiveTab] = useState<'all' | 'inbox'>('all');

  // ---------------------------------------------------------------------------
  // All Memories tab state
  // ---------------------------------------------------------------------------
  const [projectFilter, setProjectFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showDeprecated, setShowDeprecated] = useState(false);
  const [sortBy, setSortBy] = useState('newest');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  // ---------------------------------------------------------------------------
  // Selection state for All Memories tab
  // ---------------------------------------------------------------------------
  const {
    selectedIds,
    focusedIndex,
    toggleSelect,
    clearSelection,
  } = useMemorySelection();

  // ---------------------------------------------------------------------------
  // Modal state
  // ---------------------------------------------------------------------------
  const [editingMemory, setEditingMemory] = useState<MemoryItemResponse | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: 'reject' | 'deprecate' | 'delete';
    memoryId: string;
    title: string;
    description: string;
  } | null>(null);

  // ---------------------------------------------------------------------------
  // Data hooks
  // ---------------------------------------------------------------------------
  const { data: projects = [] } = useProjects();
  const selectedProjectId = projectFilter === 'all' ? undefined : projectFilter;

  const { sortBy: apiSortBy, sortOrder: apiSortOrder } = parseSortValue(sortBy);

  // All Memories data
  const { data, isLoading, isError, error, refetch } = useGlobalMemoryItems({
    projectId: selectedProjectId,
    status: statusFilter !== 'all' ? (statusFilter as MemoryStatus) : undefined,
    type: typeFilter !== 'all' ? (typeFilter as MemoryType) : undefined,
    search: searchQuery.trim() || undefined,
    sortBy: apiSortBy,
    sortOrder: apiSortOrder,
    limit: 100,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const filteredItems = useMemo(
    () =>
      statusFilter === 'all' && !showDeprecated
        ? items.filter((m) => m.status !== 'deprecated')
        : items,
    [items, statusFilter, showDeprecated]
  );

  // Candidate count for inbox badge (separate query, shares cache with inbox)
  const { data: candidateData } = useGlobalMemoryItems({
    status: 'candidate' as MemoryStatus,
    limit: 100,
  });
  const candidateCount = candidateData?.items?.length ?? 0;

  // ---------------------------------------------------------------------------
  // Derived data
  // ---------------------------------------------------------------------------
  const projectNameMap = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects]
  );

  const projectOptions = useMemo(
    () => projects.map((p) => ({ id: p.id, name: p.name })),
    [projects]
  );

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = { all: filteredItems.length };
    for (const item of filteredItems) {
      counts[item.type] = (counts[item.type] ?? 0) + 1;
    }
    return counts;
  }, [filteredItems]);

  const groupedItems = useMemo(() => {
    const groups = new Map<string, MemoryItemResponse[]>();
    for (const item of filteredItems) {
      if (!groups.has(item.project_id)) groups.set(item.project_id, []);
      groups.get(item.project_id)!.push(item);
    }
    return groups;
  }, [filteredItems]);

  // ---------------------------------------------------------------------------
  // Expand all / collapse all
  // ---------------------------------------------------------------------------
  const allExpanded = useMemo(
    () => Array.from(groupedItems.keys()).every((key) => expandedGroups[key] !== false),
    [groupedItems, expandedGroups]
  );

  const toggleAllGroups = useCallback(() => {
    const newState: Record<string, boolean> = {};
    for (const key of groupedItems.keys()) {
      newState[key] = !allExpanded;
    }
    setExpandedGroups(newState);
  }, [groupedItems, allExpanded]);

  // ---------------------------------------------------------------------------
  // Mutation hooks
  // ---------------------------------------------------------------------------
  const promoteItem = usePromoteMemoryItem();
  const deprecateItem = useDeprecateMemoryItem({
    onSuccess: () => setConfirmAction(null),
  });
  const deleteItem = useDeleteMemoryItem();
  const updateItem = useUpdateMemoryItem();
  const bulkPromote = useBulkPromoteMemoryItems();
  const bulkDeprecate = useBulkDeprecateMemoryItems();
  const bulkDelete = useBulkDeleteMemoryItems();

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleApprove = useCallback(
    (id: string) => {
      promoteItem.mutate({ itemId: id, data: { reason: 'Approved via global memories page' } });
    },
    [promoteItem]
  );

  const handleReject = useCallback((id: string) => {
    setConfirmAction({
      type: 'reject',
      memoryId: id,
      title: 'Reject Memory?',
      description:
        'This will deprecate the memory item. It can be restored later by changing its status.',
    });
  }, []);

  const handleEdit = useCallback(
    (id: string) => {
      const mem = filteredItems.find((m) => m.id === id) ?? null;
      if (mem) {
        setEditingMemory(mem);
      }
    },
    [filteredItems]
  );

  const handleMerge = useCallback((_id: string) => {
    // No-op on global page; merge is project-scoped
  }, []);

  const handleCardClick = useCallback((_id: string) => {
    // No-op on global page; no detail panel
  }, []);

  const handleDeprecate = useCallback((id: string) => {
    setConfirmAction({
      type: 'deprecate',
      memoryId: id,
      title: 'Deprecate Memory?',
      description:
        'This will mark the memory item as deprecated. It will no longer be included in active context.',
    });
  }, []);

  const handleReactivate = useCallback(
    (id: string) => {
      updateItem.mutate({
        itemId: id,
        data: { status: 'candidate' },
      });
    },
    [updateItem]
  );

  const handleDelete = useCallback((id: string) => {
    setConfirmAction({
      type: 'delete',
      memoryId: id,
      title: 'Delete Memory?',
      description: 'This will permanently delete this memory item. This action cannot be undone.',
    });
  }, []);

  const handleConfirmAction = useCallback(() => {
    if (!confirmAction) return;
    if (confirmAction.type === 'delete') {
      if (confirmAction.memoryId === '__batch__') {
        bulkDelete.mutate([...selectedIds], {
          onSuccess: () => {
            setConfirmAction(null);
            clearSelection();
          },
        });
      } else {
        deleteItem.mutate(confirmAction.memoryId, {
          onSuccess: () => setConfirmAction(null),
        });
      }
    } else {
      deprecateItem.mutate({
        itemId: confirmAction.memoryId,
        data: {
          reason:
            confirmAction.type === 'reject'
              ? 'Rejected via global memories page'
              : 'Deprecated via global memories page',
        },
      });
    }
  }, [confirmAction, deprecateItem, deleteItem, bulkDelete, selectedIds, clearSelection]);

  const handleCreateMemory = useCallback(() => {
    // No-op on global page; creation is project-scoped
  }, []);

  const handleBatchApprove = useCallback(() => {
    if (selectedIds.size === 0) return;
    bulkPromote.mutate(
      { item_ids: [...selectedIds], reason: 'Batch approved via global memories page' },
      { onSuccess: () => clearSelection() }
    );
  }, [selectedIds, bulkPromote, clearSelection]);

  const handleBatchReject = useCallback(() => {
    if (selectedIds.size === 0) return;
    bulkDeprecate.mutate(
      { item_ids: [...selectedIds], reason: 'Batch rejected via global memories page' },
      { onSuccess: () => clearSelection() }
    );
  }, [selectedIds, bulkDeprecate, clearSelection]);

  const handleBatchDelete = useCallback(() => {
    if (selectedIds.size === 0) return;
    setConfirmAction({
      type: 'delete',
      memoryId: '__batch__',
      title: `Delete ${selectedIds.size} ${selectedIds.size === 1 ? 'Memory' : 'Memories'}?`,
      description: `This will permanently delete ${selectedIds.size} selected ${selectedIds.size === 1 ? 'memory item' : 'memory items'}. This action cannot be undone.`,
    });
  }, [selectedIds]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex h-full flex-col">
      {/* ------------------------------------------------------------------ */}
      {/* Page Header                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="border-b px-6 pb-4 pt-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Brain className="h-7 w-7 text-muted-foreground" aria-hidden="true" />
              <h1 className="text-3xl font-bold tracking-tight">Memories</h1>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Browse and triage memories across all projects.
            </p>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Tab Bar                                                            */}
      {/* ------------------------------------------------------------------ */}
      <div className="border-b px-6 py-2">
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as 'all' | 'inbox')}
        >
          <TabsList aria-label="Memory view tabs">
            <TabsTrigger value="all">All Memories</TabsTrigger>
            <TabsTrigger value="inbox" className="gap-1.5">
              <Inbox className="h-3.5 w-3.5" aria-hidden="true" />
              Inbox
              {candidateCount > 0 && (
                <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-[10px]">
                  {candidateCount}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Tab Content: All Memories                                          */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === 'all' && (
        <>
          <MemoryFilterBar
            typeFilter={typeFilter}
            onTypeFilterChange={setTypeFilter}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            showDeprecated={showDeprecated}
            onShowDeprecatedChange={setShowDeprecated}
            sortBy={sortBy}
            onSortByChange={setSortBy}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
            counts={typeCounts}
            projectFilter={projectFilter}
            onProjectFilterChange={setProjectFilter}
            projects={projectOptions}
          />

          {/* View toggle + count bar */}
          <div className="flex items-center justify-between px-6 py-2 border-b">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {filteredItems.length} {filteredItems.length === 1 ? 'memory' : 'memories'}
              </span>
              {!selectedProjectId && filteredItems.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={toggleAllGroups}
                >
                  {allExpanded ? 'Collapse All' : 'Expand All'}
                </Button>
              )}
            </div>
            <div
              className="flex items-center gap-1 rounded-md border bg-background p-1"
              role="group"
              aria-label="View mode"
            >
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setViewMode('grid')}
                aria-label="Grid view"
                aria-pressed={viewMode === 'grid'}
              >
                <Grid3x3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setViewMode('list')}
                aria-label="List view"
                aria-pressed={viewMode === 'list'}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Content: flat or grouped */}
          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-y-auto" role="region" aria-label="Memory list">
              {selectedProjectId ? (
                /* -------------------------------------------------------------- */
                /* Flat mode: single project selected                             */
                /* -------------------------------------------------------------- */
                <MemoryList
                  memories={filteredItems}
                  isLoading={isLoading}
                  isError={isError}
                  error={error}
                  refetch={refetch}
                  selectedIds={selectedIds}
                  focusedIndex={focusedIndex}
                  onToggleSelect={toggleSelect}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onEdit={handleEdit}
                  onMerge={handleMerge}
                  onCardClick={handleCardClick}
                  onCreateMemory={handleCreateMemory}
                  onReactivate={handleReactivate}
                  onDeprecate={handleDeprecate}
                  viewMode={viewMode}
                  onDelete={handleDelete}
                />
              ) : (
                /* -------------------------------------------------------------- */
                /* Grouped mode: all projects, collapsible sections               */
                /* -------------------------------------------------------------- */
                <>
                  {/* Loading state */}
                  {isLoading && (
                    <div aria-label="Loading memories" role="status">
                      {viewMode === 'grid' ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                          {Array.from({ length: 6 }).map((_, i) => (
                            <MemoryGridCardSkeleton key={i} />
                          ))}
                        </div>
                      ) : (
                        <div className="divide-y">
                          {Array.from({ length: 6 }).map((_, i) => (
                            <MemoryCardSkeleton key={i} />
                          ))}
                        </div>
                      )}
                      <span className="sr-only">Loading memory items...</span>
                    </div>
                  )}

                  {/* Error state */}
                  {!isLoading && isError && (
                    <div
                      className="flex flex-col items-center justify-center py-16 text-center"
                      role="alert"
                    >
                      <div className="rounded-full bg-destructive/10 p-4 mb-4">
                        <AlertTriangle
                          className="h-8 w-8 text-destructive"
                          aria-hidden="true"
                        />
                      </div>
                      <h3 className="text-lg font-semibold">Failed to load memories</h3>
                      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                        {error?.message ?? 'An unexpected error occurred.'}
                      </p>
                      <Button
                        variant="outline"
                        className="mt-4"
                        size="sm"
                        onClick={() => refetch()}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                        Retry
                      </Button>
                    </div>
                  )}

                  {/* Empty state */}
                  {!isLoading && !isError && filteredItems.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <div className="rounded-full bg-muted p-4 mb-4">
                        <Brain className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
                      </div>
                      <h3 className="text-lg font-semibold">No memories found</h3>
                      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                        No memories matched your current filters. Try adjusting your filters or
                        create memories from a project memory page.
                      </p>
                    </div>
                  )}

                  {/* Grouped items */}
                  {!isLoading && !isError && filteredItems.length > 0 && (
                    <div>
                      {Array.from(groupedItems.entries()).map(([projId, projItems]) => (
                        <Collapsible
                          key={projId}
                          open={expandedGroups[projId] !== false}
                          onOpenChange={(open) =>
                            setExpandedGroups((prev) => ({ ...prev, [projId]: open }))
                          }
                        >
                          <CollapsibleTrigger asChild>
                            <button
                              className="flex w-full items-center gap-2 px-6 py-3 text-left hover:bg-muted/50 border-b transition-colors"
                              aria-label={`${projectNameMap.get(projId) ?? projId} - ${projItems.length} ${projItems.length === 1 ? 'memory' : 'memories'}`}
                            >
                              <ChevronRight
                                className={cn(
                                  'h-4 w-4 text-muted-foreground transition-transform',
                                  expandedGroups[projId] !== false && 'rotate-90'
                                )}
                                aria-hidden="true"
                              />
                              <span className="font-medium text-sm">
                                {projectNameMap.get(projId) ?? projId}
                              </span>
                              <Badge variant="secondary" className="ml-1">
                                {projItems.length}
                              </Badge>
                            </button>
                          </CollapsibleTrigger>
                          <CollapsibleContent>
                            {viewMode === 'grid' ? (
                              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                                {projItems.map((memory) => (
                                  <MemoryGridCard
                                    key={memory.id}
                                    memory={memory}
                                    selected={selectedIds.has(memory.id)}
                                    focused={false}
                                    onToggleSelect={toggleSelect}
                                    onApprove={handleApprove}
                                    onReject={handleReject}
                                    onEdit={handleEdit}
                                    onMerge={handleMerge}
                                    onClick={handleCardClick}
                                    onReactivate={handleReactivate}
                                    onDeprecate={handleDeprecate}
                                    onDelete={handleDelete}
                                  />
                                ))}
                              </div>
                            ) : (
                              <div className="divide-y">
                                {projItems.map((memory) => (
                                  <MemoryCard
                                    key={memory.id}
                                    memory={memory}
                                    selected={selectedIds.has(memory.id)}
                                    focused={false}
                                    onToggleSelect={toggleSelect}
                                    onApprove={handleApprove}
                                    onReject={handleReject}
                                    onEdit={handleEdit}
                                    onMerge={handleMerge}
                                    onClick={handleCardClick}
                                    onReactivate={handleReactivate}
                                    onDeprecate={handleDeprecate}
                                    onDelete={handleDelete}
                                  />
                                ))}
                              </div>
                            )}
                          </CollapsibleContent>
                        </Collapsible>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <BatchActionBar
            selectedCount={selectedIds.size}
            onApproveAll={handleBatchApprove}
            onRejectAll={handleBatchReject}
            onDeleteAll={handleBatchDelete}
            onClearSelection={clearSelection}
          />
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Tab Content: Inbox                                                 */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === 'inbox' && (
        <GlobalMemoryInbox projectNameMap={projectNameMap} />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Shared Modals                                                      */}
      {/* ------------------------------------------------------------------ */}

      {/* Edit memory form modal */}
      <MemoryFormModal
        open={!!editingMemory}
        onOpenChange={(open) => {
          if (!open) {
            setEditingMemory(null);
          }
        }}
        memory={editingMemory}
        projectId={editingMemory?.project_id ?? ''}
      />

      {/* Confirm action dialog (reject / deprecate / delete) */}
      <ConfirmActionDialog
        open={!!confirmAction}
        onOpenChange={(open) => {
          if (!open) setConfirmAction(null);
        }}
        title={confirmAction?.title ?? ''}
        description={confirmAction?.description ?? ''}
        confirmLabel={
          confirmAction?.type === 'delete'
            ? 'Delete'
            : confirmAction?.type === 'reject'
              ? 'Reject'
              : 'Deprecate'
        }
        confirmVariant="destructive"
        onConfirm={handleConfirmAction}
        isLoading={deprecateItem.isPending || deleteItem.isPending || bulkDelete.isPending}
      />
    </div>
  );
}
