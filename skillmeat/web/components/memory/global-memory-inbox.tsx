'use client';

/**
 * GlobalMemoryInbox Component
 *
 * Cross-project inbox tab for triaging candidate memories. Filters to
 * status: 'candidate' across all projects and supports batch approve/deny.
 * Items are grouped by project with collapsible sections.
 *
 * Supports grid and list view modes with MemoryGridCard and MemoryCard
 * respectively.
 */

import { useState, useMemo, useCallback } from 'react';
import { Grid3x3, List, ChevronRight, Inbox } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import {
  useGlobalMemoryItems,
  useMemorySelection,
  usePromoteMemoryItem,
  useDeprecateMemoryItem,
  useUpdateMemoryItem,
  useDeleteMemoryItem,
  useBulkPromoteMemoryItems,
  useBulkDeprecateMemoryItems,
  useBulkDeleteMemoryItems,
} from '@/hooks';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryFilterBar } from '@/components/memory/memory-filter-bar';
import { MemoryCard } from '@/components/memory/memory-card';
import { MemoryGridCard } from '@/components/memory/memory-grid-card';
import { BatchActionBar } from '@/components/memory/batch-action-bar';
import { ConfirmActionDialog } from '@/components/memory/confirm-action-dialog';
import { MemoryFormModal } from '@/components/memory/memory-form-modal';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Parse a UI sort value into API sortBy + sortOrder parameters.
 */
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
// Confirm action state
// ---------------------------------------------------------------------------

interface ConfirmActionState {
  type: 'reject' | 'deprecate' | 'delete' | 'batch-reject' | 'batch-delete';
  title: string;
  description: string;
  /** Single-item target ID. Undefined for batch actions. */
  itemId?: string;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface GlobalMemoryInboxProps {
  /** Map of project IDs to project names for group headers. */
  projectNameMap: Map<string, string>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * GlobalMemoryInbox -- cross-project candidate memory triage inbox.
 *
 * Fetches all candidate memories globally, groups them by project, and renders
 * collapsible sections with MemoryCard (list) or MemoryGridCard (grid) items.
 *
 * Supports:
 * - Type filtering and search (status is locked to 'candidate')
 * - Grid/list view toggle
 * - Expand all / collapse all grouped sections
 * - Single-item approve, reject, edit, deprecate, reactivate, delete
 * - Batch approve, reject, delete via selection
 *
 * @example
 * ```tsx
 * <GlobalMemoryInbox
 *   projectNameMap={new Map([['proj-1', 'My Project']])}
 * />
 * ```
 */
export function GlobalMemoryInbox({ projectNameMap }: GlobalMemoryInboxProps) {
  // -------------------------------------------------------------------------
  // Filter / sort / view state
  // -------------------------------------------------------------------------
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  // Modal state
  const [editingMemory, setEditingMemory] = useState<MemoryItemResponse | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState | null>(null);

  // -------------------------------------------------------------------------
  // Selection
  // -------------------------------------------------------------------------
  const {
    selectedIds,
    toggleSelect,
    clearSelection,
  } = useMemorySelection();

  // -------------------------------------------------------------------------
  // Data fetching
  // -------------------------------------------------------------------------
  const { sortBy: apiSortBy, sortOrder: apiSortOrder } = parseSortValue(sortBy);

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useGlobalMemoryItems({
    status: 'candidate',
    type: typeFilter !== 'all' ? (typeFilter as any) : undefined,
    search: searchQuery || undefined,
    sortBy: apiSortBy,
    sortOrder: apiSortOrder,
    limit: 100,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);

  // -------------------------------------------------------------------------
  // Group items by project
  // -------------------------------------------------------------------------
  const groupedItems = useMemo(() => {
    const groups = new Map<string, MemoryItemResponse[]>();
    for (const item of items) {
      const key = item.project_id;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(item);
    }
    return groups;
  }, [items]);

  // -------------------------------------------------------------------------
  // Type counts (computed from items, not a separate API call)
  // -------------------------------------------------------------------------
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = { all: items.length };
    for (const item of items) {
      counts[item.type] = (counts[item.type] ?? 0) + 1;
    }
    return counts;
  }, [items]);

  // -------------------------------------------------------------------------
  // Expand / collapse all
  // -------------------------------------------------------------------------
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

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------
  const promoteItem = usePromoteMemoryItem();
  const deprecateItem = useDeprecateMemoryItem();
  const updateItem = useUpdateMemoryItem();
  const deleteItem = useDeleteMemoryItem();
  const bulkPromote = useBulkPromoteMemoryItems();
  const bulkDeprecate = useBulkDeprecateMemoryItems();
  const bulkDelete = useBulkDeleteMemoryItems({
    onSuccess: () => clearSelection(),
  });

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  const handleApprove = useCallback(
    (id: string) => {
      promoteItem.mutate({ itemId: id, data: { reason: 'Approved via global inbox' } });
    },
    [promoteItem]
  );

  const handleReject = useCallback(
    (id: string) => {
      setConfirmAction({
        type: 'reject',
        title: 'Reject Memory?',
        description: 'This will deprecate the memory item. It can be restored later.',
        itemId: id,
      });
    },
    []
  );

  const handleEdit = useCallback(
    (id: string) => {
      const memory = items.find((m) => m.id === id);
      if (memory) setEditingMemory(memory);
    },
    [items]
  );

  const handleMerge = useCallback((_id: string) => {
    // No-op: merge is not supported in the global inbox view.
  }, []);

  const handleCardClick = useCallback((_id: string) => {
    // No-op: no detail panel in the global inbox view.
  }, []);

  const handleDeprecate = useCallback(
    (id: string) => {
      setConfirmAction({
        type: 'deprecate',
        title: 'Deprecate Memory?',
        description: 'This will deprecate the memory item. It can be reactivated later.',
        itemId: id,
      });
    },
    []
  );

  const handleReactivate = useCallback(
    (id: string) => {
      updateItem.mutate({ itemId: id, data: { status: 'candidate' } });
    },
    [updateItem]
  );

  const handleDelete = useCallback(
    (id: string) => {
      setConfirmAction({
        type: 'delete',
        title: 'Delete Memory?',
        description: 'This will permanently delete the memory item. This action cannot be undone.',
        itemId: id,
      });
    },
    []
  );

  // Batch handlers
  const handleBatchApprove = useCallback(() => {
    bulkPromote.mutate(
      { item_ids: Array.from(selectedIds), reason: 'Batch approved via global inbox' },
      { onSuccess: () => clearSelection() }
    );
  }, [selectedIds, bulkPromote, clearSelection]);

  const handleBatchReject = useCallback(() => {
    setConfirmAction({
      type: 'batch-reject',
      title: `Reject ${selectedIds.size} ${selectedIds.size === 1 ? 'item' : 'items'}?`,
      description: 'This will deprecate all selected memory items. They can be restored later.',
    });
  }, [selectedIds]);

  const handleBatchDelete = useCallback(() => {
    setConfirmAction({
      type: 'batch-delete',
      title: `Delete ${selectedIds.size} ${selectedIds.size === 1 ? 'item' : 'items'}?`,
      description: 'This will permanently delete all selected memory items. This action cannot be undone.',
    });
  }, [selectedIds]);

  // Confirm action handler
  const handleConfirmAction = useCallback(() => {
    if (!confirmAction) return;

    switch (confirmAction.type) {
      case 'reject':
        if (confirmAction.itemId) {
          deprecateItem.mutate(
            { itemId: confirmAction.itemId, data: { reason: 'Rejected via global inbox' } },
            { onSuccess: () => setConfirmAction(null) }
          );
        }
        break;
      case 'deprecate':
        if (confirmAction.itemId) {
          deprecateItem.mutate(
            { itemId: confirmAction.itemId, data: { reason: 'Deprecated via global inbox' } },
            { onSuccess: () => setConfirmAction(null) }
          );
        }
        break;
      case 'delete':
        if (confirmAction.itemId) {
          deleteItem.mutate(confirmAction.itemId, {
            onSuccess: () => setConfirmAction(null),
          });
        }
        break;
      case 'batch-reject':
        bulkDeprecate.mutate(
          { item_ids: Array.from(selectedIds), reason: 'Batch rejected via global inbox' },
          {
            onSuccess: () => {
              clearSelection();
              setConfirmAction(null);
            },
          }
        );
        break;
      case 'batch-delete':
        bulkDelete.mutate(Array.from(selectedIds), {
          onSuccess: () => {
            clearSelection();
            setConfirmAction(null);
          },
        });
        break;
    }
  }, [confirmAction, deprecateItem, deleteItem, bulkDeprecate, bulkDelete, selectedIds, clearSelection]);

  // Derive confirm button label and loading state
  const confirmLabel = useMemo(() => {
    if (!confirmAction) return 'Confirm';
    switch (confirmAction.type) {
      case 'delete':
      case 'batch-delete':
        return 'Delete';
      case 'reject':
      case 'batch-reject':
        return 'Reject';
      case 'deprecate':
        return 'Deprecate';
      default:
        return 'Confirm';
    }
  }, [confirmAction]);

  const isConfirmLoading =
    deprecateItem.isPending ||
    deleteItem.isPending ||
    bulkDeprecate.isPending ||
    bulkDelete.isPending;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <>
      {/* Filter bar -- status locked to 'candidate' */}
      <MemoryFilterBar
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        statusFilter="candidate"
        onStatusFilterChange={() => {}} // no-op: status is fixed to candidate
        showDeprecated={false}
        onShowDeprecatedChange={() => {}}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        counts={typeCounts}
      />

      {/* View toggle + Expand All/Collapse All toolbar */}
      <div className="flex items-center justify-between px-6 py-2 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {items.length} {items.length === 1 ? 'candidate' : 'candidates'}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={toggleAllGroups}
          >
            {allExpanded ? 'Collapse All' : 'Expand All'}
          </Button>
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

      {/* Loading state */}
      {isLoading && (
        <div className="p-6">
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {!isLoading && isError && (
        <div
          className="flex flex-col items-center justify-center py-16 text-center"
          role="alert"
        >
          <p className="text-sm text-destructive">
            Failed to load candidates. Try refreshing.
          </p>
          <Button variant="outline" size="sm" className="mt-4" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Inbox className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-semibold">Inbox is empty</h3>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            No candidate memories to triage. Memories are automatically extracted from
            agent sessions.
          </p>
        </div>
      )}

      {/* Grouped items */}
      {!isLoading && !isError && items.length > 0 && (
        <div className="flex-1 overflow-y-auto">
          {Array.from(groupedItems.entries()).map(([projectId, projectItems]) => (
            <Collapsible
              key={projectId}
              open={expandedGroups[projectId] !== false}
              onOpenChange={(open) =>
                setExpandedGroups((prev) => ({ ...prev, [projectId]: open }))
              }
            >
              <CollapsibleTrigger asChild>
                <button
                  className="flex w-full items-center gap-2 px-6 py-3 text-left hover:bg-muted/50 border-b transition-colors"
                >
                  <ChevronRight
                    className={cn(
                      'h-4 w-4 text-muted-foreground transition-transform',
                      expandedGroups[projectId] !== false && 'rotate-90'
                    )}
                  />
                  <span className="font-medium text-sm">
                    {projectNameMap.get(projectId) ?? projectId}
                  </span>
                  <Badge variant="secondary" className="ml-1">
                    {projectItems.length}
                  </Badge>
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                {viewMode === 'grid' ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                    {projectItems.map((memory) => (
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
                    {projectItems.map((memory) => (
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

      {/* Batch action bar */}
      <BatchActionBar
        selectedCount={selectedIds.size}
        onApproveAll={handleBatchApprove}
        onRejectAll={handleBatchReject}
        onDeleteAll={handleBatchDelete}
        onClearSelection={clearSelection}
      />

      {/* Edit modal */}
      <MemoryFormModal
        open={!!editingMemory}
        onOpenChange={(open) => {
          if (!open) setEditingMemory(null);
        }}
        memory={editingMemory}
        projectId={editingMemory?.project_id ?? ''}
      />

      {/* Confirm action dialog */}
      <ConfirmActionDialog
        open={!!confirmAction}
        onOpenChange={(open) => {
          if (!open) setConfirmAction(null);
        }}
        title={confirmAction?.title ?? ''}
        description={confirmAction?.description ?? ''}
        confirmLabel={confirmLabel}
        confirmVariant="destructive"
        onConfirm={handleConfirmAction}
        isLoading={isConfirmLoading}
      />
    </>
  );
}
