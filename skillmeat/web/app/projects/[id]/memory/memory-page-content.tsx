'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Settings,
  Plus,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  useMemoryItems,
  useMemoryItemCounts,
  useMemorySelection,
  usePromoteMemoryItem,
  useDeprecateMemoryItem,
  useBulkPromoteMemoryItems,
  useBulkDeprecateMemoryItems,
} from '@/hooks';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryType } from '@/sdk/models/MemoryType';
import { MemoryFilterBar } from '@/components/memory/memory-filter-bar';
import { MemoryList } from '@/components/memory/memory-list';
import { BatchActionBar } from '@/components/memory/batch-action-bar';

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
// Placeholder component (detail panel -- replaced in UI-3.4)
// ---------------------------------------------------------------------------

function DetailPanelPlaceholder() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
      <p className="text-sm font-medium">Select a memory to view details</p>
      <p className="text-xs">Click on any memory item in the list</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface MemoryPageContentProps {
  projectId: string;
}

export function MemoryPageContent({ projectId }: MemoryPageContentProps) {
  // ---------------------------------------------------------------------------
  // Filter & sort state
  // ---------------------------------------------------------------------------
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);

  // For now, use projectId as the display name. Hook integration comes in a
  // later task when useProject is wired up.
  const projectName = projectId;

  // ---------------------------------------------------------------------------
  // Selection state
  // ---------------------------------------------------------------------------
  const {
    selectedIds,
    focusedIndex,
    toggleSelect,
    clearSelection,
  } = useMemorySelection();

  // ---------------------------------------------------------------------------
  // Build API filter params from UI state
  // ---------------------------------------------------------------------------
  const { sortBy: apiSortBy, sortOrder: apiSortOrder } = parseSortValue(sortBy);

  const memoryFilters = {
    projectId,
    status: statusFilter !== 'all' ? (statusFilter as MemoryStatus) : undefined,
    type: typeFilter !== 'all' ? (typeFilter as MemoryType) : undefined,
    search: searchQuery || undefined,
    sortBy: apiSortBy,
    sortOrder: apiSortOrder,
  };

  // ---------------------------------------------------------------------------
  // Data hooks
  // ---------------------------------------------------------------------------
  const {
    data: memoryData,
    isLoading,
    isError,
    error,
    refetch,
  } = useMemoryItems(memoryFilters);

  const { data: counts } = useMemoryItemCounts({ projectId });

  const memories = memoryData?.items ?? [];

  // ---------------------------------------------------------------------------
  // Mutation hooks
  // ---------------------------------------------------------------------------
  const promoteItem = usePromoteMemoryItem();
  const deprecateItem = useDeprecateMemoryItem();
  const bulkPromote = useBulkPromoteMemoryItems();
  const bulkDeprecate = useBulkDeprecateMemoryItems();

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  /** Select a memory card to open detail panel. */
  const handleCardClick = useCallback((memoryId: string) => {
    setSelectedMemoryId(memoryId);
  }, []);

  /** Approve (promote) a single memory item. */
  const handleApprove = useCallback(
    (id: string) => {
      promoteItem.mutate({ itemId: id, data: { reason: 'Approved via memory inbox' } });
    },
    [promoteItem]
  );

  /** Reject (deprecate) a single memory item. */
  const handleReject = useCallback(
    (id: string) => {
      deprecateItem.mutate({ itemId: id, data: { reason: 'Rejected via memory inbox' } });
    },
    [deprecateItem]
  );

  /** Placeholder for edit -- will open edit panel/dialog in UI-3.4. */
  const handleEdit = useCallback((_id: string) => {
    // TODO: Open edit dialog (UI-3.4)
  }, []);

  /** Placeholder for merge -- will open merge dialog in a future task. */
  const handleMerge = useCallback((_id: string) => {
    // TODO: Open merge dialog
  }, []);

  /** Open create memory flow. */
  const handleCreateMemory = useCallback(() => {
    // TODO: Open create memory dialog
  }, []);

  /** Batch approve all selected items. */
  const handleBatchApprove = useCallback(() => {
    if (selectedIds.size === 0) return;
    bulkPromote.mutate(
      { item_ids: [...selectedIds], reason: 'Batch approved via memory inbox' },
      { onSuccess: () => clearSelection() }
    );
  }, [selectedIds, bulkPromote, clearSelection]);

  /** Batch reject all selected items. */
  const handleBatchReject = useCallback(() => {
    if (selectedIds.size === 0) return;
    bulkDeprecate.mutate(
      { item_ids: [...selectedIds], reason: 'Batch rejected via memory inbox' },
      { onSuccess: () => clearSelection() }
    );
  }, [selectedIds, bulkDeprecate, clearSelection]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex h-screen flex-col">
      {/* ------------------------------------------------------------------ */}
      {/* Page Header                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="border-b px-6 pb-4 pt-6">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-3">
          <ol className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <li>
              <Link href="/projects" className="hover:text-foreground transition-colors">
                Projects
              </Link>
            </li>
            <li aria-hidden="true">
              <ChevronRight className="h-3.5 w-3.5" />
            </li>
            <li>
              <Link
                href={`/projects/${projectId}`}
                className="hover:text-foreground transition-colors"
              >
                {projectName}
              </Link>
            </li>
            <li aria-hidden="true">
              <ChevronRight className="h-3.5 w-3.5" />
            </li>
            <li className="font-medium text-foreground">Memory</li>
          </ol>
        </nav>

        {/* Title row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Memory</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Review and manage extracted knowledge for this project
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
            <Button size="sm" onClick={handleCreateMemory}>
              <Plus className="mr-2 h-4 w-4" />
              Create Memory
            </Button>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Filter Bar (Type Tabs + Controls)                                  */}
      {/* ------------------------------------------------------------------ */}
      <MemoryFilterBar
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        counts={counts}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Main Content: List + Detail Panel                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-1 overflow-hidden">
        {/* Memory list area (scrollable, flex-1) */}
        <div
          className="flex-1 overflow-y-auto"
          role="region"
          aria-label="Memory list"
        >
          <MemoryList
            memories={memories}
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
          />
        </div>

        {/* Detail panel (conditional, right sidebar) */}
        {selectedMemoryId && (
          <aside
            className={cn(
              'w-[420px] shrink-0 border-l overflow-y-auto',
              'hidden lg:block' // hide on smaller screens
            )}
            role="complementary"
            aria-label="Memory detail panel"
          >
            {/* TODO: Replace with DetailPanel in UI-3.4 */}
            <DetailPanelPlaceholder />
          </aside>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Batch Action Bar (fixed bottom, slides up when items selected)     */}
      {/* ------------------------------------------------------------------ */}
      <BatchActionBar
        selectedCount={selectedIds.size}
        onApproveAll={handleBatchApprove}
        onRejectAll={handleBatchReject}
        onClearSelection={clearSelection}
      />
    </div>
  );
}
