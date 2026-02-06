'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import Link from 'next/link';
import {
  Settings,
  Plus,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useMemoryItems,
  useMemoryItem,
  useMemoryItemCounts,
  useMemorySelection,
  usePromoteMemoryItem,
  useDeprecateMemoryItem,
  useUpdateMemoryItem,
  useBulkPromoteMemoryItems,
  useBulkDeprecateMemoryItems,
  useKeyboardShortcuts,
} from '@/hooks';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryType } from '@/sdk/models/MemoryType';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryFilterBar } from '@/components/memory/memory-filter-bar';
import { MemoryList } from '@/components/memory/memory-list';
import { BatchActionBar } from '@/components/memory/batch-action-bar';
import { MemoryDetailPanel } from '@/components/memory/memory-detail-panel';
import { ConfirmActionDialog } from '@/components/memory/confirm-action-dialog';
import { MemoryFormModal } from '@/components/memory/memory-form-modal';
import { MergeModal } from '@/components/memory/merge-modal';
import { KeyboardHelpModal } from '@/components/memory/keyboard-help-modal';

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
    setFocusedIndex,
    toggleSelect,
    selectAll,
    clearSelection,
  } = useMemorySelection();

  // ---------------------------------------------------------------------------
  // Modal state
  // ---------------------------------------------------------------------------
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItemResponse | null>(null);
  const [mergingMemoryId, setMergingMemoryId] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: 'reject' | 'deprecate';
    memoryId: string;
    title: string;
    description: string;
  } | null>(null);
  const [helpModalOpen, setHelpModalOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // Container ref for keyboard shortcut scope
  // ---------------------------------------------------------------------------
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Fetch the selected memory item for the detail panel
  const { data: selectedMemory } = useMemoryItem(selectedMemoryId ?? undefined);

  // ---------------------------------------------------------------------------
  // Mutation hooks
  // ---------------------------------------------------------------------------
  const promoteItem = usePromoteMemoryItem();
  const deprecateItem = useDeprecateMemoryItem({
    onSuccess: () => setConfirmAction(null),
  });
  const updateItem = useUpdateMemoryItem();
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

  /** Reject (deprecate) a single memory item -- opens confirm dialog. */
  const handleReject = useCallback(
    (id: string) => {
      setConfirmAction({
        type: 'reject',
        memoryId: id,
        title: 'Reject Memory?',
        description:
          'This will deprecate the memory item. It can be restored later by changing its status.',
      });
    },
    []
  );

  /** Open the edit form modal for a memory item. */
  const handleEdit = useCallback(
    (id: string) => {
      const mem = memories.find((m) => m.id === id) ?? null;
      if (mem) {
        setEditingMemory(mem);
      }
    },
    [memories]
  );

  /** Open the merge modal for a memory item. */
  const handleMerge = useCallback((id: string) => {
    setMergingMemoryId(id);
  }, []);

  /** Deprecate a single memory item from the detail panel -- opens confirm dialog. */
  const handleDeprecate = useCallback(
    (id: string) => {
      setConfirmAction({
        type: 'deprecate',
        memoryId: id,
        title: 'Deprecate Memory?',
        description:
          'This will mark the memory item as deprecated. It will no longer be included in active context.',
      });
    },
    []
  );

  /** Reactivate a deprecated memory item by setting status to candidate. */
  const handleReactivate = useCallback(
    (id: string) => {
      updateItem.mutate({
        itemId: id,
        data: { status: 'candidate' },
      });
    },
    [updateItem]
  );

  /** Set a memory item's status directly (bypasses promote/deprecate flow). */
  const handleSetStatus = useCallback(
    (id: string, status: MemoryStatus) => {
      updateItem.mutate({
        itemId: id,
        data: { status },
      });
    },
    [updateItem]
  );

  /** Execute the confirmed action (reject or deprecate). */
  const handleConfirmAction = useCallback(() => {
    if (!confirmAction) return;
    deprecateItem.mutate({
      itemId: confirmAction.memoryId,
      data: {
        reason:
          confirmAction.type === 'reject'
            ? 'Rejected via memory inbox'
            : 'Deprecated via memory detail panel',
      },
    });
  }, [confirmAction, deprecateItem]);

  /** Close the detail panel. */
  const handleCloseDetail = useCallback(() => {
    setSelectedMemoryId(null);
  }, []);

  /** Open create memory dialog. */
  const handleCreateMemory = useCallback(() => {
    setCreateModalOpen(true);
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
  // Keyboard shortcuts (A11Y-3.12)
  // ---------------------------------------------------------------------------
  const anyModalOpen =
    createModalOpen ||
    !!editingMemory ||
    !!mergingMemoryId ||
    !!confirmAction ||
    helpModalOpen;

  useKeyboardShortcuts(
    containerRef,
    {
      onNavigateDown: () => {
        setFocusedIndex((prev) => Math.min(prev + 1, memories.length - 1));
      },
      onNavigateUp: () => {
        setFocusedIndex((prev) => Math.max(prev - 1, 0));
      },
      onApprove: () => {
        const item = memories[focusedIndex];
        if (item) handleApprove(item.id);
      },
      onEdit: () => {
        const item = memories[focusedIndex];
        if (item) handleEdit(item.id);
      },
      onReject: () => {
        const item = memories[focusedIndex];
        if (item) handleReject(item.id);
      },
      onMerge: () => {
        const item = memories[focusedIndex];
        if (item) handleMerge(item.id);
      },
      onToggleSelect: () => {
        const item = memories[focusedIndex];
        if (item) toggleSelect(item.id);
      },
      onOpenDetail: () => {
        const item = memories[focusedIndex];
        if (item) handleCardClick(item.id);
      },
      onDismiss: () => {
        if (selectedMemoryId) {
          handleCloseDetail();
        } else if (selectedIds.size > 0) {
          clearSelection();
        }
      },
      onSelectAll: () => {
        selectAll(memories.map((m) => m.id));
      },
      onShowHelp: () => {
        setHelpModalOpen(true);
      },
      itemCount: memories.length,
    },
    !anyModalOpen
  );

  // ---------------------------------------------------------------------------
  // Scroll focused card into view on j/k navigation
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (focusedIndex < 0) return;
    const container = containerRef.current;
    if (!container) return;
    const rows = container.querySelectorAll('[role="row"]');
    const target = rows[focusedIndex];
    if (target) {
      target.scrollIntoView({ block: 'nearest' });
    }
  }, [focusedIndex]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div ref={containerRef} tabIndex={-1} className="flex h-screen flex-col outline-none">
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
              <Settings className="mr-2 h-4 w-4" aria-hidden="true" />
              Settings
            </Button>
            <Button size="sm" onClick={handleCreateMemory}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
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
            onReactivate={handleReactivate}
            onDeprecate={handleDeprecate}
          />
        </div>

      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Detail Panel (fixed right sidebar, slides in/out)                  */}
      {/* ------------------------------------------------------------------ */}
      <MemoryDetailPanel
        memory={selectedMemory ?? null}
        isOpen={!!selectedMemoryId}
        onClose={handleCloseDetail}
        onEdit={handleEdit}
        onApprove={handleApprove}
        onReject={handleReject}
        onMerge={handleMerge}
        onDeprecate={handleDeprecate}
        onReactivate={handleReactivate}
        onSetStatus={handleSetStatus}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Batch Action Bar (fixed bottom, slides up when items selected)     */}
      {/* ------------------------------------------------------------------ */}
      <BatchActionBar
        selectedCount={selectedIds.size}
        onApproveAll={handleBatchApprove}
        onRejectAll={handleBatchReject}
        onClearSelection={clearSelection}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Modals                                                             */}
      {/* ------------------------------------------------------------------ */}

      {/* Create / Edit memory form modal */}
      <MemoryFormModal
        open={createModalOpen || !!editingMemory}
        onOpenChange={(open) => {
          if (!open) {
            setCreateModalOpen(false);
            setEditingMemory(null);
          }
        }}
        memory={editingMemory}
        projectId={projectId}
      />

      {/* Merge modal */}
      <MergeModal
        open={!!mergingMemoryId}
        onOpenChange={(open) => {
          if (!open) setMergingMemoryId(null);
        }}
        sourceMemory={memories.find((m) => m.id === mergingMemoryId) ?? null}
        allMemories={memories}
      />

      {/* Confirm action dialog (reject / deprecate) */}
      <ConfirmActionDialog
        open={!!confirmAction}
        onOpenChange={(open) => {
          if (!open) setConfirmAction(null);
        }}
        title={confirmAction?.title ?? ''}
        description={confirmAction?.description ?? ''}
        confirmLabel={confirmAction?.type === 'reject' ? 'Reject' : 'Deprecate'}
        confirmVariant="destructive"
        onConfirm={handleConfirmAction}
        isLoading={deprecateItem.isPending}
      />

      {/* Keyboard shortcuts help modal */}
      <KeyboardHelpModal
        open={helpModalOpen}
        onOpenChange={setHelpModalOpen}
      />
    </div>
  );
}
